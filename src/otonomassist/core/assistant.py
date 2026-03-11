"""Core assistant implementation."""

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from otonomassist.ai.factory import AIProviderFactory
from otonomassist.core.agent_context import build_agent_context_block, ensure_agent_storage
from otonomassist.core.result_formatter import extract_presentation_request, format_result
from otonomassist.core.skill_loader import SkillLoader
from otonomassist.core.skill_registry import SkillRegistry
from otonomassist.core.transport import TransportContext

if TYPE_CHECKING:
    from otonomassist.models import Skill


class Assistant:
    """Core assistant that manages skills and command execution."""

    SKILL_RESPONSE_PATTERN = re.compile(
        r"^SKILL:\s*(\w+)\s*\|\s*ARGS:\s*(.*)$",
        re.IGNORECASE | re.MULTILINE
    )
    FACT_VALIDATION_PATTERN = re.compile(
        r"\b(20\d{2}|kapan|tanggal|bulan apa|jadwal|schedule|hari raya|idul fitri|lebaran|"
        r"terbaru|latest|hari ini|today|saat ini|current|presiden|ceo|harga|"
        r"cuaca|kurs|libur)\b",
        re.IGNORECASE,
    )

    def __init__(self, skills_dir: Path | None = None) -> None:
        load_dotenv(override=True)
        ensure_agent_storage()
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

{build_agent_context_block()}

Petunjuk:
1. Analisis input user untuk menentukan skill yang tepat
2. Jika user hanya ingin chatting/pertanyaan umum tanpa skill spesifik, gunakan skill 'ai'
3. Respon dengan format: SKILL: <nama_skill> | ARGS: <argumen untuk skill>
4. Jika user ingin menyimpan fakta atau keputusan, prioritaskan skill 'memory'
5. Gunakan skill 'planner' hanya untuk goal, backlog, task, atau langkah kerja agent internal; jangan gunakan 'planner' untuk rencana umum seperti itinerary, jadwal liburan, atau outline non-agent. Untuk itu gunakan skill 'ai'
6. Jika user ingin mengatur identitas, preferensi, atau personalisasi agent, prioritaskan skill 'profile'
7. Jika user ingin refleksi mandiri atau langkah berikutnya berdasarkan state agent, prioritaskan skill 'agent-loop'
8. Jika user ingin mengeksekusi next task atau menjalankan action dari planner, prioritaskan skill 'executor'
9. Jika user ingin menjalankan loop otomatis beberapa langkah atau sampai idle, prioritaskan skill 'runner'
10. Jika user ingin menyimpan atau mengelola kredensial, prioritaskan skill 'secrets'
11. Jika user ingin membaca, mencari, melihat struktur, atau merangkum file proyek, prioritaskan skill 'workspace' dan ubah ke subcommand yang executable seperti `workspace tree .`, `workspace read README.md`, `workspace find OPENAI_MODEL`, atau `workspace summary src`
12. Jika user meminta fakta real-world yang sensitif terhadap waktu, tanggal, jadwal, atau informasi terbaru, prioritaskan skill 'research'
13. Jika user ingin audit atau evaluasi hasil kerja, prioritaskan skill 'self-review'
14. Jika user input "apa itu python", respons: SKILL: ai | ARGS: apa itu python
15. Jika user berkata "lihat struktur file yang ada di workspace", respons: SKILL: workspace | ARGS: tree .
16. Jika user berkata "baca README.md", respons: SKILL: workspace | ARGS: read README.md
17. Jika user berkata "buat rencana libur idul fitri 2026", respons: SKILL: research | ARGS: buat rencana libur idul fitri 2026 di indonesia
18. Pastikan ARGS berisi informasi yang dibutuhkan skill untuk menjalankan tugasnya, bukan sekadar mengulang kalimat user mentah bila skill membutuhkan subcommand tertentu

Responskan HANYA format SKILL: ... | ARGS: ... tanpa teks lain."""

    def _get_provider(self):
        """Get available AI provider."""
        try:
            return AIProviderFactory.auto_detect()
        except Exception:
            return None

    def execute(self, command: str) -> str:
        """Execute a command using AI-First orchestration."""
        return self._execute_with_context(command, context=None)

    def _execute_with_context(self, command: str, context: TransportContext | None) -> str:
        """Execute a command with optional transport context."""
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

        if cmd_lower == "debug-config":
            denied = self._authorize_command("debug-config", "", context)
            if denied:
                return denied
            return self.get_debug_config()

        if cmd_lower == "list-models":
            denied = self._authorize_command("list-models", "", context)
            if denied:
                return denied
            return self.get_model_listing()

        for prefix in ("cari informasi ", "cek informasi ", "cari fakta ", "verifikasi "):
            if cmd_lower.startswith(prefix):
                research_skill = self.registry.get("research")
                if research_skill:
                    query = command.strip()[len(prefix):].strip()
                    denied = self._authorize_command("research", query, context)
                    if denied:
                        return denied
                    return self._execute_skill(research_skill, query, original_command=command)

        # Hybrid approach: try direct skill match first
        skill, args = self.registry.find_by_command(command)
        if skill:
            denied = self._authorize_command(skill.name.lower(), args, context)
            if denied:
                return denied
            return self._execute_skill(skill, args, original_command=command)

        if self._should_force_research(command):
            research_skill = self.registry.get("research")
            if research_skill:
                denied = self._authorize_command("research", command, context)
                if denied:
                    return denied
                return self._execute_skill(research_skill, command, original_command=command)

        # Fallback to AI routing for natural language input
        return self._route_via_ai(command, context=context)

    def handle_message(self, message: str, context: TransportContext | None = None) -> str:
        """Handle an inbound message from any transport."""
        context = context or TransportContext()
        text = message.strip()
        if not text:
            return "Please enter a command. Type 'help' for available commands."

        return self._execute_with_context(text, context)

    def _route_via_ai(self, command: str, context: TransportContext | None = None) -> str:
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

            return self._parse_and_execute(response, command, context=context)

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

            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    pending = [
                        task for task in asyncio.all_tasks(new_loop)
                        if not task.done()
                    ]
                    for task in pending:
                        task.cancel()
                    if pending:
                        new_loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                    new_loop.run_until_complete(new_loop.shutdown_default_executor())
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()
        else:
            return asyncio.run(coro)

    def _parse_and_execute(
        self,
        ai_response: str,
        original_command: str,
        context: TransportContext | None = None,
    ) -> str:
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
            denied = self._authorize_command(skill.name.lower(), skill_args, context)
            if denied:
                return denied
            return self._execute_skill(skill, skill_args, original_command=original_command)
        except Exception as e:
            return f"Error executing skill '{skill_name}': {str(e)}"

    def _execute_skill(self, skill: "Skill", args: str, original_command: str | None = None) -> str:
        """Execute a skill with assistant-level special cases."""
        if skill.name.lower() == "help":
            return self.get_help()

        cleaned_args, presentation = extract_presentation_request(original_command or args, args)
        raw_result = skill.run(cleaned_args)
        return format_result(raw_result, presentation)

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

    def _should_force_research(self, command: str) -> bool:
        """Detect prompts that should be web-validated before answering."""
        text = command.strip()
        if not text:
            return False
        return bool(self.FACT_VALIDATION_PATTERN.search(text))

    def _authorize_command(
        self,
        prefix: str,
        args: str,
        context: TransportContext | None,
    ) -> str | None:
        """Authorize a command/skill prefix and subcommand for a transport context."""
        if context is None or context.source != "telegram":
            return None

        roles = set(context.roles)
        if "owner" in roles:
            return None
        if "approved" not in roles:
            return "Akses Telegram belum diotorisasi untuk operasi ini."

        prefix = prefix.strip().lower()
        subcommand = _extract_subcommand(args)
        owner_only = _parse_prefix_set(
            "TELEGRAM_OWNER_ONLY_PREFIXES",
            {"debug-config", "list-models", "secrets", "executor", "runner"},
        )
        approved = _parse_prefix_set(
            "TELEGRAM_APPROVED_PREFIXES",
            {
                "help",
                "list",
                "ai",
                "research",
                "memory",
                "planner",
                "profile",
                "agent-loop",
                "workspace",
                "self-review",
            },
        )

        if prefix in owner_only:
            return (
                f"Command/skill `{prefix}` dibatasi untuk owner Telegram. "
                "Gunakan akun owner atau minta owner menjalankannya."
            )

        if prefix in approved:
            action_denied = self._authorize_approved_action(prefix, subcommand)
            if action_denied:
                return action_denied
            return None

        return (
            f"Command/skill `{prefix}` tidak diizinkan untuk user Telegram non-owner."
        )

    def _authorize_approved_action(self, prefix: str, subcommand: str) -> str | None:
        """Apply finer-grained action checks for approved Telegram users."""
        read_only_actions: dict[str, set[str]] = {
            "help": {""},
            "list": {""},
            "ai": {"*"},
            "research": {"*"},
            "workspace": {"tree", "read", "find", "files", "summary"},
            "memory": {"list", "search", "get", "summarize", "summary", "context"},
            "planner": {"list", "next", "summary"},
            "profile": {"show"},
        }
        mutate_denial: dict[str, str] = {
            "memory": "Operasi ubah memory Telegram dibatasi untuk owner.",
            "planner": "Operasi ubah planner Telegram dibatasi untuk owner.",
            "profile": "Operasi ubah profile Telegram dibatasi untuk owner.",
            "self-review": "Self-review Telegram dibatasi untuk owner karena menulis memory, lessons, dan planner.",
            "agent-loop": "Agent-loop Telegram dibatasi untuk owner karena menulis memory pembelajaran.",
        }

        allowed = read_only_actions.get(prefix)
        if allowed is None:
            if prefix in mutate_denial:
                return mutate_denial[prefix]
            return (
                f"Operasi `{prefix}` tidak diizinkan untuk user Telegram approved."
            )

        if "*" in allowed:
            return None
        if subcommand in allowed:
            return None
        if prefix in mutate_denial:
            return mutate_denial[prefix]
        return (
            f"Subcommand `{prefix} {subcommand or '(default)'}` dibatasi untuk owner Telegram."
        )

    def get_help(self) -> str:
        """Get help text."""
        return """OtonomAssist - Available commands:
- help: Show this help message
- list: List all available skills
- debug-config: Show active AI provider configuration
- list-models: List models visible to the active API key
- <any other command>: Will be routed to AI to determine appropriate skill

Skills are loaded from the skills/ directory."""

    def get_debug_config(self) -> str:
        """Get active AI provider diagnostic info."""
        return AIProviderFactory.get_config_diagnostic()

    def get_model_listing(self) -> str:
        """Get model listing for the active provider if supported."""
        try:
            return AIProviderFactory.get_model_listing()
        except Exception as e:
            return self._format_error("model_listing_error", str(e))

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


def _parse_prefix_set(name: str, default: set[str]) -> set[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return set(default)
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _extract_subcommand(args: str) -> str:
    args = args.strip().lower()
    if not args:
        return ""
    return args.split()[0]

    def list_skills(self) -> list["Skill"]:
        """List all registered skills."""
        return self.registry.list_skills()
