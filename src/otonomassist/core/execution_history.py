"""Structured execution history and trace helpers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import otonomassist.core.agent_context as agent_context
from otonomassist.core.event_bus import publish_execution_event
from otonomassist.core.runtime_interaction import get_current_interaction_context
from otonomassist.storage import SQLiteStateStore
from otonomassist.core.workspace_guard import ensure_internal_state_write_allowed, ensure_read_allowed


def new_trace_id() -> str:
    """Generate a stable trace identifier for one inbound request flow."""
    return uuid.uuid4().hex


def append_execution_event(
    event_type: str,
    *,
    trace_id: str,
    status: str = "",
    source: str = "",
    command: str = "",
    skill_name: str = "",
    duration_ms: int | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one structured execution event to the local history log."""
    agent_context.ensure_agent_storage()
    _sync_execution_history_store()
    interaction = get_current_interaction_context()
    payload_data = dict(data or {})
    if interaction:
        payload_data.setdefault("agent_scope", str(interaction.get("agent_scope") or "default"))
        payload_data.setdefault("session_mode", str(interaction.get("session_mode") or "main"))
        payload_data.setdefault("roles", list(interaction.get("roles") or ()))
    event = {
        "event_id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "event_type": event_type,
        "status": status,
        "source": source,
        "command": _truncate_text(command),
        "skill_name": skill_name,
        "duration_ms": duration_ms,
        "data": payload_data,
    }
    ensure_internal_state_write_allowed(agent_context.EXECUTION_HISTORY_FILE)
    with agent_context.EXECUTION_HISTORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")
    _get_state_store().append_execution_event(event)
    publish_execution_event(event)
    return event


def load_execution_events(limit: int = 20) -> list[dict[str, Any]]:
    """Load the most recent execution events."""
    agent_context.ensure_agent_storage()
    _sync_execution_history_store()
    return _get_state_store().load_execution_events(limit=limit)


def export_execution_events(
    limit: int = 20,
    *,
    agent_scope: str | None = None,
    roles: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Export recent execution events as machine-readable data."""
    events = load_execution_events(limit=limit)
    if not agent_scope:
        return events
    return _filter_execution_events(events, agent_scope=agent_scope, roles=roles)


def render_execution_history(limit: int = 20) -> str:
    """Render recent execution history for operator-facing inspection."""
    events = load_execution_events(limit=limit)
    lines = [
        "Execution History",
        "",
        "[Summary]",
        f"- returned_events: {len(events)}",
    ]
    if not events:
        lines.extend(["", "[Events]", "- belum ada execution history"])
        return "\n".join(lines)

    lines.extend(["", "[Events]"])
    for event in events:
        header = (
            f"- {event.get('timestamp')} "
            f"{event.get('event_type')} "
            f"[trace={event.get('trace_id')}, status={event.get('status') or '-'}]"
        )
        lines.append(header)
        if event.get("source"):
            lines.append(f"  source: {event.get('source')}")
        if event.get("skill_name"):
            lines.append(f"  skill: {event.get('skill_name')}")
        if event.get("command"):
            lines.append(f"  command: {event.get('command')}")
        if event.get("duration_ms") is not None:
            lines.append(f"  duration_ms: {event.get('duration_ms')}")
        data = event.get("data") or {}
        if isinstance(data, dict):
            summary = _truncate_text(str(data.get("summary") or data.get("result_preview") or ""))
            if summary:
                lines.append(f"  detail: {summary}")
    return "\n".join(lines)


def filter_execution_events(
    limit: int = 20,
    *,
    agent_scope: str,
    roles: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Load and filter recent execution events by scope visibility."""
    return _filter_execution_events(load_execution_events(limit=limit), agent_scope=agent_scope, roles=roles)


def _truncate_text(value: str, limit: int = 240) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _get_state_store() -> SQLiteStateStore:
    return SQLiteStateStore(agent_context.get_state_db_path())


def _sync_execution_history_store() -> None:
    store = _get_state_store()
    if store.count_execution_events() > 0:
        return
    ensure_read_allowed(agent_context.EXECUTION_HISTORY_FILE)
    for line in agent_context.EXECUTION_HISTORY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            store.append_execution_event(event)


def _filter_execution_events(
    events: list[dict[str, Any]],
    *,
    agent_scope: str,
    roles: tuple[str, ...],
) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if agent_context._is_scope_visible(  # type: ignore[attr-defined]
            str((event.get("data") or {}).get("agent_scope") or "default"),
            str(agent_scope or "").strip().lower() or "default",
            roles=roles,
        )
    ]
