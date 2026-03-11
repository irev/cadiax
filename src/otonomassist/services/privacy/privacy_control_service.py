"""Privacy governance controls for quiet hours, consent, export, and deletion."""

from __future__ import annotations

import json
from datetime import datetime, time, timedelta, timezone
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
        retention_candidates = self.get_retention_candidates()
        return {
            "quiet_hours": state.get("quiet_hours", {}),
            "quiet_hours_active": self.is_quiet_hours(),
            "consent_required_for_proactive": bool(state.get("consent_required_for_proactive", True)),
            "proactive_assistance_enabled": bool(state.get("proactive_assistance_enabled", True)),
            "memory_retention_days": int(state.get("memory_retention_days", 365) or 365),
            "memory_entry_count": len(memories),
            "memory_summary_count": len(agent_context.load_memory_summary_state().get("summaries", [])),
            "notification_count": len(agent_context.load_notification_state().get("notifications", [])),
            "email_count": len(agent_context.load_email_message_state().get("messages", [])),
            "whatsapp_count": len(agent_context.load_whatsapp_message_state().get("messages", [])),
            "episode_count": len(agent_context.load_episode_state().get("episodes", [])),
            "proactive_insight_count": len(agent_context.load_proactive_insight_state().get("insights", [])),
            "retention_candidates": retention_candidates,
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
            "episodes": agent_context.load_episode_state(),
            "proactive_insights": agent_context.load_proactive_insight_state(),
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

    def delete_personal_data(self) -> dict[str, int]:
        """Delete personal-data stores across privacy-relevant runtime state."""
        result = {
            "deleted_memory_entries": len(agent_context.load_all_memories()),
            "deleted_memory_summaries": len(agent_context.load_memory_summary_state().get("summaries", [])),
            "deleted_preferences": len(agent_context.load_preference_state().get("preferences", [])),
            "deleted_habits": len(agent_context.load_habit_state().get("habits", [])),
            "deleted_identities": len(agent_context.load_identity_state().get("identities", [])),
            "deleted_sessions": len(agent_context.load_session_state().get("sessions", [])),
            "deleted_notifications": len(agent_context.load_notification_state().get("notifications", [])),
            "deleted_email_messages": len(agent_context.load_email_message_state().get("messages", [])),
            "deleted_whatsapp_messages": len(agent_context.load_whatsapp_message_state().get("messages", [])),
            "deleted_episodes": len(agent_context.load_episode_state().get("episodes", [])),
            "deleted_proactive_insights": len(agent_context.load_proactive_insight_state().get("insights", [])),
        }
        agent_context.replace_memory_entries([])
        agent_context.save_memory_summary_state({"summaries": [], "updated_at": _utc_now_iso(), "prune_candidates": 0})
        agent_context.save_preference_state({"preferences": [], "profile": {}})
        agent_context.save_habit_state({"habits": [], "updated_at": _utc_now_iso(), "signals_analyzed": 0})
        agent_context.save_identity_state({"identities": [], "updated_at": _utc_now_iso()})
        agent_context.save_session_state({"sessions": [], "updated_at": _utc_now_iso()})
        agent_context.save_notification_state({"notifications": [], "updated_at": _utc_now_iso()})
        agent_context.save_email_message_state({"messages": [], "updated_at": _utc_now_iso()})
        agent_context.save_whatsapp_message_state({"messages": [], "updated_at": _utc_now_iso()})
        agent_context.save_episode_state({"episodes": [], "updated_at": _utc_now_iso(), "episodes_analyzed": 0})
        agent_context.save_proactive_insight_state({"insights": [], "updated_at": _utc_now_iso(), "insights_generated": 0})
        append_execution_event(
            "privacy_delete_completed",
            trace_id=new_trace_id(),
            status="ok",
            source="privacy",
            command="privacy delete-personal-data",
            data=result,
        )
        return result

    def get_retention_candidates(self, now: datetime | None = None) -> dict[str, int]:
        """Count records older than the configured retention window."""
        cutoff = self._get_retention_cutoff(now=now)
        return {
            "memory_entries": _count_older_than(agent_context.load_all_memories(), "timestamp", cutoff),
            "notifications": _count_older_than(agent_context.load_notification_state().get("notifications", []), "created_at", cutoff),
            "email_messages": _count_older_than(agent_context.load_email_message_state().get("messages", []), "created_at", cutoff),
            "whatsapp_messages": _count_older_than(agent_context.load_whatsapp_message_state().get("messages", []), "created_at", cutoff),
            "episodes": _count_older_than(agent_context.load_episode_state().get("episodes", []), "last_timestamp", cutoff),
            "proactive_insights": _count_older_than(agent_context.load_proactive_insight_state().get("insights", []), "created_at", cutoff),
        }

    def prune_expired_personal_data(self, now: datetime | None = None) -> dict[str, int]:
        """Prune records older than the configured retention window."""
        cutoff = self._get_retention_cutoff(now=now)
        result = {
            "memory_entries": self._prune_memories(cutoff),
            "notifications": self._prune_state_items(
                agent_context.load_notification_state,
                agent_context.save_notification_state,
                "notifications",
                "created_at",
                cutoff,
            ),
            "email_messages": self._prune_state_items(
                agent_context.load_email_message_state,
                agent_context.save_email_message_state,
                "messages",
                "created_at",
                cutoff,
            ),
            "whatsapp_messages": self._prune_state_items(
                agent_context.load_whatsapp_message_state,
                agent_context.save_whatsapp_message_state,
                "messages",
                "created_at",
                cutoff,
            ),
            "episodes": self._prune_state_items(
                agent_context.load_episode_state,
                agent_context.save_episode_state,
                "episodes",
                "last_timestamp",
                cutoff,
                {"episodes_analyzed": agent_context.load_episode_state().get("episodes_analyzed", 0)},
            ),
            "proactive_insights": self._prune_state_items(
                agent_context.load_proactive_insight_state,
                agent_context.save_proactive_insight_state,
                "insights",
                "created_at",
                cutoff,
                {"insights_generated": agent_context.load_proactive_insight_state().get("insights_generated", 0)},
            ),
        }
        append_execution_event(
            "privacy_prune_completed",
            trace_id=new_trace_id(),
            status="ok",
            source="privacy",
            command="privacy prune",
            data={"cutoff": cutoff.isoformat(), "deleted": result},
        )
        return result

    def _get_retention_cutoff(self, now: datetime | None = None) -> datetime:
        settings = self.get_settings()
        retention_days = int(settings.get("memory_retention_days", 365) or 365)
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current - timedelta(days=max(1, retention_days))

    def _prune_memories(self, cutoff: datetime) -> int:
        entries = agent_context.load_all_memories()
        retained = [entry for entry in entries if not _is_older_than(entry, "timestamp", cutoff)]
        deleted = len(entries) - len(retained)
        agent_context.replace_memory_entries(retained)
        return deleted

    def _prune_state_items(
        self,
        loader: Any,
        saver: Any,
        collection_key: str,
        timestamp_key: str,
        cutoff: datetime,
        extra_fields: dict[str, Any] | None = None,
    ) -> int:
        state = loader()
        items = list(state.get(collection_key, []))
        retained = [item for item in items if not _is_older_than(item, timestamp_key, cutoff)]
        deleted = len(items) - len(retained)
        next_state = {collection_key: retained, "updated_at": _utc_now_iso()}
        if extra_fields:
            next_state.update(extra_fields)
        saver(next_state)
        return deleted


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


def _count_older_than(items: list[dict[str, Any]], field: str, cutoff: datetime) -> int:
    return sum(1 for item in items if _is_older_than(item, field, cutoff))


def _is_older_than(item: dict[str, Any], field: str, cutoff: datetime) -> bool:
    value = str(item.get(field, "") or "").strip()
    parsed = _parse_datetime(value)
    return parsed is not None and parsed < cutoff


def _parse_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
