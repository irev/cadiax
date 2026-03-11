"""Habit model derived from durable execution history."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from otonomassist.core import agent_context
from otonomassist.core.execution_history import load_execution_events


class HabitModelService:
    """Infer lightweight user/assistant habits from recent execution traces."""

    def refresh(self, *, limit: int = 200) -> dict[str, Any]:
        """Recompute the habit model from recent execution history."""
        events = [
            event
            for event in load_execution_events(limit=limit)
            if event.get("event_type") == "command_completed"
        ]
        source_counts: Counter[str] = Counter()
        status_counts: Counter[str] = Counter()
        command_prefix_counts: Counter[str] = Counter()

        for event in events:
            source = str(event.get("source") or "").strip().lower()
            if source:
                source_counts[source] += 1
            status = str(event.get("status") or "").strip().lower()
            if status:
                status_counts[status] += 1
            command = str(event.get("command") or "").strip().lower()
            prefix = command.split(" ", 1)[0] if command else ""
            if prefix:
                command_prefix_counts[prefix] += 1

        habits: list[dict[str, Any]] = []
        if source_counts:
            source, count = source_counts.most_common(1)[0]
            habits.append(
                {
                    "kind": "preferred_source",
                    "value": source,
                    "confidence": _confidence(count, len(events)),
                    "evidence_count": count,
                    "summary": f"Interaksi paling sering datang dari {source}.",
                }
            )
        for prefix, count in command_prefix_counts.most_common(3):
            if count < 2:
                continue
            habits.append(
                {
                    "kind": "frequent_command_prefix",
                    "value": prefix,
                    "confidence": _confidence(count, len(events)),
                    "evidence_count": count,
                    "summary": f"Prefix command `{prefix}` sering dipakai.",
                }
            )
        if status_counts:
            success_count = status_counts.get("ok", 0) + status_counts.get("done", 0)
            if success_count:
                habits.append(
                    {
                        "kind": "successful_usage_pattern",
                        "value": "stable",
                        "confidence": _confidence(success_count, len(events)),
                        "evidence_count": success_count,
                        "summary": "Mayoritas command recent selesai tanpa error.",
                    }
                )

        state = {
            "habits": habits,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "signals_analyzed": len(events),
        }
        agent_context.save_habit_state(state)
        return state

    def load_or_refresh(self) -> dict[str, Any]:
        """Return the current habit model, refreshing it when empty."""
        state = agent_context.load_habit_state()
        if state.get("habits"):
            return state
        return self.refresh()

    def list_habits(self, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return the most relevant habits."""
        state = self.load_or_refresh()
        habits = list(state.get("habits", []))
        habits.sort(key=lambda item: (-int(item.get("evidence_count", 0) or 0), str(item.get("kind") or "")))
        return habits[: max(1, limit)]


def _confidence(count: int, total: int) -> str:
    if total <= 0:
        return "low"
    ratio = count / max(1, total)
    if ratio >= 0.6:
        return "high"
    if ratio >= 0.3:
        return "medium"
    return "low"
