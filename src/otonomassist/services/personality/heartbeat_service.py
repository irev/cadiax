"""Heartbeat service for autonomous runtime rhythm."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from otonomassist.core import agent_context
from otonomassist.core.execution_history import append_execution_event, new_trace_id
from otonomassist.core.job_runtime import get_job_queue_summary
from otonomassist.core.scheduler_runtime import get_scheduler_summary
from otonomassist.core.workspace_guard import get_workspace_root
from otonomassist.services.personality.proactive_assistance_service import ProactiveAssistanceService
from otonomassist.services.privacy.privacy_control_service import PrivacyControlService


class HeartbeatService:
    """Translate runtime state into a durable heartbeat pulse."""

    def __init__(self, document_path: Path | None = None) -> None:
        self.document_path = document_path or (get_workspace_root() / "HEARTBEAT.md")

    def show_heartbeat(self, max_chars: int = 1200) -> str:
        """Return the current heartbeat document."""
        agent_context.ensure_agent_storage()
        if not self.document_path.exists():
            return "- belum ada heartbeat guide yang ditetapkan"
        return agent_context.load_markdown(self.document_path, max_chars=max_chars)

    def pulse(self, *, trigger: str, trace_id: str = "") -> dict[str, Any]:
        """Capture one heartbeat pulse and refresh related insight state."""
        quiet_hours = PrivacyControlService().is_quiet_hours()
        runtime = get_job_queue_summary()
        planner = agent_context.load_planner_state()
        proactive = ProactiveAssistanceService().refresh()
        next_task = next((task for task in planner.get("tasks", []) if task.get("status") == "todo"), None)

        actions: list[str] = []
        mode = "reflective"
        summary = "Runtime idle; heartbeat menjaga konteks dan kesiapan."
        if quiet_hours:
            mode = "deferred"
            summary = "Heartbeat ditahan karena quiet hours aktif."
            actions.append("privacy show")
        elif int(runtime.get("queued_jobs", 0) or 0) > 0:
            mode = "active"
            summary = f"Heartbeat mendeteksi {runtime.get('queued_jobs')} job queued untuk diproses."
            actions.append("worker --until-idle")
        elif next_task:
            mode = "ready"
            summary = f"Heartbeat melihat task planner siap: #{next_task.get('id')} {next_task.get('text')}"
            actions.append("jobs enqueue")

        top_insight = next((item for item in proactive.get("insights", [])), None)
        if top_insight and str(top_insight.get("suggested_action", "")).strip():
            actions.append(str(top_insight["suggested_action"]))

        previous = agent_context.load_heartbeat_state()
        state = {
            "pulse_count": int(previous.get("pulse_count", 0) or 0) + 1,
            "last_pulse_at": datetime.now(timezone.utc).isoformat(),
            "last_mode": mode,
            "last_summary": summary,
            "last_trigger": trigger,
            "last_actions": _dedupe_actions(actions),
        }
        agent_context.save_heartbeat_state(state)
        append_execution_event(
            "heartbeat_pulse",
            trace_id=trace_id or new_trace_id(),
            status=mode,
            source="heartbeat",
            command=f"heartbeat {trigger}",
            data={
                "summary": summary,
                "actions": state["last_actions"],
                "scheduler_status": get_scheduler_summary().get("last_status", ""),
                "proactive_insight_count": len(proactive.get("insights", [])),
            },
        )
        return state

    def load_state(self) -> dict[str, Any]:
        """Return durable heartbeat state."""
        return agent_context.load_heartbeat_state()

    def load_or_pulse(self, *, trigger: str = "manual") -> dict[str, Any]:
        """Return heartbeat state, pulsing when empty."""
        state = self.load_state()
        if state.get("last_pulse_at"):
            return state
        return self.pulse(trigger=trigger)

    def render_report(self) -> str:
        """Render a human-readable heartbeat snapshot."""
        state = self.load_or_pulse(trigger="report")
        lines = [
            "Heartbeat",
            "",
            f"- pulse_count: {state.get('pulse_count', 0)}",
            f"- last_pulse_at: {state.get('last_pulse_at') or '-'}",
            f"- last_mode: {state.get('last_mode') or '-'}",
            f"- last_trigger: {state.get('last_trigger') or '-'}",
            f"- last_summary: {state.get('last_summary') or '-'}",
        ]
        for action in state.get("last_actions", []):
            lines.append(f"- action: {action}")
        return "\n".join(lines)


def _dedupe_actions(actions: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in actions:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result[:4]
