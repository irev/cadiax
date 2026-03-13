"""Durable internal event bus for runtime triggers and automation observability."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any
import uuid

import otonomassist.core.agent_context as agent_context
from otonomassist.storage import SQLiteStateStore


def publish_event(
    topic: str,
    *,
    event_type: str,
    trace_id: str = "",
    source: str = "",
    data: dict[str, Any] | None = None,
    timestamp: str | None = None,
    bus_event_id: str | None = None,
) -> dict[str, Any]:
    """Publish one durable event into the internal event bus."""
    agent_context.ensure_agent_storage()
    payload = {
        "bus_event_id": bus_event_id or uuid.uuid4().hex,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "topic": topic.strip() or "runtime.misc",
        "event_type": event_type.strip(),
        "trace_id": trace_id.strip(),
        "source": source.strip(),
        "data": data or {},
    }
    _get_state_store().append_event_bus_event(payload)
    return payload


def publish_execution_event(event: dict[str, Any]) -> dict[str, Any]:
    """Project one execution-history event onto the internal event bus."""
    payload_data = dict(event.get("data") or {})
    if event.get("status") is not None:
        payload_data.setdefault("status", str(event.get("status") or ""))
    return publish_event(
        _derive_topic(str(event.get("event_type") or "")),
        event_type=str(event.get("event_type") or ""),
        trace_id=str(event.get("trace_id") or ""),
        source=str(event.get("source") or ""),
        data=payload_data,
        timestamp=str(event.get("timestamp") or ""),
        bus_event_id=str(event.get("event_id") or "") or None,
    )


def load_event_bus_events(limit: int = 20) -> list[dict[str, Any]]:
    """Load recent internal event bus events."""
    _sync_from_execution_history_if_needed()
    return _get_state_store().load_event_bus_events(limit=limit)


def get_event_bus_snapshot(
    limit: int = 100,
    *,
    agent_scope: str | None = None,
    roles: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Summarize the current internal event bus state for operator diagnostics."""
    events = load_event_bus_events(limit=max(20, limit))
    if agent_scope:
        events = _filter_bus_events(events, agent_scope=agent_scope, roles=roles)
    topic_counts = Counter(event.get("topic", "") for event in events if event.get("topic"))
    total_events = len(events) if agent_scope else _get_state_store().count_event_bus_events()
    last_event = events[-1] if events else {}
    return {
        "status": "healthy" if total_events > 0 else "warning",
        "total_events": total_events,
        "returned_events": len(events),
        "last_event_at": str(last_event.get("timestamp", "")),
        "last_event_topic": str(last_event.get("topic", "")),
        "last_event_type": str(last_event.get("event_type", "")),
        "topics": dict(sorted(topic_counts.items())),
        "automation_event_count": sum(
            1 for event in events if str(event.get("topic", "")).startswith("automation.")
        ),
        "policy_event_count": sum(
            1 for event in events if str(event.get("topic", "")).startswith("policy.")
        ),
        "external_event_count": sum(
            1 for event in events if str(event.get("topic", "")).startswith("external.")
        ),
        "events": events,
    }


def render_event_bus(limit: int = 20) -> str:
    """Render recent internal event bus entries."""
    snapshot = get_event_bus_snapshot(limit=max(20, limit))
    lines = [
        "Internal Event Bus",
        "",
        "[Summary]",
        f"- total_events: {snapshot['total_events']}",
        f"- returned_events: {snapshot['returned_events']}",
        f"- automation_event_count: {snapshot['automation_event_count']}",
        f"- policy_event_count: {snapshot['policy_event_count']}",
        f"- external_event_count: {snapshot['external_event_count']}",
        f"- last_event_topic: {snapshot['last_event_topic'] or '-'}",
        f"- last_event_type: {snapshot['last_event_type'] or '-'}",
    ]
    lines.extend(["", "[Topics]"])
    if snapshot["topics"]:
        for topic, count in snapshot["topics"].items():
            lines.append(f"- {topic}: {count}")
    else:
        lines.append("- belum ada topic")

    lines.extend(["", "[Events]"])
    if not snapshot["events"]:
        lines.append("- belum ada event bus entry")
        return "\n".join(lines)

    for event in snapshot["events"][-limit:]:
        lines.append(
            f"- {event.get('timestamp')} {event.get('topic')}::{event.get('event_type')} "
            f"[trace={event.get('trace_id') or '-'}, source={event.get('source') or '-'}]"
        )
    return "\n".join(lines)


def _derive_topic(event_type: str) -> str:
    normalized = event_type.strip().lower()
    if normalized.startswith("interaction_"):
        return "interaction.message"
    if normalized.startswith("command_"):
        return "interaction.command"
    if normalized.startswith("ai_route_"):
        return "ai.route"
    if normalized.startswith("policy_"):
        return "policy.decision"
    if normalized.startswith("skill_"):
        return "execution.skill"
    if normalized.startswith("job_"):
        return "automation.job"
    if normalized.startswith("task_execution_"):
        return "automation.task"
    if normalized.startswith("worker_cycle_"):
        return "automation.worker"
    if normalized.startswith("scheduler_"):
        return "automation.scheduler"
    if normalized.startswith("service_"):
        return "runtime.service"
    if normalized.startswith("external_"):
        return "external.runtime"
    return "runtime.misc"


def _get_state_store() -> SQLiteStateStore:
    return SQLiteStateStore(agent_context.get_state_db_path())


def _sync_from_execution_history_if_needed() -> None:
    store = _get_state_store()
    if store.count_event_bus_events() > 0:
        return
    for event in store.load_execution_events(limit=500):
        publish_execution_event(event)


def _filter_bus_events(
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
