"""Episodic learning derived from durable execution history."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from cadiax.core import agent_context
from cadiax.core.execution_history import load_execution_events


class EpisodicLearningService:
    """Build lightweight episode summaries from recent traces."""

    def refresh(self, *, limit: int = 250) -> dict[str, Any]:
        """Recompute episodic learning state from recent execution history."""
        events = load_execution_events(limit=limit)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            trace_id = str(event.get("trace_id") or "").strip()
            if not trace_id:
                continue
            grouped[trace_id].append(event)

        episodes: list[dict[str, Any]] = []
        for trace_id, trace_events in grouped.items():
            rendered = self._render_episode(trace_id, trace_events)
            if rendered is None:
                continue
            episodes.append(rendered)

        episodes.sort(key=lambda item: str(item.get("last_timestamp", "")), reverse=True)
        state = {
            "episodes": episodes[:12],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "episodes_analyzed": len(grouped),
        }
        agent_context.save_episode_state(state)
        return state

    def load_or_refresh(self) -> dict[str, Any]:
        """Return persisted episodic learning state, refreshing if empty."""
        state = agent_context.load_episode_state()
        if state.get("episodes"):
            return state
        return self.refresh()

    def list_episodes(self, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return the most recent episodic summaries."""
        state = self.load_or_refresh()
        return list(state.get("episodes", []))[: max(1, limit)]

    def _render_episode(self, trace_id: str, events: list[dict[str, Any]]) -> dict[str, Any] | None:
        completed = [event for event in events if str(event.get("event_type", "")).endswith("_completed")]
        if not completed:
            return None
        first = min(events, key=lambda item: str(item.get("timestamp", "")))
        last = max(events, key=lambda item: str(item.get("timestamp", "")))
        commands = [
            str(event.get("command", "")).strip()
            for event in events
            if str(event.get("command", "")).strip()
        ]
        command = commands[0] if commands else ""
        statuses = [
            str(event.get("status", "")).strip()
            for event in completed
            if str(event.get("status", "")).strip()
        ]
        dominant_status = statuses[-1] if statuses else ""
        result_preview = ""
        for event in reversed(completed):
            data = event.get("data") or {}
            if isinstance(data, dict):
                result_preview = str(data.get("result_preview") or data.get("summary") or "").strip()
                if result_preview:
                    break
        summary_parts = []
        if command:
            summary_parts.append(f"command `{command}`")
        if dominant_status:
            summary_parts.append(f"berakhir `{dominant_status}`")
        sources = sorted({str(event.get("source", "")).strip() for event in events if str(event.get("source", "")).strip()})
        if sources:
            summary_parts.append(f"sumber {', '.join(sources)}")
        if result_preview:
            summary_parts.append(f"hasil {result_preview[:120]}")
        return {
            "trace_id": trace_id,
            "first_timestamp": str(first.get("timestamp", "")),
            "last_timestamp": str(last.get("timestamp", "")),
            "command": command,
            "status": dominant_status,
            "event_count": len(events),
            "sources": sources,
            "summary": "Episode: " + " | ".join(summary_parts),
        }
