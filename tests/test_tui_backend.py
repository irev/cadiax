from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

import cadiax.core.agent_context as agent_context
import cadiax.core.setup_wizard as setup_wizard
from cadiax.cli import main
from cadiax.platform.dashboard_runtime import load_dashboard_state
from cadiax.tui.app import (
    build_agents_view,
    build_bootstrap_view,
    CadiaxTuiApp,
    build_channels_view,
    build_doctor_view,
    build_events_view,
    build_external_view,
    build_heartbeat_view,
    build_history_view,
    build_home_view,
    build_jobs_view,
    build_metrics_view,
    build_notify_view,
    build_paths_view,
    build_privacy_view,
    build_proactive_view,
    build_skills_view,
    build_startup_view,
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
        "privacy_controls": {
            "quiet_hours": {"enabled": True, "start": "21:30", "end": "06:30"},
            "quiet_hours_active": False,
            "consent_required_for_proactive": True,
            "proactive_assistance_enabled": True,
            "memory_retention_days": 365,
            "scope_count": 1,
            "memory_entry_count": 3,
            "memory_summary_count": 1,
            "notification_count": 2,
            "email_count": 1,
            "whatsapp_count": 2,
            "identity_count": 1,
            "session_count": 1,
            "filter_agent_scope": "",
            "filter_roles": [],
            "retention_candidates": {"memory_entries": 1, "notifications": 0},
            "scoped_controls": {
                "finance-agent": {
                    "proactive_assistance_enabled": False,
                    "consent_required_for_proactive": True,
                    "allowed_roles": ["finance"],
                }
            },
        },
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
        "startup": {
            "session_mode": "main",
            "agent_scope": "default",
            "scope_declared": True,
            "request_roles": [],
            "documents": [
                {"name": "agents", "availability": "available", "path": "C:/Users/test/Cadiax/workspace/AGENTS.md"}
            ],
            "daily_notes": "Latest note",
            "curated_memory": "Remember this",
        },
        "bootstrap": {
            "bundled_template_dir": "C:/Users/test/AppData/Local/Cadiax/app/bootstrap_assets/foundation/official",
            "template_count": 13,
            "active_runtime_template_count": 6,
            "workspace_seeded_count": 6,
            "workspace_seeded_files": ["AGENTS.md", "SOUL.md"],
            "manifest_file": "C:/Users/test/AppData/Local/Cadiax/state/bootstrap_manifest.json",
            "manifest": {
                "source": "official-foundation-templates",
                "runtime_docs_only": True,
                "seeded_at": "2026-03-14T00:00:00+00:00",
                "workspace_root": "C:/Users/test/Cadiax/workspace",
                "written": ["AGENTS.md", "SOUL.md"],
                "existing": ["USER.md"],
            },
        },
        "external_assets": {
            "asset_count": 3,
            "event_count": 2,
            "incompatible_count": 0,
            "unapproved_count": 1,
            "undeclared_capability_count": 0,
            "blocked_capability_count": 1,
            "isolated_skill_count": 1,
            "approval_by_state": {"approved": 1, "rejected": 1, "pending": 1},
            "approval_event_count": 2,
            "latest_approval_event": {
                "asset_name": "finance-pack",
                "state": "approved",
                "actor": "ops",
                "timestamp": "2026-03-14T00:00:00+00:00",
            },
            "trust_policy": "explicit-approval",
            "allowed_capabilities": ["python", "http"],
            "layout": {
                "skills_dir": "C:/Users/test/Cadiax/workspace/skills-external",
                "tools_dir": "C:/Users/test/Cadiax/workspace/tools-external",
                "packages_dir": "C:/Users/test/Cadiax/workspace/packages-external",
            },
        },
        "agent_scopes": {
            "scope_count": 2,
            "document_path": "C:/Users/test/Cadiax/workspace/AGENTS.md",
            "scopes": [
                {"scope": "default", "description": "Runtime utama", "allowed_roles": []},
                {"scope": "finance-agent", "description": "Analisis keuangan", "allowed_roles": ["finance"]},
            ],
        },
        "notifications": {
            "notification_count": 2,
            "total_notification_count": 3,
            "delivery_batch_count": 1,
            "filter_agent_scope": "",
            "filter_roles": [],
            "by_channel": {"email": 1, "internal": 1},
            "by_scope": {"default": 1, "finance-agent": 1},
            "latest_notification": {
                "channel": "email",
                "title": "Build Alert",
                "target": "ops@example.com",
                "status": "queued",
                "agent_scope": "finance-agent",
            },
        },
        "issues": ["missing api key"],
        "email": {
            "message_count": 1,
            "inbound_count": 0,
            "outbound_count": 1,
            "latest_message": {
                "to_address": "ops@example.com",
                "direction": "outbound",
                "status": "queued",
                "agent_scope": "finance-agent",
            },
            "by_scope": {"finance-agent": 1},
        },
        "whatsapp": {
            "message_count": 2,
            "inbound_count": 1,
            "outbound_count": 1,
            "latest_message": {
                "phone_number": "+628123456789",
                "display_name": "Budi",
                "direction": "inbound",
                "status": "ok",
                "agent_scope": "default",
            },
            "by_scope": {"default": 2},
        },
        "personality": {
            "preference_profile": {"preferred_channels": ["telegram", "email"]},
            "heartbeat_guide_preview": "Pulse menjaga konteks operasi.",
            "heartbeat": {
                "last_mode": "steady",
                "last_summary": "Runtime idle; heartbeat menjaga konteks dan kesiapan.",
                "last_pulse_at": "2026-03-14T00:00:00+00:00",
                "last_trigger": "scheduler",
                "last_trace_id": "hb-1",
                "proactive_insight_count": 2,
            },
            "proactive_insight_count": 2,
            "proactive_insights_generated": 3,
            "proactive_insights": [
                {
                    "confidence": "high",
                    "agent_scope": "finance-agent",
                    "summary": "Review outstanding notification backlog.",
                }
            ],
        },
        "skills_audit": {
            "skills_dir": "C:/Users/test/Cadiax/workspace/skills",
            "category_count": 2,
            "skill_count": 3,
            "categories": {
                "analysis": [
                    {
                        "name": "observe",
                        "risk_level": "low",
                        "idempotency": "idempotent",
                        "timeout_behavior": "fail",
                        "retry_policy": "none",
                        "requires": ["python"],
                        "side_effects": [],
                    }
                ],
                "ops": [
                    {
                        "name": "notify",
                        "risk_level": "medium",
                        "idempotency": "best-effort",
                        "timeout_behavior": "fail",
                        "retry_policy": "retry-once",
                        "requires": ["http"],
                        "side_effects": ["network"],
                    }
                ],
            },
        },
    }

    assert "preferred_channels: telegram, email" in build_channels_view(payload)
    assert "ctrl+e" in build_channels_view(payload)
    assert "global_setup     : none" in build_channels_view(payload)
    assert "latest_direction : outbound" in build_channels_view(payload)
    assert "email:finance-agent -> 1" in build_channels_view(payload)
    assert "command_on_path" in build_paths_view(payload)
    assert "missing api key" in build_doctor_view(payload)
    assert "quiet_hours_enabled" in build_privacy_view(payload)
    assert "finance-agent" in build_privacy_view(payload)
    assert "last_mode" in build_heartbeat_view(payload)
    assert "Pulse menjaga konteks operasi." in build_heartbeat_view(payload)
    assert "insights_generated" in build_proactive_view(payload)
    assert "Review outstanding notification backlog." in build_proactive_view(payload)
    assert "path_mode" in build_home_view(payload)
    assert "workspace_seeded_count" in build_bootstrap_view(payload)
    assert "seed active runtime docs" in build_bootstrap_view(payload)
    assert "seed full template set" in build_bootstrap_view(payload)
    assert "force overwrite active runtime docs" in build_bootstrap_view(payload)
    assert "trust_policy" in build_external_view(payload)
    assert "finance-pack" in build_external_view(payload)
    assert "scope_count" in build_agents_view(payload)
    assert "finance-agent" in build_agents_view(payload)
    assert "category_count" in build_skills_view(payload)
    assert "notify [risk=medium" in build_skills_view(payload)
    assert "delivery_batch_count" in build_notify_view(payload)
    assert "Build Alert" in build_notify_view(payload)
    assert "telegram_in_main_service" in build_services_view(payload, selected_target="conversation-api")
    assert "show_command            : cadiax service show conversation-api" in build_services_view(
        payload, selected_target="conversation-api"
    )
    assert "last_worker_run_at" in build_worker_view(payload)
    assert "last_heartbeat_mode" in build_scheduler_view(payload)
    assert "session_mode" in build_startup_view(payload)
    assert "AGENTS.md" in build_startup_view(payload)
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
    result = runner.invoke(main, ["tui", "--screen", "skills"])

    assert result.exit_code == 0
    assert called["screen"] == "skills"


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


def test_tui_channel_actions_dispatch_test_email_and_whatsapp(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="channels")
    app.status_data = {
        "email": {
            "latest_message": {"to_address": "ops@example.com"},
        },
        "whatsapp": {
            "latest_message": {"phone_number": "+628123456789", "display_name": "Budi"},
        },
    }
    app.current_screen_name = "channels"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)

    class FakeEmailService:
        def send(self, **kwargs):
            return {"to_address": kwargs["to_address"]}

    class FakeWhatsAppService:
        def send(self, **kwargs):
            return {"phone_number": kwargs["phone_number"]}

    monkeypatch.setattr("cadiax.tui.app.EmailInterfaceService", FakeEmailService)
    monkeypatch.setattr("cadiax.tui.app.WhatsAppInterfaceService", FakeWhatsAppService)

    app.action_send_test_email()
    app.action_send_test_whatsapp()

    assert any("Email test queued to ops@example.com" in item for item in notifications)
    assert any("WhatsApp test queued to +628123456789" in item for item in notifications)


def test_tui_channel_target_override_updates_view_and_dispatch(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="channels")
    app.status_data = {
        "email": {
            "latest_message": {"to_address": "ops@example.com"},
        },
        "whatsapp": {
            "latest_message": {"phone_number": "+628123456789", "display_name": "Budi"},
        },
        "personality": {"preference_profile": {"preferred_channels": ["email", "whatsapp"]}},
    }
    app.current_screen_name = "channels"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_reload", lambda: None)

    rendered: list[str] = []
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: rendered.append(screen_name))

    class FakeEmailService:
        def send(self, **kwargs):
            return {"to_address": kwargs["to_address"]}

    class FakeWhatsAppService:
        def send(self, **kwargs):
            return {"phone_number": kwargs["phone_number"]}

    monkeypatch.setattr("cadiax.tui.app.EmailInterfaceService", FakeEmailService)
    monkeypatch.setattr("cadiax.tui.app.WhatsAppInterfaceService", FakeWhatsAppService)

    app._handle_setup_input(("email_test_target", "custom@example.com"))
    app._handle_setup_input(("whatsapp_test_target", "+620000000000"))

    assert app.channel_draft["email_test_target"] == "custom@example.com"
    assert app.channel_draft["whatsapp_test_target"] == "+620000000000"
    assert "email_target     : custom@example.com" in build_channels_view(app.status_data, draft_targets=app.channel_draft)
    assert "whatsapp_target  : +620000000000" in build_channels_view(app.status_data, draft_targets=app.channel_draft)

    app.action_send_test_email()
    app.action_send_test_whatsapp()

    assert any("Email test queued to custom@example.com" in item for item in notifications)
    assert any("WhatsApp test queued to +620000000000" in item for item in notifications)


def test_tui_service_action_writes_wrappers(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="services")
    app.status_data = {"dashboard": {"enabled": False}, "telegram": {"enabled": False}}
    app.current_screen_name = "services"
    app.current_service_target = "scheduler"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)
    called: dict[str, str] = {}

    def fake_write_service_wrapper_artifacts(target="cadiax"):
        called["target"] = target
        return [Path("cadiax-scheduler.service")]

    monkeypatch.setattr("cadiax.tui.app.write_service_wrapper_artifacts", fake_write_service_wrapper_artifacts)
    monkeypatch.setattr("cadiax.tui.app.get_service_wrapper_output_dir", lambda: Path("C:/Cadiax/state/service-wrappers"))

    app.action_write_service_wrappers()

    assert called["target"] == "scheduler"
    assert any("Service wrappers written: 1 files for scheduler" in item for item in notifications)


def test_tui_service_target_selection_cycles(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="services")
    app.current_screen_name = "services"
    app.current_service_target = "cadiax"
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)

    app.action_next_service_target()
    assert app.current_service_target == "worker"

    app.action_prev_service_target()
    assert app.current_service_target == "cadiax"


def test_tui_worker_and_scheduler_actions_run_one_shot(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="worker")
    app.status_data = {"runtime": {"status": "healthy"}, "scheduler": {"status": "healthy"}}
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)
    monkeypatch.setattr(
        "cadiax.tui.app.run_worker_once_for_tui",
        lambda: {"processed": 1, "status": "active", "trace_id": "work-1"},
    )
    monkeypatch.setattr(
        "cadiax.tui.app.run_scheduler_once_for_tui",
        lambda: {"processed": 1, "status": "idle", "trace_id": "sched-1"},
    )

    app.current_screen_name = "worker"
    app.action_run_worker_once()
    app.current_screen_name = "scheduler"
    app.action_run_scheduler_once()

    assert any("Worker run complete: processed=1 status=active" in item for item in notifications)
    assert any("Scheduler run complete: processed=1 status=idle" in item for item in notifications)


def test_tui_service_probe_actions_report_admin_and_conversation(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="services")
    app.status_data = {"dashboard": {"enabled": False}, "telegram": {"enabled": False}}
    app.current_screen_name = "services"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)
    monkeypatch.setattr(
        "cadiax.tui.app.probe_admin_api_for_tui",
        lambda: {"ok": True, "status_code": 200, "status": "ok"},
    )
    monkeypatch.setattr(
        "cadiax.tui.app.probe_conversation_api_for_tui",
        lambda: {"ok": False, "status_code": 401, "status": "http_error"},
    )

    app.action_probe_admin_api()
    app.action_probe_conversation_api()

    assert any("Admin API probe: 200 ok" in item for item in notifications)
    assert any("Conversation API probe: 401 http_error" in item for item in notifications)


def test_tui_privacy_actions_update_controls(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="privacy")
    app.status_data = {
        "privacy_controls": {
            "quiet_hours": {"enabled": False, "start": "22:00", "end": "07:00"},
            "proactive_assistance_enabled": True,
            "consent_required_for_proactive": True,
            "memory_retention_days": 365,
        }
    }
    app.current_screen_name = "privacy"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)

    calls: list[tuple[str, dict[str, object]]] = []

    class FakePrivacyControlService:
        def set_quiet_hours(self, **kwargs):
            calls.append(("quiet_hours", kwargs))
            return {}

        def set_proactive_controls(self, **kwargs):
            calls.append(("proactive", kwargs))
            return {}

    monkeypatch.setattr("cadiax.tui.app.PrivacyControlService", FakePrivacyControlService)

    app.action_toggle_quiet_hours()
    app.action_cycle_retention_days()
    app.action_toggle_proactive_delivery()
    app.action_toggle_proactive_consent()

    assert ("quiet_hours", {"start": "22:00", "end": "07:00", "enabled": True}) in calls
    assert ("proactive", {"memory_retention_days": 30}) in calls
    assert ("proactive", {"proactive_enabled": False}) in calls
    assert ("proactive", {"consent_required": False}) in calls
    assert any("Quiet hours enabled" in item for item in notifications)
    assert any("Memory retention set to 30 day(s)" in item for item in notifications)
    assert any("Proactive delivery disabled" in item for item in notifications)
    assert any("Proactive consent optional" in item for item in notifications)


def test_tui_bootstrap_action_seeds_runtime_docs(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="bootstrap")
    app.status_data = {"bootstrap": {"workspace_seeded_count": 0}}
    app.current_screen_name = "bootstrap"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)
    monkeypatch.setattr(
        "cadiax.tui.app.ensure_workspace_skeleton",
        lambda **kwargs: {"written_count": 6, "existing_count": 0},
    )

    app.action_run_bootstrap_foundation()

    assert any("Foundation bootstrap written=6 existing=0" in item for item in notifications)


def test_tui_bootstrap_advanced_actions_seed_optional_and_force(monkeypatch) -> None:
    app = CadiaxTuiApp(initial_screen="bootstrap")
    app.status_data = {"bootstrap": {"workspace_seeded_count": 0}}
    app.current_screen_name = "bootstrap"
    notifications: list[str] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append(str(message)))
    monkeypatch.setattr(app, "_render_screen", lambda screen_name: None)
    monkeypatch.setattr(app, "_reload", lambda: None)

    calls: list[dict[str, object]] = []

    def fake_ensure_workspace_skeleton(**kwargs):
        calls.append(kwargs)
        return {"written_count": 13 if not kwargs.get("runtime_docs_only", True) else 6, "existing_count": 0}

    monkeypatch.setattr("cadiax.tui.app.ensure_workspace_skeleton", fake_ensure_workspace_skeleton)

    app.action_run_bootstrap_optional()
    app.action_run_bootstrap_force()

    assert {"force": False, "only_if_workspace_empty": False, "runtime_docs_only": False} in calls
    assert {"force": True, "only_if_workspace_empty": False, "runtime_docs_only": True} in calls
    assert any("Foundation optional bootstrap written=13 existing=0" in item for item in notifications)
    assert any("Foundation force bootstrap written=6 existing=0" in item for item in notifications)


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
