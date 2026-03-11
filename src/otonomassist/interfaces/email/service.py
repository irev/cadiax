"""Email interface service built on top of conversation and notification boundaries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import otonomassist.core.agent_context as agent_context
from otonomassist.core.event_bus import publish_event
from otonomassist.services.interactions.conversation_service import ConversationService
from otonomassist.services.interactions.models import InteractionRequest
from otonomassist.services.interactions.notification_dispatcher import NotificationDispatcher


class EmailInterfaceService:
    """Normalize inbound and outbound email channel activity."""

    def __init__(
        self,
        conversation_service: ConversationService | None = None,
        dispatcher: NotificationDispatcher | None = None,
    ) -> None:
        self.conversation_service = conversation_service
        self.dispatcher = dispatcher or NotificationDispatcher()

    def receive(
        self,
        *,
        from_address: str,
        subject: str,
        body: str,
        to_address: str = "",
        email_id: str = "",
        thread_id: str = "",
        trace_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Accept one inbound email and route it into the conversation runtime."""
        if self.conversation_service is None:
            raise ValueError("conversation_service is required for inbound email handling")

        payload_metadata = dict(metadata or {})
        payload_metadata.update(
            {
                "email_subject": subject.strip(),
                "email_from": from_address.strip(),
                "email_to": to_address.strip(),
                "email_id": email_id.strip(),
                "thread_id": thread_id.strip(),
            }
        )
        request = InteractionRequest(
            message=body.strip(),
            source="email",
            user_id=from_address.strip(),
            session_id=thread_id.strip() or email_id.strip() or from_address.strip(),
            identity_id=str(payload_metadata.get("identity_id") or "").strip() or None,
            roles=("email",),
            trace_id=trace_id.strip() or None,
            metadata=payload_metadata,
        )
        response = self.conversation_service.handle(request)
        entry = self._append_message(
            {
                "direction": "inbound",
                "from_address": from_address.strip(),
                "to_address": to_address.strip(),
                "subject": subject.strip(),
                "body": body.strip(),
                "email_id": email_id.strip(),
                "thread_id": thread_id.strip() or str(response.metadata.get("canonical_session_id") or ""),
                "trace_id": response.trace_id or "",
                "identity_id": response.identity_id or "",
                "status": response.status,
                "metadata": payload_metadata,
            }
        )
        publish_event(
            "email.inbound",
            event_type="email_received",
            trace_id=response.trace_id or "",
            source="email",
            data={
                "email_message_id": entry["id"],
                "from_address": entry["from_address"],
                "to_address": entry["to_address"],
                "subject": entry["subject"],
                "identity_id": entry["identity_id"],
                "thread_id": entry["thread_id"],
            },
        )
        return {
            "email": entry,
            "interaction": response.to_dict(),
        }

    def send(
        self,
        *,
        to_address: str,
        subject: str,
        body: str,
        from_address: str = "",
        trace_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dispatch one outbound email-shaped notification."""
        payload_metadata = dict(metadata or {})
        if from_address.strip():
            payload_metadata.setdefault("from_address", from_address.strip())
        payload_metadata.setdefault("interface", "email")
        notification = self.dispatcher.dispatch(
            channel="email",
            title=subject.strip() or "Notification",
            message=body.strip(),
            trace_id=trace_id.strip(),
            target=to_address.strip(),
            metadata=payload_metadata,
        )
        entry = self._append_message(
            {
                "direction": "outbound",
                "from_address": from_address.strip(),
                "to_address": to_address.strip(),
                "subject": subject.strip(),
                "body": body.strip(),
                "email_id": "",
                "thread_id": "",
                "trace_id": notification["trace_id"],
                "identity_id": "",
                "status": "queued",
                "notification_id": notification["id"],
                "metadata": payload_metadata,
            }
        )
        publish_event(
            "email.outbound",
            event_type="email_dispatched",
            trace_id=notification["trace_id"],
            source="email",
            data={
                "email_message_id": entry["id"],
                "notification_id": notification["id"],
                "to_address": entry["to_address"],
                "subject": entry["subject"],
            },
        )
        return entry

    def get_snapshot(self) -> dict[str, Any]:
        """Return machine-readable email interface diagnostics."""
        state = agent_context.load_email_message_state()
        messages = state.get("messages", [])
        inbound = [item for item in messages if item.get("direction") == "inbound"]
        outbound = [item for item in messages if item.get("direction") == "outbound"]
        latest = messages[-1] if messages else {}
        return {
            "message_count": len(messages),
            "inbound_count": len(inbound),
            "outbound_count": len(outbound),
            "latest_message": latest,
        }

    def _append_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = agent_context.load_email_message_state()
        messages = state.setdefault("messages", [])
        entry = {
            "id": len(messages) + 1,
            "created_at": _utc_now_iso(),
            **payload,
        }
        messages.append(entry)
        state["updated_at"] = entry["created_at"]
        agent_context.save_email_message_state(state)
        return entry


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
