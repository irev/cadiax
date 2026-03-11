"""HTTP conversation API separated from the admin API surface."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from otonomassist.services.interactions.conversation_service import ConversationService
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
