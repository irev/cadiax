from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

import cadiax.core.agent_context as agent_context
import cadiax.core.setup_wizard as setup_wizard
from cadiax.cli import main
from cadiax.platform.dashboard_runtime import load_dashboard_state
from cadiax.tui.app import (
    CadiaxTuiApp,
    build_channels_view,
    build_doctor_view,
    build_events_view,
    build_history_view,
    build_home_view,
    build_jobs_view,
    build_metrics_view,
    build_paths_view,
    build_scheduler_view,
    build_services_view,
    build_setup_view,
    build_worker_view,
)


def test_tui_view_builders_cover_channels_and_runtime_snapshot() -> None:
    payload = {
        "overall": {"status": "warning"},
        "ai": {"provider": "openai", "status": "warning"},
        "scheduler": {
            "status": "healthy",
            "last_run_at": "2026-03-14T00:00:00+00:00",
            "last_status": "idle",
            "last_cycles": 1,
            "last_processed": 2,
            "last_trace_id": "sched-1",
            "last_heartbeat_mode": "steady",
        },
        "runtime": {
            "status": "healthy",
            "last_worker_run_at": "2026-03-14T00:00:00+00:00",
            "last_worker_status": "idle",
            "last_worker_processed": 2,
            "last_worker_trace_id": "work-1",
        },
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
        "jobs": {
            "total_jobs": 5,
            "queued_jobs": 2,
            "leased_jobs": 1,
            "done_jobs": 1,
            "failed_jobs": 1,
            "requeued_jobs": 0,
            "last_worker_run_at": "2026-03-14T00:00:00+00:00",
            "last_worker_status": "healthy",
            "last_worker_processed": 2,
        },
        "metrics": {
            "summary": {
                "events_total": 12,
                "commands_total": 4,
                "routes_total": 5,
                "heuristic_routes_total": 2,
                "ai_routes_total": 1,
                "errors_total": 0,
                "timeouts_total": 0,
                "ai_requests_total": 3,
                "ai_total_tokens": 1500,
            },
            "queue_depth": {
                "runtime": {"current_depth": 3, "high_watermark": 4, "queued": 2, "leased": 1}
            },
            "provider_latency": {
                "openai:gpt-4.1-mini": {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "avg_ms": 123,
                    "max_ms": 150,
                    "last_ms": 110,
                }
            },
        },
        "history": [
            {"timestamp": "2026-03-14T00:00:00+00:00", "event_type": "command_completed", "trace_id": "abc", "status": "ok"}
        ],
        "events": {
            "total_events": 8,
            "returned_events": 3,
            "automation_event_count": 2,
            "policy_event_count": 1,
            "external_event_count": 0,
            "last_event_topic": "automation.job",
            "topics": {"automation.job": 2, "policy.decision": 1},
            "events": [
                {
                    "timestamp": "2026-03-14T00:00:00+00:00",
                    "topic": "automation.job",
                    "event_type": "job_enqueued",
                    "trace_id": "abc",
                }
            ],
        },
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
    assert "telegram_in_main_service" in build_services_view(payload)
    assert "last_worker_run_at" in build_worker_view(payload)
    assert "last_heartbeat_mode" in build_scheduler_view(payload)
    assert "queued_jobs" in build_jobs_view(payload)
    assert "ai_total_tokens" in build_metrics_view(payload)
    assert "command_completed" in build_history_view(payload)
    assert "automation.job" in build_events_view(payload)
    provider_step = build_setup_view(payload, step_index=0, draft={"provider": "claude"})
    telegram_step = build_setup_view(payload, step_index=2, draft={"telegram_dm_policy": "owner", "telegram_require_mention": "false"})
    dashboard_step = build_setup_view(payload, step_index=3, draft={"dashboard_host": "0.0.0.0", "dashboard_port": 8800})
    interfaces_step = build_setup_view(payload, step_index=4)
    summary_step = build_setup_view(payload, step_index=5)
    assert "[Step] 1/6 - Provider" in provider_step
    assert "provider_draft         : claude" in provider_step
    assert "dm_policy_draft        : owner" in telegram_step
    assert "port_draft             : 8800" in dashboard_step
    assert "Per-Dispatch Interfaces" in interfaces_step
    assert "email                  : no global credential form" in interfaces_step
    assert "Current Boundary" in summary_step


def test_cli_tui_command_dispatches_selected_screen(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_run_tui(*, initial_screen: str = "home") -> None:
        called["screen"] = initial_screen

    monkeypatch.setattr("cadiax.cli.run_tui", fake_run_tui)
    runner = CliRunner()
    result = runner.invoke(main, ["tui", "--screen", "metrics"])

    assert result.exit_code == 0
    assert called["screen"] == "metrics"


def test_cli_setup_command_dispatches_setup_tui(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_run_tui(*, initial_screen: str = "home") -> None:
        called["screen"] = initial_screen

    monkeypatch.setattr("cadiax.cli.run_tui", fake_run_tui)
    runner = CliRunner()
    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 0
    assert called["screen"] == "setup"


def test_tui_toggle_actions_update_dashboard_and_telegram(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "config.env"
    state_dir = tmp_path / ".cadiax"
    monkeypatch.setenv("CADIAX_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("OTONOMASSIST_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("CADIAX_STATE_DIR", str(state_dir))
    monkeypatch.setenv("OTONOMASSIST_STATE_DIR", str(state_dir))
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    monkeypatch.setattr(agent_context, "DATA_DIR", state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    env_file.write_text("TELEGRAM_ENABLED=false\nDASHBOARD_ENABLED=false\n", encoding="utf-8")

    app = CadiaxTuiApp(initial_screen="setup")
    app.status_data = {
        "dashboard": {"enabled": False, "host": "127.0.0.1", "port": 8795, "admin_api_url": "http://127.0.0.1:8787"},
        "telegram": {"enabled": False},
    }
    app.current_screen_name = "setup"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)

    app.action_toggle_telegram()
    app.action_toggle_dashboard()

    env_text = env_file.read_text(encoding="utf-8")
    assert "TELEGRAM_ENABLED=true" in env_text
    assert "DASHBOARD_ENABLED=true" in env_text
    assert load_dashboard_state()["enabled"] is True
    assert any("Telegram enabled" in item for item in notifications)
    assert any("Dashboard enabled" in item for item in notifications)


def test_tui_service_action_writes_wrappers(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="services")
    app.status_data = {"dashboard": {"enabled": False}, "telegram": {"enabled": False}}
    app.current_screen_name = "services"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)
    monkeypatch.setattr("cadiax.tui.app.write_service_wrapper_artifacts", lambda target="cadiax": [Path("cadiax-cadiax.service")])
    monkeypatch.setattr("cadiax.tui.app.get_service_wrapper_output_dir", lambda: Path("C:/Cadiax/state/service-wrappers"))

    app.action_write_service_wrappers()

    assert any("Service wrappers written: 1 files" in item for item in notifications)


def test_tui_setup_actions_edit_and_save_provider_and_workspace(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "config.env"
    state_dir = tmp_path / ".cadiax"
    monkeypatch.setenv("CADIAX_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("OTONOMASSIST_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("CADIAX_STATE_DIR", str(state_dir))
    monkeypatch.setenv("OTONOMASSIST_STATE_DIR", str(state_dir))
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    monkeypatch.setattr(agent_context, "DATA_DIR", state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    env_file.write_text("AI_PROVIDER=openai\nOTONOMASSIST_WORKSPACE_ACCESS=ro\n", encoding="utf-8")

    app = CadiaxTuiApp(initial_screen="setup")
    app.status_data = {
        "ai": {"provider": "openai"},
        "workspace": {"access": "ro"},
        "dashboard": {"host": "127.0.0.1"},
    }
    app._sync_setup_draft()
    app.current_screen_name = "setup"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)
    monkeypatch.setattr("cadiax.tui.app.ensure_workspace_skeleton", lambda **kwargs: {"written_count": 0, "existing_count": 0})

    app.current_setup_step = 0
    app.action_cycle_setup_field()
    app.action_save_setup_step()

    app.current_setup_step = 1
    app._handle_setup_input(("workspace_root", str(tmp_path / "workspace-new")))
    app.action_alternate_setup_field()
    app.action_save_setup_step()

    env_text = env_file.read_text(encoding="utf-8")
    assert "AI_PROVIDER=claude" in env_text
    assert f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path / 'workspace-new'}" in env_text
    assert "OTONOMASSIST_WORKSPACE_ACCESS=rw" in env_text
    assert any("Provider saved" in item for item in notifications)
    assert any("Workspace access saved" in item for item in notifications)


def test_tui_setup_rejects_empty_workspace_root(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "config.env"
    state_dir = tmp_path / ".cadiax"
    monkeypatch.setenv("CADIAX_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("OTONOMASSIST_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("CADIAX_STATE_DIR", str(state_dir))
    monkeypatch.setenv("OTONOMASSIST_STATE_DIR", str(state_dir))
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    monkeypatch.setattr(agent_context, "DATA_DIR", state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    env_file.write_text("", encoding="utf-8")

    app = CadiaxTuiApp(initial_screen="setup")
    app.status_data = {"workspace": {"root": "", "access": "ro"}}
    app._sync_setup_draft()
    app.current_screen_name = "setup"
    app.current_setup_step = 1
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)

    app._handle_setup_input(("workspace_root", "   "))
    app.action_save_setup_step()

    assert env_file.read_text(encoding="utf-8") == ""
    assert any("Workspace root belum diisi" in item for item in notifications)


def test_tui_setup_actions_edit_and_save_telegram_and_dashboard(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "config.env"
    state_dir = tmp_path / ".cadiax"
    monkeypatch.setenv("CADIAX_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("OTONOMASSIST_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("CADIAX_STATE_DIR", str(state_dir))
    monkeypatch.setenv("OTONOMASSIST_STATE_DIR", str(state_dir))
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    monkeypatch.setattr(agent_context, "DATA_DIR", state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    env_file.write_text(
        "\n".join(
            [
                "TELEGRAM_DM_POLICY=pairing",
                "TELEGRAM_REQUIRE_MENTION=true",
                "DASHBOARD_ENABLED=true",
                "DASHBOARD_HOST=127.0.0.1",
                "DASHBOARD_PORT=8795",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    app = CadiaxTuiApp(initial_screen="setup")
    app.status_data = {
        "ai": {"provider": "openai"},
        "workspace": {"access": "ro"},
        "telegram": {"enabled": True, "dm_policy": "pairing", "require_mention": True},
        "dashboard": {"enabled": True, "host": "127.0.0.1", "port": 8795, "admin_api_url": "http://127.0.0.1:8787"},
    }
    app._sync_setup_draft()
    app.current_screen_name = "setup"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)

    app.current_setup_step = 2
    app.action_cycle_setup_field()
    app.action_alternate_setup_field()
    app.action_save_setup_step()

    app.current_setup_step = 3
    app.action_cycle_setup_field()
    app.action_alternate_setup_field()
    app._handle_setup_input(("dashboard_admin_api_url", "http://127.0.0.1:9999"))
    app.action_save_setup_step()

    env_text = env_file.read_text(encoding="utf-8")
    assert "TELEGRAM_DM_POLICY=owner" in env_text
    assert "TELEGRAM_REQUIRE_MENTION=false" in env_text
    assert "DASHBOARD_HOST=0.0.0.0" in env_text
    assert "DASHBOARD_PORT=8796" in env_text
    assert "DASHBOARD_ADMIN_API_URL=http://127.0.0.1:9999" in env_text
    assert any("Telegram settings saved" in item for item in notifications)
    assert any("Dashboard access saved" in item for item in notifications)


def test_tui_setup_rejects_empty_dashboard_admin_api_url(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "config.env"
    state_dir = tmp_path / ".cadiax"
    monkeypatch.setenv("CADIAX_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("OTONOMASSIST_CONFIG_FILE", str(env_file))
    monkeypatch.setenv("CADIAX_STATE_DIR", str(state_dir))
    monkeypatch.setenv("OTONOMASSIST_STATE_DIR", str(state_dir))
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    monkeypatch.setattr(agent_context, "DATA_DIR", state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    env_file.write_text("DASHBOARD_ADMIN_API_URL=http://127.0.0.1:8787\n", encoding="utf-8")

    app = CadiaxTuiApp(initial_screen="setup")
    app.status_data = {
        "dashboard": {"enabled": True, "host": "127.0.0.1", "port": 8795, "admin_api_url": "http://127.0.0.1:8787"}
    }
    app._sync_setup_draft()
    app.current_screen_name = "setup"
    app.current_setup_step = 3
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)

    app._handle_setup_input(("dashboard_admin_api_url", "   "))

    assert "DASHBOARD_ADMIN_API_URL=http://127.0.0.1:8787" in env_file.read_text(encoding="utf-8")
    assert any("Dashboard admin API URL tidak boleh kosong" in item for item in notifications)
