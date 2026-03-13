from __future__ import annotations

from click.testing import CliRunner

from cadiax.cli import main
from cadiax.tui.app import build_channels_view, build_doctor_view, build_home_view, build_paths_view


def test_tui_view_builders_cover_channels_and_runtime_snapshot() -> None:
    payload = {
        "overall": {"status": "warning"},
        "ai": {"provider": "openai", "status": "warning"},
        "runtime": {"status": "healthy"},
        "telegram": {"enabled": True, "status": "warning", "dm_policy": "pairing", "group_policy": "allowlist"},
        "dashboard": {"enabled": True, "host": "127.0.0.1", "port": 8795, "admin_api_url": "http://127.0.0.1:8787"},
        "storage": {
            "path_mode": "user",
            "env_file": "C:/Users/test/AppData/Roaming/Cadiax/config.env",
            "state_dir": "C:/Users/test/AppData/Local/Cadiax/state",
            "dashboard_root": "C:/Users/test/AppData/Local/Cadiax/app/monitoring-dashboard",
            "command_kind": "application",
            "command_on_path": "C:/Users/test/.cadiax/bin/cadiax.cmd",
            "command_detail": "shim",
        },
        "workspace": {"root": "C:/Users/test/Cadiax/workspace", "status": "healthy"},
        "routing": {
            "builtin_routes_total": 2,
            "direct_skill_routes_total": 3,
            "heuristic_routes_total": 4,
            "ai_routes_total": 1,
        },
        "privacy": {"status": "healthy"},
        "issues": ["missing api key"],
        "email": {"message_count": 1, "latest_message": {"to_address": "ops@example.com"}},
        "whatsapp": {"message_count": 2, "latest_message": {"phone_number": "+628123456789"}},
        "personality": {"preference_profile": {"preferred_channels": ["telegram", "email"]}},
    }

    assert "preferred_channels: telegram, email" in build_channels_view(payload)
    assert "global_setup     : none" in build_channels_view(payload)
    assert "command_on_path" in build_paths_view(payload)
    assert "missing api key" in build_doctor_view(payload)
    assert "path_mode" in build_home_view(payload)


def test_cli_tui_command_dispatches_selected_screen(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_run_tui(*, initial_screen: str = "home") -> None:
        called["screen"] = initial_screen

    monkeypatch.setattr("cadiax.cli.run_tui", fake_run_tui)
    runner = CliRunner()
    result = runner.invoke(main, ["tui", "--screen", "channels"])

    assert result.exit_code == 0
    assert called["screen"] == "channels"
