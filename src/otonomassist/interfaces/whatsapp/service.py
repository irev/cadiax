"""WhatsApp interface service built on top of conversation and notification boundaries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import otonomassist.core.agent_context as agent_context
from otonomassist.core.event_bus import publish_event
from otonomassist.services.interactions.conversation_service import ConversationService
from otonomassist.services.interactions.models import InteractionRequest
from otonomassist.services.interactions.notification_dispatcher import NotificationDispatcher


class WhatsAppInterfaceService:
    """Normalize inbound and outbound WhatsApp channel activity."""

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
        phone_number: str,
        body: str,
        display_name: str = "",
        wa_id: str = "",
        thread_id: str = "",
        trace_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Accept one inbound WhatsApp message and route it into the conversation runtime."""
        if self.conversation_service is None:
            raise ValueError("conversation_service is required for inbound whatsapp handling")

        payload_metadata = dict(metadata or {})
        payload_metadata.update(
            {
                "phone_number": phone_number.strip(),
                "display_name": display_name.strip(),
                "wa_id": wa_id.strip(),
                "thread_id": thread_id.strip(),
            }
        )
        request = InteractionRequest(
            message=body.strip(),
            source="whatsapp",
            user_id=phone_number.strip(),
            session_id=thread_id.strip() or wa_id.strip() or phone_number.strip(),
            identity_id=str(payload_metadata.get("identity_id") or "").strip() or None,
            roles=("whatsapp",),
            trace_id=trace_id.strip() or None,
            metadata=payload_metadata,
        )
        response = self.conversation_service.handle(request)
        entry = self._append_message(
            {
                "direction": "inbound",
                "phone_number": phone_number.strip(),
                "display_name": display_name.strip(),
                "body": body.strip(),
                "wa_id": wa_id.strip(),
                "thread_id": thread_id.strip() or str(response.metadata.get("canonical_session_id") or ""),
                "trace_id": response.trace_id or "",
                "identity_id": response.identity_id or "",
                "status": response.status,
                "metadata": payload_metadata,
            }
        )
        publish_event(
            "whatsapp.inbound",
            event_type="whatsapp_received",
            trace_id=response.trace_id or "",
            source="whatsapp",
            data={
                "whatsapp_message_id": entry["id"],
                "phone_number": entry["phone_number"],
                "display_name": entry["display_name"],
                "identity_id": entry["identity_id"],
                "thread_id": entry["thread_id"],
            },
        )
        return {
            "whatsapp": entry,
            "interaction": response.to_dict(),
        }

    def send(
        self,
        *,
        phone_number: str,
        body: str,
        display_name: str = "",
        trace_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dispatch one outbound WhatsApp-shaped notification."""
        payload_metadata = dict(metadata or {})
        if display_name.strip():
            payload_metadata.setdefault("display_name", display_name.strip())
        payload_metadata.setdefault("interface", "whatsapp")
        notification = self.dispatcher.dispatch(
            channel="whatsapp",
            title=display_name.strip() or "WhatsApp",
            message=body.strip(),
            trace_id=trace_id.strip(),
            target=phone_number.strip(),
            metadata=payload_metadata,
        )
        entry = self._append_message(
            {
                "direction": "outbound",
                "phone_number": phone_number.strip(),
                "display_name": display_name.strip(),
                "body": body.strip(),
                "wa_id": "",
                "thread_id": "",
                "trace_id": notification["trace_id"],
                "identity_id": "",
                "status": "queued",
                "notification_id": notification["id"],
                "metadata": payload_metadata,
            }
        )
        publish_event(
            "whatsapp.outbound",
            event_type="whatsapp_dispatched",
            trace_id=notification["trace_id"],
            source="whatsapp",
            data={
                "whatsapp_message_id": entry["id"],
                "notification_id": notification["id"],
                "phone_number": entry["phone_number"],
            },
        )
        return entry

    def get_snapshot(self) -> dict[str, Any]:
        """Return machine-readable WhatsApp interface diagnostics."""
        state = agent_context.load_whatsapp_message_state()
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
        state = agent_context.load_whatsapp_message_state()
        messages = state.setdefault("messages", [])
        entry = {
            "id": len(messages) + 1,
            "created_at": _utc_now_iso(),
            **payload,
        }
        messages.append(entry)
        state["updated_at"] = entry["created_at"]
        agent_context.save_whatsapp_message_state(state)
        return entry


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
