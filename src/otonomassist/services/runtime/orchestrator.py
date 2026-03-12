"""Runtime orchestration for canonical interactions."""

from __future__ import annotations

import re
from typing import Any

from otonomassist.core.admin_api import build_admin_snapshot
from otonomassist.core.config_doctor import get_config_status_report
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
            return self.assistant.get_help()

        if cmd_lower == "list":
            denied = self._authorize("list", "", context)
            if denied:
                return denied
            return self.assistant.list_skills_str()

        if cmd_lower in {"history", "history recent"}:
            denied = self._authorize("history", "recent" if cmd_lower.endswith("recent") else "", context)
            if denied:
                return denied
            return self.assistant.render_execution_history()
        if cmd_lower in {"metrics", "metrics summary"}:
            denied = self._authorize("metrics", "summary" if cmd_lower.endswith("summary") else "", context)
            if denied:
                return denied
            return self.assistant.render_execution_metrics()
        if cmd_lower in {"jobs", "jobs list", "job queue"}:
            denied = self._authorize("jobs", "list" if cmd_lower != "job queue" else "queue", context)
            if denied:
                return denied
            return render_job_queue()
        if cmd_lower in {"api status", "admin status"}:
            denied = self._authorize("admin", "status", context)
            if denied:
                return denied
            _, payload = build_admin_snapshot("/status")
            return str(payload)
        if cmd_lower in {"jobs enqueue", "job enqueue"}:
            denied = self._authorize("jobs", "enqueue", context)
            if denied:
                return denied
            job = enqueue_ready_planner_task(trace_id=context.trace_id or "", source=context.source)
            if not job:
                return "Tidak ada task ready untuk dimasukkan ke job queue."
            return f"Job #{job['id']} dibuat untuk task #{job['task_id']} {job['task_text']}"

        if cmd_lower in {"external audit", "external list"}:
            denied = self._authorize("external", "audit" if cmd_lower.endswith("audit") else "list", context)
            if denied:
                return denied
            return render_external_asset_audit()
        if cmd_lower.startswith("external approve "):
            name = command.strip()[len("external approve ") :].strip()
            denied = self._authorize("external", f"approve {name}".strip(), context)
            if denied:
                return denied
            if not name:
                return "Gunakan: external approve <name>"
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
            try:
                asset = set_external_asset_approval(name, "rejected", actor="assistant")
            except Exception as exc:
                return f"External reject gagal: {exc}"
            return f"External asset `{asset['name']}` diset ke rejected."
        if cmd_lower == "external sync":
            denied = self._authorize("external", "sync", context)
            if denied:
                return denied
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
            try:
                result = install_external_skill(source, actor="assistant")
                return render_external_install_result(result)
            except Exception as exc:
                return f"External install gagal: {exc}"
        if cmd_lower in {"skills audit", "skill audit"}:
            denied = self._authorize("skills", "audit", context)
            if denied:
                return denied
            return self.assistant.render_skill_layer_audit()

        if cmd_lower in {"doctor", "config status", "config-status"}:
            denied = self._authorize("doctor", "status" if cmd_lower != "doctor" else "", context)
            if denied:
                return denied
            return get_config_status_report()

        if cmd_lower == "debug-config":
            denied = self._authorize("debug-config", "", context)
            if denied:
                return denied
            return self.assistant.get_debug_config()

        if cmd_lower == "list-models":
            denied = self._authorize("list-models", "", context)
            if denied:
                return denied
            return self.assistant.get_model_listing()

        for prefix in self.RESEARCH_PREFIXES:
            if cmd_lower.startswith(prefix):
                research_skill = self.assistant.registry.get("research")
                if research_skill:
                    query = command.strip()[len(prefix) :].strip()
                    denied = self._authorize("research", query, context)
                    if denied:
                        return denied
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
            return self.execution_service.execute_skill(
                skill,
                args,
                original_command=command,
                trace_id=context.trace_id or "",
            )

        if self._looks_like_direct_skill_invocation(command):
            skill_name = command.strip().split(maxsplit=1)[0]
            return f"Skill '{skill_name}' tidak ditemukan."

        if self.assistant.should_force_research(command):
            research_skill = self.assistant.registry.get("research")
            if research_skill:
                denied = self._authorize("research", command, context)
                if denied:
                    return denied
                return self.execution_service.execute_skill(
                    research_skill,
                    command,
                    original_command=command,
                    trace_id=context.trace_id or "",
                )

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
