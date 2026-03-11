"""Core assistant implementation."""

import asyncio
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from otonomassist.ai.factory import AIProviderFactory
from otonomassist.core.agent_context import build_runtime_context_block, ensure_agent_storage
from otonomassist.core.execution_control import classify_result_status, get_skill_timeout_seconds
from otonomassist.core.execution_history import append_execution_event, new_trace_id, render_execution_history
from otonomassist.core.execution_metrics import record_execution_metric, render_execution_metrics
from otonomassist.core.external_assets import (
    ensure_external_asset_layout,
    get_external_skills_dir,
)
from otonomassist.core.skill_loader import SkillLoader
from otonomassist.core.skill_registry import SkillRegistry
from otonomassist.core.transport import TransportContext
from otonomassist.services.personality import PersonalityService
from otonomassist.services.policy import PolicyService
from otonomassist.services.runtime import BudgetManager, ExecutionService, InteractionOrchestrator, ModelRouter

if TYPE_CHECKING:
    from otonomassist.models import Skill


class Assistant:
    """Core assistant that manages skills and command execution."""
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
        self.personality_service = PersonalityService()
        self.policy_service = PolicyService()
        self.budget_manager = BudgetManager()
        self.model_router = ModelRouter(self.budget_manager)
        self.execution_service = ExecutionService(
            self.registry,
            self.policy_service,
            provider_getter=self._get_provider,
            system_prompt_builder=self._get_orchestration_system_prompt,
            error_formatter=self._format_error,
            async_runner=self._run_async,
            help_renderer=self.get_help,
        )
        self.orchestrator = InteractionOrchestrator(self, self.policy_service, self.execution_service)
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the assistant and load all skills."""
        if self._initialized:
            return

        ensure_external_asset_layout()
        count = self.loader.load_all(self.registry)
        external_loader = SkillLoader(get_external_skills_dir())
        count += external_loader.load_all(self.registry)
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
            lines.append(
                f"- {defn.name}: {defn.description} "
                f"(layer: {defn.autonomy_category}, risk: {defn.risk_level}, triggers: {triggers})"
            )
            if defn.side_effects:
                lines.append(f"  Side Effects: {', '.join(defn.side_effects)}")
            if defn.requires:
                lines.append(f"  Requires: {', '.join(defn.requires)}")
            if defn.idempotency and defn.idempotency != "unknown":
                lines.append(f"  Idempotency: {defn.idempotency}")
            # Add AI-specific instructions if available
            if defn.ai_instructions:
                lines.append(f"  AI Instructions: {defn.ai_instructions[:200]}...")

        return "\n".join(lines)

    def _render_skill_layer_audit(self) -> str:
        """Render the autonomous skill-layer summary."""
        summary = self.registry.get_skill_layer_summary()
        lines = [
            "Skill Layer Audit",
            "",
            "[Summary]",
            f"- category_count: {summary['category_count']}",
            f"- skill_count: {len(self.registry.list_skills())}",
        ]
        for category, skills in sorted(summary["skills"].items()):
            lines.extend(["", f"[{category}]"])
            for item in skills:
                lines.append(
                    f"- {item['name']} [risk={item['risk_level']}, idempotency={item['idempotency']}]"
                )
                if item["requires"]:
                    lines.append("  requires: " + ", ".join(item["requires"]))
                if item["side_effects"]:
                    lines.append("  side_effects: " + ", ".join(item["side_effects"]))
        return "\n".join(lines)

    def _get_orchestration_system_prompt(self, command: str) -> str:
        """Build system prompt for AI orchestration."""
        return f"""Anda adalah asisten yang menentukan skill mana yang akan digunakan berdasarkan input user.

{self._build_skills_context()}

{self.personality_service.build_prompt_block()}

{build_runtime_context_block(command)}

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
            return self.model_router.get_provider()
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

        context = context or TransportContext()
        trace_id = context.trace_id or new_trace_id()
        context.trace_id = trace_id
        command_started = time.perf_counter()
        append_execution_event(
            "command_received",
            trace_id=trace_id,
            status="started",
            source=context.source,
            command=command,
            data={
                "user_id": context.user_id or "",
                "chat_id": context.chat_id or "",
            },
        )
        result = self.orchestrator.handle_command(command, context)
        return self._finalize_command_result(context, command, result, command_started)

    def handle_message(self, message: str, context: TransportContext | None = None) -> str:
        """Handle an inbound message from any transport."""
        context = context or TransportContext()
        text = message.strip()
        if not text:
            return "Please enter a command. Type 'help' for available commands."

        return self._execute_with_context(text, context)

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

    def _format_error(self, error_type: str, message: str) -> str:
        """Format error message with diagnostic info."""
        lines = [
            f"[ERROR] {error_type.upper()}",
            message,
            "",
            "--- Diagnostic Info ---",
            AIProviderFactory.get_config_diagnostic(),
            "",
            f"Skill timeout: {get_skill_timeout_seconds():.2f}s",
        ]
        return "\n".join(lines)

    def _finalize_command_result(
        self,
        context: TransportContext,
        command: str,
        result: str,
        started_at: float,
    ) -> str:
        """Log the final command outcome and return the original result unchanged."""
        append_execution_event(
            "command_completed",
            trace_id=context.trace_id or new_trace_id(),
            status=classify_result_status(result),
            source=context.source,
            command=command,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            data={
                "result_preview": result[:240],
            },
        )
        record_execution_metric(
            "command_completed",
            status=classify_result_status(result),
            source=context.source,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        return result

    def _should_force_research(self, command: str) -> bool:
        """Detect prompts that should be web-validated before answering."""
        text = command.strip()
        if not text:
            return False
        return bool(self.FACT_VALIDATION_PATTERN.search(text))

    def get_help(self) -> str:
        """Get help text."""
        return """OtonomAssist - Available commands:
- help: Show this help message
- list: List all available skills
- history: Show recent execution history
- metrics: Show aggregated execution metrics
- jobs: Show runtime job queue
- jobs enqueue: Enqueue the next ready planner task into runtime job queue
- external audit: Show audited external assets in workspace
- external approve <name>: Approve one external skill for loading
- external reject <name>: Reject one external skill from loading
- external sync: Refresh external asset inventory from workspace
- external install <source>: Install external skill into workspace/skills-external
- skills audit: Show autonomous skill-layer categories, risk, and requirements
- doctor: Show read-only configuration status
- config status: Alias for doctor
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

    def render_skill_layer_audit(self) -> str:
        """Expose skill-layer audit through the orchestration service boundary."""
        return self._render_skill_layer_audit()

    def render_execution_history(self) -> str:
        """Expose execution history rendering through the orchestration boundary."""
        return render_execution_history()

    def render_execution_metrics(self) -> str:
        """Expose execution metrics rendering through the orchestration boundary."""
        return render_execution_metrics()

    def should_force_research(self, command: str) -> bool:
        """Expose fact-validation detection through the orchestration boundary."""
        return self._should_force_research(command)

    def route_via_ai(self, command: str, context: TransportContext | None = None) -> str:
        """Expose AI routing through the execution service boundary."""
        return self.execution_service.route_via_ai(command, context=context)

    def execute_skill(
        self,
        skill: "Skill",
        args: str,
        original_command: str | None = None,
        trace_id: str = "",
    ) -> str:
        """Expose skill execution through the execution service boundary."""
        return self.execution_service.execute_skill(
            skill,
            args,
            original_command=original_command,
            trace_id=trace_id,
        )
