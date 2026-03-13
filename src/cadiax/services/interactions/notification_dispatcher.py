"""Notification dispatch service for operator and automation surfaces."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

import cadiax.core.agent_context as agent_context
from cadiax.core.event_bus import publish_event
from cadiax.core.runtime_interaction import get_current_interaction_context


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
        from cadiax.services.privacy.privacy_control_service import PrivacyControlService

        metadata_payload, agent_scope, roles = _resolve_delivery_context(metadata)
        should_defer, reason = PrivacyControlService().should_defer_proactive(metadata_payload)
        if should_defer:
            payload = self._record_notification(
                channel=channel,
                title=title,
                message=message,
                trace_id=trace_id,
                target=target,
                metadata={**metadata_payload, "deferred_reason": reason},
                status="deferred",
                agent_scope=agent_scope,
                roles=roles,
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
                    "agent_scope": agent_scope,
                    "roles": list(roles),
                },
            )
            return payload
        return self._record_notification(
            channel=channel,
            title=title,
            message=message,
            trace_id=trace_id,
            target=target,
            metadata=metadata_payload,
            agent_scope=agent_scope,
            roles=roles,
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
            delivery_metadata, agent_scope, roles = _resolve_delivery_context(delivery_metadata)
            from cadiax.services.privacy.privacy_control_service import PrivacyControlService

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
                agent_scope=agent_scope,
                roles=roles,
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
                        "agent_scope": agent_scope,
                        "roles": list(roles),
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
                    agent_scope=agent_scope,
                    roles=roles,
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
                "agent_scopes": sorted({str(item.get("agent_scope") or "default") for item in results}),
            },
        )
        return {
            "batch_id": batch_id,
            "delivery_count": len(results),
            "notifications": results,
        }

    def get_snapshot(
        self,
        *,
        agent_scope: str | None = None,
        roles: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Return machine-readable notification history summary."""
        state = agent_context.load_notification_state()
        notifications = list(state.get("notifications", []))
        filtered_notifications = (
            agent_context.filter_notification_entries_by_scope(
                notifications,
                agent_scope=agent_scope or "default",
                roles=roles,
            )
            if agent_scope
            else notifications
        )
        by_channel: dict[str, int] = {}
        by_scope: dict[str, int] = {}
        batch_ids: set[str] = set()
        for item in filtered_notifications:
            channel = str(item.get("channel", "") or "internal")
            by_channel[channel] = by_channel.get(channel, 0) + 1
            scope_name = str(item.get("agent_scope") or (item.get("metadata") or {}).get("agent_scope") or "default")
            by_scope[scope_name] = by_scope.get(scope_name, 0) + 1
            batch_id = str(item.get("metadata", {}).get("notification_batch_id", "") or "")
            if batch_id:
                batch_ids.add(batch_id)
        latest = filtered_notifications[-1] if filtered_notifications else {}
        return {
            "notification_count": len(filtered_notifications),
            "total_notification_count": len(notifications),
            "by_channel": by_channel,
            "by_scope": by_scope,
            "delivery_batch_count": len(batch_ids),
            "latest_notification": latest,
            "filter_agent_scope": str(agent_scope or ""),
            "filter_roles": list(roles),
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
        agent_scope: str = "default",
        roles: tuple[str, ...] = (),
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
            "agent_scope": str(agent_scope or "default").strip().lower() or "default",
            "roles": [str(item).strip().lower() for item in roles if str(item).strip()],
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
                "agent_scope": payload["agent_scope"],
                "roles": payload["roles"],
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
        agent_scope: str,
        roles: tuple[str, ...],
    ) -> None:
        if channel == "email":
            from cadiax.interfaces.email import EmailInterfaceService

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
            from cadiax.interfaces.whatsapp import WhatsAppInterfaceService

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
                    "agent_scope": agent_scope,
                    "roles": list(roles),
                    "metadata": metadata,
                },
            )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_delivery_context(metadata: dict[str, Any] | None) -> tuple[dict[str, Any], str, tuple[str, ...]]:
    payload = dict(metadata or {})
    interaction = get_current_interaction_context()
    agent_scope = str(
        payload.get("agent_scope")
        or interaction.get("agent_scope")
        or "default"
    ).strip().lower() or "default"
    raw_roles = payload.get("roles")
    if isinstance(raw_roles, str):
        roles = tuple(item for item in [raw_roles.strip().lower()] if item)
    elif isinstance(raw_roles, (list, tuple, set)):
        roles = tuple(
            item_text
            for item_text in (str(item).strip().lower() for item in raw_roles)
            if item_text
        )
    else:
        roles = tuple(
            item_text
            for item_text in (
                str(item).strip().lower()
                for item in interaction.get("roles", ())
            )
            if item_text
        )
    payload["agent_scope"] = agent_scope
    payload["roles"] = list(roles)
    return payload, agent_scope, roles
