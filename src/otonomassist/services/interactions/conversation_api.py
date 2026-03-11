"""HTTP conversation API separated from the admin API surface."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from otonomassist.core.event_bus import publish_event
from otonomassist.interfaces.email import EmailInterfaceService
from otonomassist.interfaces.whatsapp import WhatsAppInterfaceService
from otonomassist.services.interactions.conversation_service import ConversationService
from otonomassist.services.interactions.notification_dispatcher import NotificationDispatcher
from otonomassist.services.interactions.models import InteractionRequest


def build_conversation_response(
    path: str,
    *,
    service: ConversationService,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Build one JSON response for the conversation API."""
    if not _is_authorized(headers or {}):
        return 401, {"error": "unauthorized"}

    route = urlparse(path).path.rstrip("/") or "/"
    method = method.upper().strip()

    if route == "/health":
        if method != "GET":
            return 405, {"error": "method_not_allowed", "allowed": ["GET"]}
        return 200, {"status": "ok", "service": "conversation-api"}

    if route in {"/messages", "/v1/messages"}:
        if method != "POST":
            return 405, {"error": "method_not_allowed", "allowed": ["POST"]}
        try:
            payload = _load_json_body(body)
            request = InteractionRequest.from_payload(payload)
        except json.JSONDecodeError:
            return 400, {"error": "invalid_json"}
        except ValueError as exc:
            return 400, {"error": "invalid_request", "detail": str(exc)}

        try:
            response = service.handle(request)
        except Exception as exc:
            return 500, {"error": "execution_failed", "detail": str(exc)}
        return 200, response.to_dict()

    if route in {"/webhooks/events", "/v1/webhooks/events"}:
        if method != "POST":
            return 405, {"error": "method_not_allowed", "allowed": ["POST"]}
        try:
            payload = _load_json_body(body)
        except json.JSONDecodeError:
            return 400, {"error": "invalid_json"}
        except ValueError as exc:
            return 400, {"error": "invalid_request", "detail": str(exc)}

        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        event_type = str(payload.get("event_type") or "event.received").strip() or "event.received"
        text = str(payload.get("message") or payload.get("text") or "").strip()
        if text:
            request = InteractionRequest(
                message=text,
                source=str(payload.get("source") or "webhook"),
                user_id=_coerce_optional_text(payload.get("user_id")),
                session_id=_coerce_optional_text(payload.get("session_id")),
                chat_id=_coerce_optional_text(payload.get("chat_id")),
                identity_id=_coerce_optional_text(payload.get("identity_id")),
                roles=tuple(str(item).strip() for item in payload.get("roles", []) if str(item).strip()) if isinstance(payload.get("roles"), list) else (),
                trace_id=_coerce_optional_text(payload.get("trace_id")),
                metadata={"webhook_event_type": event_type, **metadata},
            )
            try:
                response = service.handle(request)
            except Exception as exc:
                return 500, {"error": "execution_failed", "detail": str(exc)}
            return 200, {
                "status": "accepted",
                "webhook_event_type": event_type,
                "interaction": response.to_dict(),
            }

        published = publish_event(
            "webhook.event",
            event_type=event_type,
            trace_id=str(payload.get("trace_id") or ""),
            source=str(payload.get("source") or "webhook"),
            data={
                "user_id": _coerce_optional_text(payload.get("user_id")) or "",
                "session_id": _coerce_optional_text(payload.get("session_id")) or "",
                "chat_id": _coerce_optional_text(payload.get("chat_id")) or "",
                "metadata": metadata,
            },
        )
        return 202, {
            "status": "accepted",
            "webhook_event_type": event_type,
            "event_topic": published["topic"],
            "trace_id": published["trace_id"],
        }

    if route in {"/notifications", "/v1/notifications"}:
        if method != "POST":
            return 405, {"error": "method_not_allowed", "allowed": ["POST"]}
        try:
            payload = _load_json_body(body)
        except json.JSONDecodeError:
            return 400, {"error": "invalid_json"}
        except ValueError as exc:
            return 400, {"error": "invalid_request", "detail": str(exc)}
        message = str(payload.get("message") or "").strip()
        if not message:
            return 400, {"error": "invalid_request", "detail": "field `message` is required"}
        metadata = payload.get("metadata")
        dispatcher = NotificationDispatcher()
        deliveries = payload.get("deliveries")
        if isinstance(deliveries, list) and deliveries:
            dispatched = dispatcher.dispatch_many(
                title=str(payload.get("title") or "Notification"),
                message=message,
                deliveries=[item for item in deliveries if isinstance(item, dict)],
                trace_id=str(payload.get("trace_id") or ""),
                metadata=metadata if isinstance(metadata, dict) else {},
            )
            return 200, {"status": "ok", "batch": dispatched}
        dispatched = dispatcher.dispatch(
            channel=str(payload.get("channel") or "internal"),
            title=str(payload.get("title") or "Notification"),
            message=message,
            trace_id=str(payload.get("trace_id") or ""),
            target=str(payload.get("target") or ""),
            metadata=metadata if isinstance(metadata, dict) else {},
        )
        return 200, {"status": "ok", "notification": dispatched}

    if route in {"/email/inbound", "/v1/email/inbound"}:
        if method != "POST":
            return 405, {"error": "method_not_allowed", "allowed": ["POST"]}
        try:
            payload = _load_json_body(body)
        except json.JSONDecodeError:
            return 400, {"error": "invalid_json"}
        except ValueError as exc:
            return 400, {"error": "invalid_request", "detail": str(exc)}
        from_address = str(payload.get("from_address") or "").strip()
        message = str(payload.get("message") or payload.get("body") or "").strip()
        if not from_address:
            return 400, {"error": "invalid_request", "detail": "field `from_address` is required"}
        if not message:
            return 400, {"error": "invalid_request", "detail": "field `message` is required"}
        metadata = payload.get("metadata")
        email = EmailInterfaceService(conversation_service=service)
        try:
            handled = email.receive(
                from_address=from_address,
                to_address=str(payload.get("to_address") or "").strip(),
                subject=str(payload.get("subject") or "").strip(),
                body=message,
                email_id=str(payload.get("email_id") or "").strip(),
                thread_id=str(payload.get("thread_id") or "").strip(),
                trace_id=str(payload.get("trace_id") or "").strip(),
                metadata=metadata if isinstance(metadata, dict) else {},
            )
        except Exception as exc:
            return 500, {"error": "execution_failed", "detail": str(exc)}
        return 200, {"status": "accepted", **handled}

    if route in {"/email/outbound", "/v1/email/outbound"}:
        if method != "POST":
            return 405, {"error": "method_not_allowed", "allowed": ["POST"]}
        try:
            payload = _load_json_body(body)
        except json.JSONDecodeError:
            return 400, {"error": "invalid_json"}
        except ValueError as exc:
            return 400, {"error": "invalid_request", "detail": str(exc)}
        to_address = str(payload.get("to_address") or "").strip()
        message = str(payload.get("message") or payload.get("body") or "").strip()
        if not to_address:
            return 400, {"error": "invalid_request", "detail": "field `to_address` is required"}
        if not message:
            return 400, {"error": "invalid_request", "detail": "field `message` is required"}
        metadata = payload.get("metadata")
        email = EmailInterfaceService()
        dispatched = email.send(
            to_address=to_address,
            from_address=str(payload.get("from_address") or "").strip(),
            subject=str(payload.get("subject") or "Notification").strip(),
            body=message,
            trace_id=str(payload.get("trace_id") or "").strip(),
            metadata=metadata if isinstance(metadata, dict) else {},
        )
        return 200, {"status": "ok", "email": dispatched}

    if route in {"/whatsapp/inbound", "/v1/whatsapp/inbound"}:
        if method != "POST":
            return 405, {"error": "method_not_allowed", "allowed": ["POST"]}
        try:
            payload = _load_json_body(body)
        except json.JSONDecodeError:
            return 400, {"error": "invalid_json"}
        except ValueError as exc:
            return 400, {"error": "invalid_request", "detail": str(exc)}
        phone_number = str(payload.get("phone_number") or "").strip()
        message = str(payload.get("message") or payload.get("body") or "").strip()
        if not phone_number:
            return 400, {"error": "invalid_request", "detail": "field `phone_number` is required"}
        if not message:
            return 400, {"error": "invalid_request", "detail": "field `message` is required"}
        metadata = payload.get("metadata")
        whatsapp = WhatsAppInterfaceService(conversation_service=service)
        try:
            handled = whatsapp.receive(
                phone_number=phone_number,
                body=message,
                display_name=str(payload.get("display_name") or "").strip(),
                wa_id=str(payload.get("wa_id") or "").strip(),
                thread_id=str(payload.get("thread_id") or "").strip(),
                trace_id=str(payload.get("trace_id") or "").strip(),
                metadata=metadata if isinstance(metadata, dict) else {},
            )
        except Exception as exc:
            return 500, {"error": "execution_failed", "detail": str(exc)}
        return 200, {"status": "accepted", **handled}

    if route in {"/whatsapp/outbound", "/v1/whatsapp/outbound"}:
        if method != "POST":
            return 405, {"error": "method_not_allowed", "allowed": ["POST"]}
        try:
            payload = _load_json_body(body)
        except json.JSONDecodeError:
            return 400, {"error": "invalid_json"}
        except ValueError as exc:
            return 400, {"error": "invalid_request", "detail": str(exc)}
        phone_number = str(payload.get("phone_number") or "").strip()
        message = str(payload.get("message") or payload.get("body") or "").strip()
        if not phone_number:
            return 400, {"error": "invalid_request", "detail": "field `phone_number` is required"}
        if not message:
            return 400, {"error": "invalid_request", "detail": "field `message` is required"}
        metadata = payload.get("metadata")
        whatsapp = WhatsAppInterfaceService()
        dispatched = whatsapp.send(
            phone_number=phone_number,
            body=message,
            display_name=str(payload.get("display_name") or "").strip(),
            trace_id=str(payload.get("trace_id") or "").strip(),
            metadata=metadata if isinstance(metadata, dict) else {},
        )
        return 200, {"status": "ok", "whatsapp": dispatched}

    return 404, {"error": "not_found", "path": route}


def run_conversation_api(
    service: ConversationService,
    host: str = "127.0.0.1",
    port: int = 8788,
) -> None:
    """Run the local conversation API."""
    handler_cls = _build_handler(service)
    server = ThreadingHTTPServer((host, port), handler_cls)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _build_handler(service: ConversationService):
    class ConversationHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            headers = {key: value for key, value in self.headers.items()}
            status, payload = build_conversation_response(
                self.path,
                service=service,
                method="GET",
                headers=headers,
            )
            _write_json_response(self, status, payload)

        def do_POST(self) -> None:  # noqa: N802
            headers = {key: value for key, value in self.headers.items()}
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length > 0 else b""
            status, payload = build_conversation_response(
                self.path,
                service=service,
                method="POST",
                body=body,
                headers=headers,
            )
            _write_json_response(self, status, payload)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return ConversationHandler


def _load_json_body(body: bytes | None) -> dict[str, Any]:
    if not body:
        raise ValueError("request body is required")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    return payload


def _coerce_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _write_json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _is_authorized(headers: dict[str, str]) -> bool:
    expected = os.getenv("OTONOMASSIST_CONVERSATION_TOKEN", "").strip()
    if not expected:
        return True
    supplied = (
        headers.get("X-OtonomAssist-Conversation-Token")
        or headers.get("X-OtonomAssist-Token")
        or headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    return supplied == expected
