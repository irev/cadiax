"""Runtime helpers for the optional monitoring dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from otonomassist.core import agent_context


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_ROOT = PROJECT_ROOT / "monitoring-dashboard"
DEFAULT_DASHBOARD_PORT = 8795
DEFAULT_DASHBOARD_HOST = "127.0.0.1"
DEFAULT_ADMIN_API_URL = "http://127.0.0.1:8787"


@dataclass(slots=True)
class DashboardCommandResult:
    """Result metadata from one dashboard subprocess command."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def load_dashboard_state() -> dict[str, Any]:
    """Load dashboard runtime state from durable storage."""
    default_state = {
        "enabled": False,
        "host": DEFAULT_DASHBOARD_HOST,
        "port": DEFAULT_DASHBOARD_PORT,
        "admin_api_url": DEFAULT_ADMIN_API_URL,
        "last_action": "",
        "updated_at": "",
    }
    state_file = _dashboard_state_file()
    if not state_file.exists():
        return default_state
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default_state
    state = {**default_state, **payload}
    state["enabled"] = bool(state.get("enabled"))
    state["host"] = str(state.get("host") or DEFAULT_DASHBOARD_HOST)
    state["port"] = int(state.get("port", DEFAULT_DASHBOARD_PORT) or DEFAULT_DASHBOARD_PORT)
    state["admin_api_url"] = str(state.get("admin_api_url") or DEFAULT_ADMIN_API_URL)
    return state


def save_dashboard_state(state: dict[str, Any]) -> dict[str, Any]:
    """Persist dashboard runtime state to durable storage."""
    agent_context.ensure_agent_storage()
    state_file = _dashboard_state_file()
    normalized = {
        "enabled": bool(state.get("enabled")),
        "host": str(state.get("host") or DEFAULT_DASHBOARD_HOST),
        "port": int(state.get("port", DEFAULT_DASHBOARD_PORT) or DEFAULT_DASHBOARD_PORT),
        "admin_api_url": str(state.get("admin_api_url") or DEFAULT_ADMIN_API_URL),
        "last_action": str(state.get("last_action") or ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    state_file.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def get_dashboard_status() -> dict[str, Any]:
    """Return one machine-readable dashboard status snapshot."""
    state = load_dashboard_state()
    client_dist = DASHBOARD_ROOT / "dist" / "client" / "index.html"
    server_dist = DASHBOARD_ROOT / "dist" / "server" / "server.js"
    package_json = DASHBOARD_ROOT / "package.json"
    return {
        **state,
        "dashboard_root": str(DASHBOARD_ROOT),
        "state_file": str(_dashboard_state_file()),
        "package_json_exists": package_json.exists(),
        "dependencies_installed": (DASHBOARD_ROOT / "node_modules").exists(),
        "build_ready": client_dist.exists() and server_dist.exists(),
        "client_build_file": str(client_dist),
        "server_build_file": str(server_dist),
        "access_mode": "public" if state["host"] == "0.0.0.0" else "local",
    }


def render_dashboard_status() -> str:
    """Render dashboard status as text for operators."""
    status = get_dashboard_status()
    lines = [
        "Monitoring Dashboard",
        "",
        f"- enabled: {'yes' if status['enabled'] else 'no'}",
        f"- access_mode: {status['access_mode']}",
        f"- host: {status['host']}",
        f"- port: {status['port']}",
        f"- admin_api_url: {status['admin_api_url']}",
        f"- package_json_exists: {'yes' if status['package_json_exists'] else 'no'}",
        f"- dependencies_installed: {'yes' if status['dependencies_installed'] else 'no'}",
        f"- build_ready: {'yes' if status['build_ready'] else 'no'}",
        f"- dashboard_root: {status['dashboard_root']}",
        f"- last_action: {status['last_action'] or '-'}",
    ]
    return "\n".join(lines)


def enable_dashboard(
    *,
    host: str = DEFAULT_DASHBOARD_HOST,
    port: int = DEFAULT_DASHBOARD_PORT,
    admin_api_url: str = DEFAULT_ADMIN_API_URL,
    install: bool = True,
    build: bool = True,
) -> dict[str, Any]:
    """Enable dashboard state and optionally install/build the dashboard app."""
    state = save_dashboard_state(
        {
            "enabled": True,
            "host": host,
            "port": port,
            "admin_api_url": admin_api_url,
            "last_action": "enabled",
        }
    )
    actions: list[str] = []
    if install:
        install_dashboard_dependencies()
        actions.append("npm_install")
    if build:
        build_dashboard()
        actions.append("npm_build")
    status = get_dashboard_status()
    status["actions"] = actions
    return status


def disable_dashboard() -> dict[str, Any]:
    """Disable dashboard runtime without deleting installed assets."""
    state = load_dashboard_state()
    state["enabled"] = False
    state["last_action"] = "disabled"
    save_dashboard_state(state)
    return get_dashboard_status()


def install_dashboard_dependencies() -> DashboardCommandResult:
    """Install npm dependencies for the dashboard app."""
    return _run_dashboard_command(["npm", "install"])


def build_dashboard() -> DashboardCommandResult:
    """Build dashboard client and server assets."""
    return _run_dashboard_command(["npm", "run", "build"])


def run_dashboard_service(
    *,
    host: str | None = None,
    port: int | None = None,
    admin_api_url: str | None = None,
    install_if_missing: bool = False,
    build_if_needed: bool = True,
) -> None:
    """Run the dashboard server as a foreground process."""
    status = get_dashboard_status()
    if not status["enabled"]:
        raise RuntimeError("Dashboard disabled. Run `otonomassist dashboard enable` first.")
    if install_if_missing and not status["dependencies_installed"]:
        install_dashboard_dependencies()
        status = get_dashboard_status()
    if build_if_needed and not status["build_ready"]:
        build_dashboard()
        status = get_dashboard_status()

    env = os.environ.copy()
    env["OTONOMASSIST_DASHBOARD_HOST"] = str(host or status["host"])
    env["OTONOMASSIST_DASHBOARD_PORT"] = str(int(port or status["port"]))
    env["OTONOMASSIST_DASHBOARD_ADMIN_API_URL"] = str(admin_api_url or status["admin_api_url"])
    admin_token = os.getenv("OTONOMASSIST_ADMIN_TOKEN", "").strip()
    if admin_token:
        env["OTONOMASSIST_DASHBOARD_ADMIN_TOKEN"] = admin_token
    subprocess.run(
        ["npm", "run", "serve"],
        cwd=DASHBOARD_ROOT,
        check=True,
        env=env,
    )


def _run_dashboard_command(command: list[str]) -> DashboardCommandResult:
    """Run one dashboard subprocess command in the dashboard root."""
    completed = subprocess.run(
        command,
        cwd=DASHBOARD_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return DashboardCommandResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _dashboard_state_file() -> Path:
    return agent_context.DATA_DIR / "dashboard_state.json"
