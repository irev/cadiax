"""Privacy governance controls for quiet hours, consent, export, and deletion."""

from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path
from typing import Any

import otonomassist.core.agent_context as agent_context
from otonomassist.core.execution_history import append_execution_event, new_trace_id


class PrivacyControlService:
    """Manage privacy controls and user-visible data governance."""

    def get_settings(self) -> dict[str, Any]:
        """Return the current privacy control state."""
        return agent_context.load_privacy_control_state()

    def set_quiet_hours(self, *, start: str, end: str, enabled: bool = True) -> dict[str, Any]:
        """Persist quiet-hours configuration."""
        state = self.get_settings()
        state["quiet_hours"] = {
            "enabled": bool(enabled),
            "start": _normalize_clock_text(start),
            "end": _normalize_clock_text(end),
        }
        state["updated_at"] = _utc_now_iso()
        agent_context.save_privacy_control_state(state)
        append_execution_event(
            "privacy_controls_updated",
            trace_id=new_trace_id(),
            status="ok",
            source="privacy",
            command="privacy quiet-hours",
            data={"quiet_hours": state["quiet_hours"]},
        )
        return state

    def set_proactive_controls(
        self,
        *,
        proactive_enabled: bool | None = None,
        consent_required: bool | None = None,
        memory_retention_days: int | None = None,
    ) -> dict[str, Any]:
        """Persist proactive assistance and retention controls."""
        state = self.get_settings()
        if proactive_enabled is not None:
            state["proactive_assistance_enabled"] = bool(proactive_enabled)
        if consent_required is not None:
            state["consent_required_for_proactive"] = bool(consent_required)
        if memory_retention_days is not None:
            state["memory_retention_days"] = max(1, int(memory_retention_days))
        state["updated_at"] = _utc_now_iso()
        agent_context.save_privacy_control_state(state)
        append_execution_event(
            "privacy_controls_updated",
            trace_id=new_trace_id(),
            status="ok",
            source="privacy",
            command="privacy controls",
            data={
                "proactive_assistance_enabled": state["proactive_assistance_enabled"],
                "consent_required_for_proactive": state["consent_required_for_proactive"],
                "memory_retention_days": state["memory_retention_days"],
            },
        )
        return state

    def is_quiet_hours(self, now: datetime | None = None) -> bool:
        """Return whether quiet hours are currently active."""
        state = self.get_settings()
        quiet = state.get("quiet_hours", {})
        if not bool(quiet.get("enabled", False)):
            return False
        current = (now or datetime.now().astimezone()).time()
        start = _parse_clock(str(quiet.get("start", "22:00") or "22:00"))
        end = _parse_clock(str(quiet.get("end", "07:00") or "07:00"))
        if start == end:
            return True
        if start < end:
            return start <= current < end
        return current >= start or current < end

    def should_defer_proactive(self, metadata: dict[str, Any] | None = None, now: datetime | None = None) -> tuple[bool, str]:
        """Return whether a proactive action should be deferred or denied."""
        state = self.get_settings()
        payload = metadata or {}
        is_proactive = bool(payload.get("proactive", False))
        if not is_proactive:
            return False, ""
        if not bool(state.get("proactive_assistance_enabled", True)):
            return True, "proactive_assistance_disabled"
        if bool(state.get("consent_required_for_proactive", True)) and not bool(payload.get("user_consented", False)):
            return True, "proactive_consent_required"
        if not bool(payload.get("allow_during_quiet_hours", False)) and self.is_quiet_hours(now=now):
            return True, "quiet_hours_active"
        return False, ""

    def get_diagnostics(self) -> dict[str, Any]:
        """Return machine-readable privacy governance diagnostics."""
        state = self.get_settings()
        memories = agent_context.load_all_memories()
        return {
            "quiet_hours": state.get("quiet_hours", {}),
            "quiet_hours_active": self.is_quiet_hours(),
            "consent_required_for_proactive": bool(state.get("consent_required_for_proactive", True)),
            "proactive_assistance_enabled": bool(state.get("proactive_assistance_enabled", True)),
            "memory_retention_days": int(state.get("memory_retention_days", 365) or 365),
            "memory_entry_count": len(memories),
            "memory_summary_count": len(agent_context.load_memory_summary_state().get("summaries", [])),
            "updated_at": str(state.get("updated_at", "")),
        }

    def export_user_data(self) -> dict[str, Any]:
        """Export privacy-relevant user data for local inspection or download."""
        return {
            "privacy_controls": self.get_settings(),
            "memory_entries": agent_context.load_all_memories(),
            "memory_summaries": agent_context.load_memory_summary_state(),
            "preferences": agent_context.load_preference_state(),
            "habits": agent_context.load_habit_state(),
            "identities": agent_context.load_identity_state(),
            "sessions": agent_context.load_session_state(),
            "notifications": agent_context.load_notification_state(),
            "email": agent_context.load_email_message_state(),
            "whatsapp": agent_context.load_whatsapp_message_state(),
        }

    def export_user_data_to_path(self, output_path: Path) -> Path:
        """Write exported user data to a JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.export_user_data(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        append_execution_event(
            "privacy_export_completed",
            trace_id=new_trace_id(),
            status="ok",
            source="privacy",
            command="privacy export",
            data={"output_path": str(output_path)},
        )
        return output_path

    def delete_memory_data(self) -> dict[str, int]:
        """Delete stored memory journal and summary state."""
        memory_count = len(agent_context.load_all_memories())
        summary_count = len(agent_context.load_memory_summary_state().get("summaries", []))
        agent_context.replace_memory_entries([])
        agent_context.save_memory_summary_state(
            {"summaries": [], "updated_at": _utc_now_iso(), "prune_candidates": 0}
        )
        append_execution_event(
            "privacy_delete_completed",
            trace_id=new_trace_id(),
            status="ok",
            source="privacy",
            command="privacy delete-memory",
            data={"deleted_memory_entries": memory_count, "deleted_memory_summaries": summary_count},
        )
        return {
            "deleted_memory_entries": memory_count,
            "deleted_memory_summaries": summary_count,
        }


def _normalize_clock_text(value: str) -> str:
    parsed = _parse_clock(value)
    return f"{parsed.hour:02d}:{parsed.minute:02d}"


def _parse_clock(value: str) -> time:
    text = (value or "").strip()
    try:
        hour_text, minute_text = text.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as exc:
        raise ValueError("clock value must use HH:MM format") from exc
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("clock value must use valid 24-hour time")
    return time(hour=hour, minute=minute)


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
