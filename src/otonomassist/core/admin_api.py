"""Read-only admin API surface for local operations."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from otonomassist.core.config_doctor import get_config_status_data
from otonomassist.core.event_bus import get_event_bus_snapshot
from otonomassist.core.execution_history import export_execution_events
from otonomassist.core.execution_metrics import get_execution_metrics_snapshot
from otonomassist.core.job_runtime import get_job_queue_summary
from otonomassist.core.workspace_bootstrap import get_workspace_bootstrap_status
from otonomassist.core.agent_context import load_job_queue_state
from otonomassist.core.scheduler_runtime import get_scheduler_summary
from otonomassist.services.personality.startup_document_service import StartupDocumentService


def build_admin_snapshot(path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    """Build a read-only JSON payload for one admin API path."""
    if not _is_authorized(headers or {}):
        return 401, {"error": "unauthorized"}
    parsed = urlparse(path)
    route = parsed.path.rstrip("/") or "/"
    query = parse_qs(parsed.query)
    if route == "/health":
        status = get_config_status_data()
        return 200, {"status": "ok", "overall": status["overall"]["status"]}
    if route == "/status":
        return 200, get_config_status_data()
    if route == "/metrics":
        return 200, get_execution_metrics_snapshot()
    if route == "/jobs":
        return 200, {"summary": get_job_queue_summary(), "queue": load_job_queue_state()}
    if route == "/scheduler":
        return 200, {"scheduler": get_scheduler_summary()}
    if route == "/history":
        limit = _int_query(query, "limit", 20, minimum=1, maximum=200)
        return 200, {"events": export_execution_events(limit=limit)}
    if route == "/events":
        limit = _int_query(query, "limit", 20, minimum=1, maximum=200)
        return 200, get_event_bus_snapshot(limit=limit)
    if route == "/bootstrap":
        return 200, {"bootstrap": get_workspace_bootstrap_status()}
    if route == "/startup":
        session_mode = (query.get("session_mode") or ["main"])[0]
        return 200, {"startup": StartupDocumentService().get_snapshot(session_mode=session_mode)}
    if route == "/privacy":
        from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

        return 200, {"privacy_controls": PrivacyControlService().get_diagnostics()}
    if route == "/proactive":
        from otonomassist.services.personality.proactive_assistance_service import ProactiveAssistanceService

        return 200, {"proactive": ProactiveAssistanceService().load_or_refresh()}
    return 404, {"error": "not_found", "path": route}


def run_admin_api(host: str = "127.0.0.1", port: int = 8787) -> None:
    """Run the local read-only admin API."""
    handler_cls = _build_handler()
    server = ThreadingHTTPServer((host, port), handler_cls)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _build_handler():
    class AdminHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            headers = {key: value for key, value in self.headers.items()}
            status, payload = build_admin_snapshot(self.path, headers=headers)
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return AdminHandler


def _is_authorized(headers: dict[str, str]) -> bool:
    expected = os.getenv("OTONOMASSIST_ADMIN_TOKEN", "").strip()
    if not expected:
        return True
    supplied = (
        headers.get("X-OtonomAssist-Token")
        or headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    return supplied == expected


def _int_query(
    query: dict[str, list[str]],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw = (query.get(name) or [str(default)])[0]
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))
