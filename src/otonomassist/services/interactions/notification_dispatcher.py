"""Notification dispatch service for operator and automation surfaces."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

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
        from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

        should_defer, reason = PrivacyControlService().should_defer_proactive(metadata)
        if should_defer:
            payload = self._record_notification(
                channel=channel,
                title=title,
                message=message,
                trace_id=trace_id,
                target=target,
                metadata={**(metadata or {}), "deferred_reason": reason},
                status="deferred",
            )
            publish_event(
                "notification.deferred",
                event_type="notification_deferred",
                trace_id=trace_id,
                source=payload["channel"],
                data={
                    "notification_id": payload["id"],
                    "target": payload["target"],
                    "reason": reason,
                },
            )
            return payload
        return self._record_notification(
            channel=channel,
            title=title,
            message=message,
            trace_id=trace_id,
            target=target,
            metadata=metadata,
        )

    def dispatch_many(
        self,
        *,
        title: str,
        message: str,
        deliveries: list[dict[str, Any]],
        trace_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dispatch one notification batch across multiple channels."""
        batch_id = uuid.uuid4().hex
        shared_metadata = dict(metadata or {})
        shared_metadata["notification_batch_id"] = batch_id
        results: list[dict[str, Any]] = []
        for index, delivery in enumerate(deliveries, start=1):
            channel = str(delivery.get("channel") or "internal").strip() or "internal"
            target = str(delivery.get("target") or delivery.get("to") or "").strip()
            delivery_metadata = dict(shared_metadata)
            raw_metadata = delivery.get("metadata")
            if isinstance(raw_metadata, dict):
                delivery_metadata.update(raw_metadata)
            delivery_metadata["delivery_index"] = index
            from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

            should_defer, reason = PrivacyControlService().should_defer_proactive(delivery_metadata)
            notification = self._record_notification(
                channel=channel,
                title=str(delivery.get("title") or title).strip() or "Notification",
                message=str(delivery.get("message") or message).strip(),
                trace_id=trace_id,
                target=target,
                metadata={
                    **delivery_metadata,
                    **({"deferred_reason": reason} if should_defer else {}),
                },
                status="deferred" if should_defer else "queued",
            )
            if should_defer:
                publish_event(
                    "notification.deferred",
                    event_type="notification_deferred",
                    trace_id=trace_id,
                    source=channel,
                    data={
                        "notification_id": notification["id"],
                        "target": target,
                        "reason": reason,
                    },
                )
            else:
                self._project_delivery(
                    channel=channel,
                    target=target,
                    title=notification["title"],
                    message=notification["message"],
                    trace_id=trace_id,
                    metadata=delivery_metadata,
                    notification_id=int(notification["id"]),
                )
            results.append(notification)
        publish_event(
            "notification.batch",
            event_type="notification_batch_dispatched",
            trace_id=trace_id,
            source="notification-dispatcher",
            data={
                "batch_id": batch_id,
                "delivery_count": len(results),
                "channels": [item["channel"] for item in results],
            },
        )
        return {
            "batch_id": batch_id,
            "delivery_count": len(results),
            "notifications": results,
        }

    def get_snapshot(self) -> dict[str, Any]:
        """Return machine-readable notification history summary."""
        state = agent_context.load_notification_state()
        notifications = state.get("notifications", [])
        by_channel: dict[str, int] = {}
        batch_ids: set[str] = set()
        for item in notifications:
            channel = str(item.get("channel", "") or "internal")
            by_channel[channel] = by_channel.get(channel, 0) + 1
            batch_id = str(item.get("metadata", {}).get("notification_batch_id", "") or "")
            if batch_id:
                batch_ids.add(batch_id)
        latest = notifications[-1] if notifications else {}
        return {
            "notification_count": len(notifications),
            "by_channel": by_channel,
            "delivery_batch_count": len(batch_ids),
            "latest_notification": latest,
        }

    def _record_notification(
        self,
        *,
        channel: str,
        title: str,
        message: str,
        trace_id: str = "",
        target: str = "",
        metadata: dict[str, Any] | None = None,
        status: str = "queued",
    ) -> dict[str, Any]:
        state = agent_context.load_notification_state()
        notifications = state.setdefault("notifications", [])
        payload = {
            "id": len(notifications) + 1,
            "channel": channel.strip() or "internal",
            "title": title.strip() or "Notification",
            "message": message.strip(),
            "target": target.strip(),
            "trace_id": trace_id.strip(),
            "status": status.strip() or "queued",
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

    def _project_delivery(
        self,
        *,
        channel: str,
        target: str,
        title: str,
        message: str,
        trace_id: str,
        metadata: dict[str, Any],
        notification_id: int,
    ) -> None:
        if channel == "email":
            from otonomassist.interfaces.email import EmailInterfaceService

            EmailInterfaceService().send(
                to_address=target,
                subject=title,
                body=message,
                trace_id=trace_id,
                metadata=metadata,
                record_notification=False,
                notification_id=notification_id,
            )
            return
        if channel == "whatsapp":
            from otonomassist.interfaces.whatsapp import WhatsAppInterfaceService

            WhatsAppInterfaceService().send(
                phone_number=target,
                body=message,
                display_name=str(metadata.get("display_name") or ""),
                trace_id=trace_id,
                metadata=metadata,
                record_notification=False,
                notification_id=notification_id,
            )
            return
        if channel == "webhook":
            publish_event(
                "notification.webhook",
                event_type="notification_webhook_dispatched",
                trace_id=trace_id,
                source="webhook",
                data={
                    "notification_id": notification_id,
                    "target": target,
                    "title": title,
                    "metadata": metadata,
                },
            )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
