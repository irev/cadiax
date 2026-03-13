"""Runtime orchestration for canonical interactions."""

from __future__ import annotations

import re
from typing import Any

from otonomassist.core.admin_api import build_admin_snapshot
from otonomassist.core.config_doctor import get_config_status_report
from otonomassist.core.execution_history import append_execution_event
from otonomassist.core.execution_metrics import record_execution_metric
from otonomassist.core.external_assets import (
    get_external_skills_dir,
    render_external_asset_audit,
    set_external_asset_approval,
    sync_external_skill_inventory,
)
from otonomassist.core.external_installer import install_external_skill, render_external_install_result
from otonomassist.core.job_runtime import enqueue_ready_planner_task, render_job_queue
from otonomassist.core.transport import TransportContext
from otonomassist.services.policy import PolicyService
from otonomassist.services.runtime.execution_service import ExecutionService


class InteractionOrchestrator:
    """Route one normalized interaction through built-ins, skills, and AI fallback."""

    RESEARCH_PREFIXES = ("cari informasi ", "cek informasi ", "cari fakta ", "verifikasi ")
    DIRECT_SKILL_TOKEN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$", re.IGNORECASE)
    FILE_READ_PATTERN = re.compile(r"^[A-Za-z0-9_./\\\\-]+\.[A-Za-z0-9]+$")

    def __init__(
        self,
        assistant: Any,
        policy_service: PolicyService,
        execution_service: ExecutionService,
    ) -> None:
        self.assistant = assistant
        self.policy_service = policy_service
        self.execution_service = execution_service

    def handle_command(self, command: str, context: TransportContext) -> str:
        """Resolve one command into built-ins, direct skill execution, or AI routing."""
        cmd_lower = command.strip().lower()
        if cmd_lower == "help":
            denied = self._authorize("help", "", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="help", routed_command="help")
            return self.assistant.get_help()

        if cmd_lower == "list":
            denied = self._authorize("list", "", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="list", routed_command="list")
            return self.assistant.list_skills_str()

        if cmd_lower in {"history", "history recent"}:
            denied = self._authorize("history", "recent" if cmd_lower.endswith("recent") else "", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="history", routed_command=command)
            return self.assistant.render_execution_history()
        if cmd_lower in {"metrics", "metrics summary"}:
            denied = self._authorize("metrics", "summary" if cmd_lower.endswith("summary") else "", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="metrics", routed_command=command)
            return self.assistant.render_execution_metrics()
        if cmd_lower in {"jobs", "jobs list", "job queue"}:
            denied = self._authorize("jobs", "list" if cmd_lower != "job queue" else "queue", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="jobs", routed_command=command)
            return render_job_queue()
        if cmd_lower in {"api status", "admin status"}:
            denied = self._authorize("admin", "status", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="admin", routed_command=command)
            _, payload = build_admin_snapshot("/status")
            return str(payload)
        if cmd_lower in {"jobs enqueue", "job enqueue"}:
            denied = self._authorize("jobs", "enqueue", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="jobs", routed_command=command)
            job = enqueue_ready_planner_task(trace_id=context.trace_id or "", source=context.source)
            if not job:
                return "Tidak ada task ready untuk dimasukkan ke job queue."
            return f"Job #{job['id']} dibuat untuk task #{job['task_id']} {job['task_text']}"

        if cmd_lower in {"external audit", "external list"}:
            denied = self._authorize("external", "audit" if cmd_lower.endswith("audit") else "list", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="external", routed_command=command)
            return render_external_asset_audit()
        if cmd_lower.startswith("external approve "):
            name = command.strip()[len("external approve ") :].strip()
            denied = self._authorize("external", f"approve {name}".strip(), context)
            if denied:
                return denied
            if not name:
                return "Gunakan: external approve <name>"
            self._record_route(context, route_kind="builtin", target="external", routed_command=command)
            try:
                asset = set_external_asset_approval(name, "approved", actor="assistant")
            except Exception as exc:
                return f"External approve gagal: {exc}"
            return f"External asset `{asset['name']}` diset ke approved."
        if cmd_lower.startswith("external reject "):
            name = command.strip()[len("external reject ") :].strip()
            denied = self._authorize("external", f"reject {name}".strip(), context)
            if denied:
                return denied
            if not name:
                return "Gunakan: external reject <name>"
            self._record_route(context, route_kind="builtin", target="external", routed_command=command)
            try:
                asset = set_external_asset_approval(name, "rejected", actor="assistant")
            except Exception as exc:
                return f"External reject gagal: {exc}"
            return f"External asset `{asset['name']}` diset ke rejected."
        if cmd_lower == "external sync":
            denied = self._authorize("external", "sync", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="external", routed_command=command)
            result = sync_external_skill_inventory(installed_by="assistant")
            return (
                f"External assets synced: {result['discovered_count']} scanned from "
                f"{get_external_skills_dir()}"
            )
        if cmd_lower.startswith("external install "):
            source = command.strip()[len("external install ") :].strip()
            denied = self._authorize("external", f"install {source}".strip(), context)
            if denied:
                return denied
            if not source:
                return "Gunakan: external install <path-lokal-atau-url-git>"
            self._record_route(context, route_kind="builtin", target="external", routed_command=command)
            try:
                result = install_external_skill(source, actor="assistant")
                return render_external_install_result(result)
            except Exception as exc:
                return f"External install gagal: {exc}"
        if cmd_lower in {"skills audit", "skill audit"}:
            denied = self._authorize("skills", "audit", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="skills", routed_command=command)
            return self.assistant.render_skill_layer_audit()

        if cmd_lower in {"doctor", "config status", "config-status"}:
            denied = self._authorize("doctor", "status" if cmd_lower != "doctor" else "", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="doctor", routed_command=command)
            return get_config_status_report()

        if cmd_lower == "debug-config":
            denied = self._authorize("debug-config", "", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="debug-config", routed_command=command)
            return self.assistant.get_debug_config()

        if cmd_lower == "list-models":
            denied = self._authorize("list-models", "", context)
            if denied:
                return denied
            self._record_route(context, route_kind="builtin", target="list-models", routed_command=command)
            return self.assistant.get_model_listing()

        for prefix in self.RESEARCH_PREFIXES:
            if cmd_lower.startswith(prefix):
                research_skill = self.assistant.registry.get("research")
                if research_skill:
                    query = command.strip()[len(prefix) :].strip()
                    denied = self._authorize("research", query, context)
                    if denied:
                        return denied
                    self._record_route(context, route_kind="research_prefix", target="research", routed_command=query)
                    return self.execution_service.execute_skill(
                        research_skill,
                        query,
                        original_command=command,
                        trace_id=context.trace_id or "",
                    )

        skill, args = self.assistant.registry.find_by_command(command)
        if skill:
            denied = self._authorize(skill.name.lower(), args, context)
            if denied:
                return denied
            self._record_route(context, route_kind="direct_skill", target=skill.name.lower(), routed_command=command)
            return self.execution_service.execute_skill(
                skill,
                args,
                original_command=command,
                trace_id=context.trace_id or "",
            )

        if self._looks_like_direct_skill_invocation(command):
            skill_name = command.strip().split(maxsplit=1)[0]
            return f"Skill '{skill_name}' tidak ditemukan."

        heuristic_command = self._heuristic_route(command)
        if heuristic_command and heuristic_command.strip().lower() != cmd_lower:
            heuristic_target = heuristic_command.strip().split(maxsplit=1)[0].lower()
            self._record_route(context, route_kind="heuristic", target=heuristic_target, routed_command=heuristic_command)
            return self.handle_command(heuristic_command, context)

        if self.assistant.should_force_research(command):
            research_skill = self.assistant.registry.get("research")
            if research_skill:
                denied = self._authorize("research", command, context)
                if denied:
                    return denied
                self._record_route(context, route_kind="forced_research", target="research", routed_command=command)
                return self.execution_service.execute_skill(
                    research_skill,
                    command,
                    original_command=command,
                    trace_id=context.trace_id or "",
                )

        self._record_route(context, route_kind="ai_router", target="ai", routed_command=command)
        return self.execution_service.route_via_ai(command, context=context)

    def _authorize(self, prefix: str, args: str, context: TransportContext) -> str | None:
        decision = self.policy_service.authorize_command(prefix, args, context)
        if decision.allowed:
            return None
        return decision.message or f"Command/skill `{prefix}` ditolak oleh policy."

    def _looks_like_direct_skill_invocation(self, command: str) -> bool:
        token = command.strip().split(maxsplit=1)[0] if command.strip() else ""
        if "-" not in token and "_" not in token:
            return False
        return bool(self.DIRECT_SKILL_TOKEN_PATTERN.fullmatch(token))

    def _record_route(
        self,
        context: TransportContext,
        *,
        route_kind: str,
        target: str,
        routed_command: str,
    ) -> None:
        record_execution_metric("command_routed", status=route_kind, source=context.source)
        if context.trace_id:
            append_execution_event(
                "command_routed",
                trace_id=context.trace_id,
                status=route_kind,
                source=context.source,
                command=routed_command,
                data={
                    "route_kind": route_kind,
                    "target": target,
                },
            )

    def _heuristic_route(self, command: str) -> str | None:
        text = command.strip()
        lowered = text.lower()
        if not lowered:
            return None

        if any(token in lowered for token in ("lihat status runtime", "status runtime", "kondisi runtime", "health runtime")):
            return "observe status"
        if any(token in lowered for token in ("lihat alert aktif", "alert aktif", "warning aktif", "monitor kondisi")):
            return "monitor alerts"
        if any(token in lowered for token in ("pilih next action terbaik", "langkah terbaik berikutnya", "aksi terbaik berikutnya")):
            return "decide next"
        if lowered.startswith("kirim notifikasi "):
            message = text[len("kirim notifikasi ") :].strip()
            if message:
                return f"notify send {message}"
        if lowered.startswith("baca "):
            path_text = text[len("baca ") :].strip()
            if self.FILE_READ_PATTERN.fullmatch(path_text):
                return f"workspace read {path_text}"
        if (
            "struktur" in lowered
            and any(token in lowered for token in ("workspace", "project", "proyek", "repo", "repository"))
        ):
            return "workspace tree ."
        if any(token in lowered for token in ("jalankan scheduler sekali", "run scheduler sekali", "run scheduler once")):
            return "schedule run"
        return None
