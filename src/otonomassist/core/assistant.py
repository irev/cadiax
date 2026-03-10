"""Core assistant implementation."""

import asyncio
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from otonomassist.ai.factory import AIProviderFactory
from otonomassist.core.skill_loader import SkillLoader
from otonomassist.core.skill_registry import SkillRegistry

if TYPE_CHECKING:
    from otonomassist.models import Skill


class Assistant:
    """Core assistant that manages skills and command execution."""

    SKILL_RESPONSE_PATTERN = re.compile(
        r"^SKILL:\s*(\w+)\s*\|\s*ARGS:\s*(.*)$",
        re.IGNORECASE | re.MULTILINE
    )

    def __init__(self, skills_dir: Path | None = None) -> None:
        self.registry = SkillRegistry()
        self.loader = SkillLoader(skills_dir)
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the assistant and load all skills."""
        if self._initialized:
            return

        count = self.loader.load_all(self.registry)
        print(f"Loaded {count} skills", file=sys.stderr)
        self._initialized = True

    def _build_skills_context(self) -> str:
        """Build context string about available skills for AI."""
        skills = self.registry.list_skills()
        if not skills:
            return "No skills available."

        lines = ["Available skills:"]
        for skill in skills:
            defn = skill.definition
            triggers = ", ".join(defn.triggers) if defn.triggers else defn.name
            lines.append(f"- {defn.name}: {defn.description} (triggers: {triggers})")
            # Add AI-specific instructions if available
            if defn.ai_instructions:
                lines.append(f"  AI Instructions: {defn.ai_instructions[:200]}...")

        return "\n".join(lines)

    def _get_orchestration_system_prompt(self) -> str:
        """Build system prompt for AI orchestration."""
        return f"""Anda adalah asisten yang menentukan skill mana yang akan digunakan berdasarkan input user.

{self._build_skills_context()}

Petunjuk:
1. Analisis input user untuk menentukan skill yang tepat
2. Jika user hanya ingin chatting/pertanyaan umum tanpa skill spesifik, gunakan skill 'ai-chat'
3. Respon dengan format: SKILL: <nama_skill> | ARGS: <argumen untuk skill>
4. Contoh: Jika user input "hitung 10 + 5", respons: SKILL: calc | ARGS: 10 + 5
5. Jika user input "apa itu python", respons: SKILL: ai-chat | ARGS: apa itu python
6. Pastikan ARGS berisi informasi yang dibutuhkan skill untuk menjalankan tugasnya

Responskan HANYA format SKILL: ... | ARGS: ... tanpa teks lain."""

    def _get_provider(self):
        """Get available AI provider."""
        try:
            return AIProviderFactory.auto_detect()
        except Exception:
            return None

    def execute(self, command: str) -> str:
        """Execute a command using AI-First orchestration."""
        if not self._initialized:
            self.initialize()

        if not command.strip():
            return "Please enter a command. Type 'help' for available commands."

        # Built-in commands
        cmd_lower = command.strip().lower()
        if cmd_lower == "help":
            return self.get_help()

        if cmd_lower == "list":
            return self.list_skills_str()

        # Hybrid approach: try direct skill match first
        skill, args = self.registry.find_by_command(command)
        if skill:
            return skill.execute(args)

        # Fallback to AI routing for natural language input
        return self._route_via_ai(command)

    def _route_via_ai(self, command: str) -> str:
        """Route command through AI to determine which skill to use."""
        provider = self._get_provider()

        if not provider:
            return self._format_error(
                error_type="no_provider",
                message="Tidak ada AI provider tersedia. Cek konfigurasi di .env"
            )

        try:
            response = self._run_async(provider.chat_completion(
                prompt=command,
                system_prompt=self._get_orchestration_system_prompt()
            ))

            return self._parse_and_execute(response, command)

        except Exception as e:
            return self._format_error(
                error_type="api_error",
                message=str(e)
            )

    def _run_async(self, coro):
        """Run coroutine safely, handling existing event loops."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            import concurrent.futures
            import asyncio

            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()
        else:
            return asyncio.run(coro)

    def _parse_and_execute(self, ai_response: str, original_command: str) -> str:
        """Parse AI response and execute the determined skill."""
        match = self.SKILL_RESPONSE_PATTERN.match(ai_response.strip())

        if not match:
            # AI didn't return expected format, fallback to direct response
            return ai_response

        skill_name = match.group(1).strip().lower()
        skill_args = match.group(2).strip()

        # Find skill in registry
        skill = self.registry.get(skill_name)

        if not skill:
            return self._format_error(
                error_type="skill_not_found",
                message=f"Skill '{skill_name}' tidak ditemukan. Available: {', '.join(s.name for s in self.registry)}"
            )

        try:
            return skill.execute(skill_args)
        except Exception as e:
            return f"Error executing skill '{skill_name}': {str(e)}"

    def _format_error(self, error_type: str, message: str) -> str:
        """Format error message with diagnostic info."""
        lines = [
            f"[ERROR] {error_type.upper()}",
            message,
            "",
            "--- Diagnostic Info ---",
            AIProviderFactory.get_config_diagnostic()
        ]
        return "\n".join(lines)

    def get_help(self) -> str:
        """Get help text."""
        return """OtonomAssist - Available commands:
- help: Show this help message
- list: List all available skills
- <any other command>: Will be routed to AI to determine appropriate skill

Skills are loaded from the skills/ directory."""

    def list_skills_str(self) -> str:
        """List all skills as string."""
        skills = self.registry.list_skills()
        if not skills:
            return "No skills loaded."

        lines = ["Available skills:"]
        for skill in skills:
            defn = skill.definition
            lines.append(f"  - {defn.name}: {defn.description}")

        return "\n".join(lines)

    def list_skills(self) -> list["Skill"]:
        """List all registered skills."""
        return self.registry.list_skills()
