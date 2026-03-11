"""Notification dispatch service for operator and automation surfaces."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import otonomassist.core.agent_context as agent_context
from otonomassist.core.event_bus import publish_event


class NotificationDispatcher:
    """Durable notification dispatcher with event-bus projection."""

    def dispatch(
        self,
        *,
        channel: str,
        title: str,
        message: str,
        trace_id: str = "",
        target: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record and publish one notification dispatch."""
        state = agent_context.load_notification_state()
        notifications = state.setdefault("notifications", [])
        payload = {
            "id": len(notifications) + 1,
            "channel": channel.strip() or "internal",
            "title": title.strip() or "Notification",
            "message": message.strip(),
            "target": target.strip(),
            "trace_id": trace_id.strip(),
            "metadata": metadata or {},
            "created_at": _utc_now_iso(),
        }
        notifications.append(payload)
        state["updated_at"] = payload["created_at"]
        agent_context.save_notification_state(state)
        publish_event(
            "notification.dispatch",
            event_type="notification_dispatched",
            trace_id=trace_id,
            source=payload["channel"],
            data={
                "title": payload["title"],
                "target": payload["target"],
                "notification_id": payload["id"],
                "metadata": payload["metadata"],
            },
        )
        return payload

    def get_snapshot(self) -> dict[str, Any]:
        """Return machine-readable notification history summary."""
        state = agent_context.load_notification_state()
        notifications = state.get("notifications", [])
        by_channel: dict[str, int] = {}
        for item in notifications:
            channel = str(item.get("channel", "") or "internal")
            by_channel[channel] = by_channel.get(channel, 0) + 1
        latest = notifications[-1] if notifications else {}
        return {
            "notification_count": len(notifications),
            "by_channel": by_channel,
            "latest_notification": latest,
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
