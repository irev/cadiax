from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner
import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from otonomassist.cli import main  # noqa: E402
import otonomassist.cli as cli_module  # noqa: E402
from otonomassist.core import agent_context, workspace_guard  # noqa: E402
from otonomassist.core.assistant import Assistant  # noqa: E402
from otonomassist.core.skill_loader import SkillLoader  # noqa: E402
from otonomassist.core.skill_registry import SkillRegistry  # noqa: E402
import otonomassist.core.secure_storage as secure_storage  # noqa: E402
import otonomassist.core.setup_wizard as setup_wizard  # noqa: E402
import otonomassist.core.external_assets as external_assets  # noqa: E402
import otonomassist.core.external_installer as external_installer  # noqa: E402
from otonomassist.platform import run_process  # noqa: E402


def _configure_temp_agent_state(tmp_path, monkeypatch):
    data_dir = tmp_path / ".otonomassist"
    for name in (
        "TELEGRAM_OWNER_IDS",
        "TELEGRAM_ALLOW_FROM",
        "TELEGRAM_GROUPS",
        "TELEGRAM_GROUP_ALLOW_FROM",
        "TELEGRAM_DM_POLICY",
        "TELEGRAM_GROUP_POLICY",
        "TELEGRAM_REQUIRE_MENTION",
        "AI_PROVIDER",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(agent_context, "DATA_DIR", data_dir)
    monkeypatch.setattr(agent_context, "MEMORY_FILE", data_dir / "memory.jsonl")
    monkeypatch.setattr(agent_context, "PLANNER_FILE", data_dir / "planner.json")
    monkeypatch.setattr(agent_context, "LESSONS_FILE", data_dir / "lessons.md")
    monkeypatch.setattr(agent_context, "PROFILE_FILE", data_dir / "profile.md")
    monkeypatch.setattr(agent_context, "PREFERENCES_FILE", data_dir / "preferences.json")
    monkeypatch.setattr(agent_context, "SECRETS_FILE", data_dir / "secrets.json")
    monkeypatch.setattr(agent_context, "EXECUTION_HISTORY_FILE", data_dir / "execution_history.jsonl")
    monkeypatch.setattr(agent_context, "METRICS_FILE", data_dir / "execution_metrics.json")
    monkeypatch.setattr(agent_context, "JOB_QUEUE_FILE", data_dir / "job_queue.json")
    monkeypatch.setattr(agent_context, "SCHEDULER_STATE_FILE", data_dir / "scheduler_state.json")
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ACCESS", "rw")
    agent_context.ensure_agent_storage()


def test_cli_setup_wizard_persists_env_and_encrypted_secrets(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    monkeypatch.setattr(setup_wizard, "encrypt_secret", lambda value: f"enc:{value}")

    prompt_answers = iter(
        [
            "openai",
            str(tmp_path),
            "rw",
            "https://api.openai.com/v1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4.1",
            "sk-test-openai",
            "tg-test-token",
            "111,222",
            "pairing",
            "",
            "allowlist",
            "-100123",
            "",
        ]
    )
    confirm_answers = iter(
        [
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
        ]
    )

    monkeypatch.setattr(
        setup_wizard.click,
        "prompt",
        lambda *args, **kwargs: next(prompt_answers),
    )
    monkeypatch.setattr(
        setup_wizard.click,
        "confirm",
        lambda *args, **kwargs: next(confirm_answers),
    )

    runner = CliRunner()
    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 0
    assert "Setup selesai." in result.output

    env_text = env_file.read_text(encoding="utf-8")
    assert "AI_PROVIDER=openai" in env_text
    assert f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}" in env_text
    assert "OTONOMASSIST_WORKSPACE_ACCESS=rw" in env_text
    assert "OPENAI_MODEL=gpt-4.1-mini" in env_text
    assert "OPENAI_API_KEY=" in env_text
    assert "TELEGRAM_BOT_TOKEN=" in env_text
    assert "TELEGRAM_OWNER_IDS=111,222" in env_text
    assert "TELEGRAM_GROUPS=-100123" in env_text

    secrets_state = json.loads(agent_context.SECRETS_FILE.read_text(encoding="utf-8"))
    assert secrets_state["secrets"]["openai_api_key"]["encrypted_value"] == "enc:sk-test-openai"
    assert secrets_state["secrets"]["telegram_bot_token"]["encrypted_value"] == "enc:tg-test-token"


def test_cli_conversation_api_command_starts_separate_service(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    captured: dict[str, object] = {}

    def fake_run_conversation_api(service, host, port):
        captured["service"] = service
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr(cli_module, "run_conversation_api", fake_run_conversation_api)

    runner = CliRunner()
    result = runner.invoke(main, ["conversation-api", "--host", "0.0.0.0", "--port", "8790"])

    assert result.exit_code == 0
    assert "Conversation API listening on http://0.0.0.0:8790" in result.output
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 8790
    assert captured["service"].__class__.__name__ == "ConversationService"


def test_cli_service_status_reports_wrapper_targets(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    runner = CliRunner()
    result = runner.invoke(main, ["service", "status"])

    assert result.exit_code == 0
    assert "Service Runtime" in result.output
    assert "wrapper_output_dir:" in result.output
    assert "worker:" in result.output
    assert "conversation-api:" in result.output


def test_cli_service_show_renders_posix_worker_artifacts(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    runner = CliRunner()
    result = runner.invoke(main, ["service", "show", "worker", "--runtime", "posix"])

    assert result.exit_code == 0
    assert "Service Wrapper Artifacts: worker" in result.output
    assert "[otonomassist-worker.service]" in result.output
    assert "service run worker" in result.output


def test_cli_service_write_generates_wrapper_files(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    output_dir = tmp_path / "wrappers"

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["service", "write", "worker", "--runtime", "posix", "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 0
    assert (output_dir / "otonomassist-worker.service").exists()
    assert (output_dir / "otonomassist-worker.sh").exists()


def test_cli_service_run_uses_named_service_target(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    captured: dict[str, object] = {}

    def fake_run_named_service_target(
        target,
        *,
        skills_dir,
        host,
        port,
        interval_seconds,
        steps,
        enqueue_first,
        until_idle,
        max_loops,
    ):
        captured.update(
            {
                "target": target,
                "skills_dir": skills_dir,
                "host": host,
                "port": port,
                "interval_seconds": interval_seconds,
                "steps": steps,
                "enqueue_first": enqueue_first,
                "until_idle": until_idle,
                "max_loops": max_loops,
            }
        )
        return {"output": "service-run-ok"}

    monkeypatch.setattr(cli_module, "run_named_service_target", fake_run_named_service_target)

    runner = CliRunner()
    result = runner.invoke(main, ["service", "run", "worker", "--max-loops", "1"])

    assert result.exit_code == 0
    assert "service-run-ok" in result.output
    assert captured["target"] == "worker"
    assert captured["max_loops"] == 1


def test_should_recommend_setup_requires_provider_credential_for_remote_provider(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=openai",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)

    assert setup_wizard.should_recommend_setup() is True

    secrets_state = {"secrets": {"openai_api_key": {"encrypted_value": "enc:sk-live", "fingerprint": "********live"}}}
    agent_context.SECRETS_FILE.write_text(json.dumps(secrets_state, indent=2), encoding="utf-8")
    monkeypatch.setattr(agent_context, "get_secret_value", lambda name: "sk-live" if name == "openai_api_key" else None)

    assert setup_wizard.should_recommend_setup() is False


def test_cli_doctor_reports_missing_remote_provider_credential(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=openai",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)
    monkeypatch.setattr(agent_context, "get_secret_value", lambda name: None)

    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])

    assert result.exit_code == 0
    assert "OtonomAssist Config Status" in result.output
    assert "[Overall]" in result.output
    assert "- status: critical" in result.output
    assert "[AI]" in result.output
    assert "- provider: openai" in result.output
    assert "Credential untuk provider 'openai' belum dikonfigurasi." in result.output
    assert "Jalankan `otonomassist setup`" in result.output


def test_assistant_supports_doctor_and_config_status_commands(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
                "OTONOMASSIST_CONTEXT_BUDGET_CHARS=4321",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    doctor_result = assistant.execute("doctor")
    alias_result = assistant.execute("config status")

    assert "OtonomAssist Config Status" in doctor_result
    assert "[Overall]" in doctor_result
    assert "- status: healthy" in doctor_result
    assert "[Workspace]" in doctor_result
    assert "OtonomAssist Config Status" in alias_result
    assert "[Overall]" in alias_result
    assert "- status: healthy" in alias_result
    assert "[Workspace]" in alias_result


def test_cli_doctor_marks_warning_for_rw_workspace_and_pending_telegram(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=rw",
                "TELEGRAM_OWNER_IDS=111",
                "TELEGRAM_BOT_TOKEN=dummy-token",
                "TELEGRAM_DM_POLICY=pairing",
                "TELEGRAM_GROUP_POLICY=allowlist",
                "TELEGRAM_OWNER_ONLY_PREFIXES=workspace,external",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (agent_context.DATA_DIR / "telegram_auth.json").write_text(
        json.dumps(
            {
                "approved_users": [],
                "approved_groups": [],
                "pending_requests": [{"request_id": "req-1", "user_id": "900"}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)
    monkeypatch.setattr(agent_context, "get_secret_value", lambda name: None)

    runner = CliRunner()
    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "[Overall]" in result.output
    assert "- status: warning" in result.output
    assert "[Workspace]" in result.output
    assert "[Telegram]" in result.output
    assert "- pending_requests: 1" in result.output
    assert "[Policy]" in result.output
    assert "- telegram_owner_only_prefixes: external, workspace" in result.output


def test_cli_doctor_reads_openai_api_key_from_env_file(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=openai",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
                "OPENAI_API_KEY=sk-from-dotenv-12345678901234567890",
                "OPENAI_MODEL=gpt-4.1-mini",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)
    monkeypatch.setattr(agent_context, "get_secret_value", lambda name: None)

    runner = CliRunner()
    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "- provider: openai" in result.output
    assert "- configured: yes" in result.output
    assert "OPENAI_API_KEY tidak ditemukan" not in result.output


def test_cli_doctor_reports_platform_runtime_capabilities(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("OTONOMASSIST_SKILL_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("OTONOMASSIST_CONTEXT_BUDGET_CHARS", "4321")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
                "OTONOMASSIST_CONTEXT_BUDGET_CHARS=4321",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)

    runner = CliRunner()
    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "[Platform]" in result.output
    assert "- process_manager:" in result.output
    assert "- service_runtime:" in result.output
    assert "[Toolchains]" in result.output
    assert "[Runtime]" in result.output
    assert "[Context Budget]" in result.output
    assert "- total_budget_chars: 4321" in result.output
    assert "- python:" in result.output
    assert "- skill_timeout_seconds: 12.50" in result.output


def test_cli_compatibility_aliases_still_work(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)

    runner = CliRunner()
    doctor_result = runner.invoke(main, ["--doctor"])
    config_status_result = runner.invoke(main, ["config", "status"])

    assert doctor_result.exit_code == 0
    assert config_status_result.exit_code == 0
    assert doctor_result.output == config_status_result.output


def test_cli_doctor_json_returns_machine_readable_report(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)

    runner = CliRunner()
    result = runner.invoke(main, ["doctor", "--json"])

    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert payload["overall"]["status"] == "warning"
    assert payload["ai"]["provider"] == "ollama"
    assert "policy" in payload
    assert "budget" in payload
    assert "context_budget" in payload
    assert "runtime" in payload
    assert "storage" in payload
    assert "preference_count" in payload["storage"]


def test_cli_run_subcommand_executes_single_message(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    runner = CliRunner()
    result = runner.invoke(main, ["run", "list"])

    assert result.exit_code == 0
    assert "Available skills:" in result.output


def test_cli_history_shows_recent_execution_events(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    runner = CliRunner()
    run_result = runner.invoke(main, ["run", "list"])
    history_result = runner.invoke(main, ["history"])

    assert run_result.exit_code == 0
    assert history_result.exit_code == 0
    assert "Execution History" in history_result.output
    assert "command_received" in history_result.output
    assert "command_completed" in history_result.output


def test_cli_metrics_reports_aggregated_execution_data(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    runner = CliRunner()
    run_result = runner.invoke(main, ["run", "list"])
    metrics_result = runner.invoke(main, ["metrics"])
    metrics_json_result = runner.invoke(main, ["metrics", "--json"])

    payload = json.loads(metrics_json_result.output)
    assert run_result.exit_code == 0
    assert metrics_result.exit_code == 0
    assert "Execution Metrics" in metrics_result.output
    assert payload["summary"]["commands_total"] >= 1


def test_cli_worker_until_idle_processes_runtime_queue(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    runner = CliRunner()
    planner_result = runner.invoke(main, ["run", "planner add memory add dari cli worker"])
    worker_result = runner.invoke(main, ["worker", "--steps", "5", "--until-idle", "--enqueue-first"])
    status_result = runner.invoke(main, ["status", "--json"])

    payload = json.loads(status_result.output)
    assert planner_result.exit_code == 0
    assert worker_result.exit_code == 0
    assert "until idle" in worker_result.output
    assert payload["runtime"]["total_jobs"] >= 1
    assert payload["runtime"]["done_jobs"] >= 1
    assert payload["runtime"]["last_worker_run_at"]


def test_cli_status_reports_metrics_file_path(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)

    runner = CliRunner()
    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "- metrics_file:" in result.output
    assert "- state_db_file:" in result.output


def test_cli_scheduler_runs_cycles_and_updates_status_report(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)

    runner = CliRunner()
    runner.invoke(main, ["run", "planner add memory add dari scheduler"])
    scheduler_result = runner.invoke(main, ["scheduler", "--cycles", "1", "--steps", "5"])
    status_result = runner.invoke(main, ["status", "--json"])

    payload = json.loads(status_result.output)
    assert scheduler_result.exit_code == 0
    assert "Scheduler running 1 cycle" in scheduler_result.output
    assert payload["scheduler"]["last_run_at"]
    assert payload["scheduler"]["last_cycles"] == 1
    assert payload["scheduler"]["last_processed"] >= 1


def test_portable_secret_storage_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(secure_storage.os, "name", "posix")
    monkeypatch.setattr(secure_storage, "STATE_DIR", tmp_path / ".otonomassist")
    monkeypatch.setattr(secure_storage, "PORTABLE_KEY_FILE", tmp_path / ".otonomassist" / "portable_secrets.key")

    encrypted = secure_storage.encrypt_secret("secret-linux-ready")
    decrypted = secure_storage.decrypt_secret(encrypted)
    storage_info = secure_storage.get_secret_storage_info()

    assert encrypted.startswith("portable-v1:")
    assert decrypted == "secret-linux-ready"
    assert storage_info["backend"] == "portable-file-key"
    assert secure_storage.PORTABLE_KEY_FILE.exists()


def test_agent_storage_bootstrap_creates_default_workspace_directory(tmp_path, monkeypatch):
    workspace_root = tmp_path / "workspace"
    data_dir = tmp_path / ".otonomassist"

    monkeypatch.setattr(agent_context, "DATA_DIR", data_dir)
    monkeypatch.setattr(agent_context, "MEMORY_FILE", data_dir / "memory.jsonl")
    monkeypatch.setattr(agent_context, "PLANNER_FILE", data_dir / "planner.json")
    monkeypatch.setattr(agent_context, "LESSONS_FILE", data_dir / "lessons.md")
    monkeypatch.setattr(agent_context, "PROFILE_FILE", data_dir / "profile.md")
    monkeypatch.setattr(agent_context, "PREFERENCES_FILE", data_dir / "preferences.json")
    monkeypatch.setattr(agent_context, "SECRETS_FILE", data_dir / "secrets.json")
    monkeypatch.setattr(agent_context, "EXECUTION_HISTORY_FILE", data_dir / "execution_history.jsonl")
    monkeypatch.setattr(agent_context, "METRICS_FILE", data_dir / "execution_metrics.json")
    monkeypatch.setattr(agent_context, "JOB_QUEUE_FILE", data_dir / "job_queue.json")
    monkeypatch.setattr(agent_context, "SCHEDULER_STATE_FILE", data_dir / "scheduler_state.json")
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", workspace_root)
    monkeypatch.setattr(workspace_guard, "INTERNAL_STATE_ROOT", data_dir)

    agent_context.ensure_agent_storage()

    assert workspace_root.exists()
    assert workspace_root.is_dir()
    assert agent_context.get_state_db_path().exists()


def test_run_process_wrapper_executes_python_command():
    result = run_process([sys.executable, "-c", "print('ok-platform-runner')"])

    assert result["ok"] is True
    assert result["exit_code"] == 0
    assert "ok-platform-runner" in result["stdout"]


def test_assistant_loads_external_skill_from_workspace(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("OTONOMASSIST_EXTERNAL_SKILL_POLICY", "allow-all")
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(workspace_guard, "INTERNAL_STATE_ROOT", tmp_path / ".otonomassist")
    external_skill_dir = workspace_guard.WORKSPACE_ROOT / "skills-external" / "echox"
    (external_skill_dir / "script").mkdir(parents=True, exist_ok=True)
    (external_skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "# EchoX",
                "",
                "## Metadata",
                "- name: echox",
                "- description: External echo skill",
                "- aliases: [echox]",
                "- category: utility",
                "",
                "## Triggers",
                "- echox",
                "",
                "## AI Instructions",
                "Gunakan skill ini untuk mengulang pesan.",
            ]
        ),
        encoding="utf-8",
    )
    (external_skill_dir / "script" / "handler.py").write_text(
        "def handle(args: str) -> str:\n    return f'EXTERNAL:{args}'\n",
        encoding="utf-8",
    )

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("echox halo")

    assert result == "EXTERNAL:halo"


def test_external_audit_lists_workspace_managed_skill(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(workspace_guard, "INTERNAL_STATE_ROOT", tmp_path / ".otonomassist")
    external_skill_dir = workspace_guard.WORKSPACE_ROOT / "skills-external" / "audit-skill"
    (external_skill_dir / "script").mkdir(parents=True, exist_ok=True)
    (external_skill_dir / "SKILL.md").write_text(
        "# Audit Skill\n\n## Metadata\n- name: audit-skill\n- description: Audit\n\n## Triggers\n- audit-skill\n",
        encoding="utf-8",
    )
    external_assets.sync_external_skill_inventory(installed_by="test-suite")

    runner = CliRunner()
    result = runner.invoke(main, ["external", "audit"])

    assert result.exit_code == 0
    assert "External Asset Audit" in result.output
    assert "audit-skill" in result.output
    assert "skills_dir:" in result.output


def test_external_audit_reports_manifest_requirements_and_degraded_compatibility(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(workspace_guard, "INTERNAL_STATE_ROOT", tmp_path / ".otonomassist")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={workspace_guard.WORKSPACE_ROOT}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)
    external_skill_dir = workspace_guard.WORKSPACE_ROOT / "skills-external" / "compat-skill"
    (external_skill_dir / "script").mkdir(parents=True, exist_ok=True)
    (external_skill_dir / "SKILL.md").write_text(
        "# Compat Skill\n\n## Metadata\n- name: compat-skill\n- description: Compat\n\n## Triggers\n- compat-skill\n",
        encoding="utf-8",
    )
    (external_skill_dir / "asset.json").write_text(
        json.dumps(
            {
                "name": "compat-skill",
                "manager": "git",
                "version": "1.2.3",
                "requires": ["git", "missing-toolchain-for-test"],
                "platforms": ["windows", "linux"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    sync_result = runner.invoke(main, ["external", "sync"])
    audit_result = runner.invoke(main, ["external", "audit"])
    status_result = runner.invoke(main, ["status"])

    assert sync_result.exit_code == 0
    assert "External assets synced:" in sync_result.output
    assert audit_result.exit_code == 0
    assert "compat-skill" in audit_result.output
    assert "compatibility=degraded" in audit_result.output
    assert "requirements: git, missing-toolchain-for-test" in audit_result.output
    assert "missing_toolchains: missing-toolchain-for-test" in audit_result.output
    assert status_result.exit_code == 0
    assert "[External Assets]" in status_result.output
    assert "- incompatible_count: 1" in status_result.output
    assert "- unapproved_count: 1" in status_result.output


def test_cli_external_install_copies_local_skill_and_audits_it(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(workspace_guard, "INTERNAL_STATE_ROOT", tmp_path / ".otonomassist")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={workspace_guard.WORKSPACE_ROOT}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)

    source_skill_dir = tmp_path / "external-source-skill"
    (source_skill_dir / "script").mkdir(parents=True, exist_ok=True)
    (source_skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "# Local External Skill",
                "",
                "## Metadata",
                "- name: local-ext",
                "- description: Installed from local path",
                "",
                "## Triggers",
                "- local-ext",
            ]
        ),
        encoding="utf-8",
    )
    (source_skill_dir / "asset.json").write_text(
        json.dumps(
            {
                "name": "local-ext",
                "manager": "local-path",
                "version": "0.0.1",
                "requires": ["python"],
                "capabilities": ["workspace_read"],
                "platforms": ["windows", "linux"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (source_skill_dir / "script" / "handler.py").write_text(
        "def handle(args: str) -> str:\n    return f'LOCAL-EXT:{args}'\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    install_result = runner.invoke(main, ["external", "install", str(source_skill_dir)])
    audit_result = runner.invoke(main, ["external", "audit"])

    assert install_result.exit_code == 0
    assert "External skill installed" in install_result.output
    assert "- name: local-ext" in install_result.output
    assert "- compatibility: ready" in install_result.output
    installed_dir = workspace_guard.WORKSPACE_ROOT / "skills-external" / "external-source-skill"
    assert installed_dir.exists()
    assert (installed_dir / "SKILL.md").exists()
    assert audit_result.exit_code == 0
    assert "local-ext" in audit_result.output
    assert "event_count:" in audit_result.output

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    assert assistant.execute("local-ext halo") != "LOCAL-EXT:halo"

    approve_result = runner.invoke(main, ["external", "approve", "local-ext"])
    assert approve_result.exit_code == 0

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    assert assistant.execute("local-ext halo") == "LOCAL-EXT:halo"

    state = external_assets.load_external_asset_registry()
    assert len(state["events"]) >= 1
    assert any(event["action"] == "install-request" for event in state["events"])
    assert any(event["action"] == "approval-approved" for event in state["events"])


def test_external_reject_disables_loading_for_approved_skill(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(workspace_guard, "INTERNAL_STATE_ROOT", tmp_path / ".otonomassist")
    source_skill_dir = tmp_path / "external-reject-skill"
    (source_skill_dir / "script").mkdir(parents=True, exist_ok=True)
    (source_skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "# Rejectable External Skill",
                "",
                "## Metadata",
                "- name: rejectable-ext",
                "- description: Installed from local path",
                "",
                "## Triggers",
                "- rejectable-ext",
            ]
        ),
        encoding="utf-8",
    )
    (source_skill_dir / "script" / "handler.py").write_text(
        "def handle(args: str) -> str:\n    return f'REJECTABLE:{args}'\n",
        encoding="utf-8",
    )
    (source_skill_dir / "asset.json").write_text(
        json.dumps(
            {
                "name": "rejectable-ext",
                "manager": "local-path",
                "version": "0.0.1",
                "capabilities": ["workspace_read"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    runner.invoke(main, ["external", "install", str(source_skill_dir)])
    runner.invoke(main, ["external", "approve", "rejectable-ext"])

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    assert assistant.execute("rejectable-ext halo") == "REJECTABLE:halo"

    reject_result = runner.invoke(main, ["external", "reject", "rejectable-ext"])
    assert reject_result.exit_code == 0

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    assert assistant.execute("rejectable-ext halo") != "REJECTABLE:halo"


def test_external_approve_requires_declared_capabilities(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(workspace_guard, "INTERNAL_STATE_ROOT", tmp_path / ".otonomassist")

    source_skill_dir = tmp_path / "undeclared-capability-skill"
    (source_skill_dir / "script").mkdir(parents=True, exist_ok=True)
    (source_skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "# Undeclared Capability Skill",
                "",
                "## Metadata",
                "- name: undeclared-ext",
                "- description: Installed from local path",
                "",
                "## Triggers",
                "- undeclared-ext",
            ]
        ),
        encoding="utf-8",
    )
    (source_skill_dir / "script" / "handler.py").write_text(
        "def handle(args: str) -> str:\n    return f'UNDECLARED:{args}'\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    install_result = runner.invoke(main, ["external", "install", str(source_skill_dir)])
    approve_result = runner.invoke(main, ["external", "approve", "undeclared-ext"])
    audit_result = runner.invoke(main, ["external", "audit"])

    assert install_result.exit_code == 0
    assert approve_result.exit_code != 0
    assert "capability declaration belum valid" in approve_result.output
    assert "undeclared_capability_count: 1" in audit_result.output


def test_external_approve_rejects_disallowed_capability_until_policy_allows_it(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(workspace_guard, "INTERNAL_STATE_ROOT", tmp_path / ".otonomassist")

    source_skill_dir = tmp_path / "network-skill"
    (source_skill_dir / "script").mkdir(parents=True, exist_ok=True)
    (source_skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "# Network Skill",
                "",
                "## Metadata",
                "- name: network-ext",
                "- description: Installed from local path",
                "",
                "## Triggers",
                "- network-ext",
            ]
        ),
        encoding="utf-8",
    )
    (source_skill_dir / "script" / "handler.py").write_text(
        "def handle(args: str) -> str:\n    return f'NETWORK:{args}'\n",
        encoding="utf-8",
    )
    (source_skill_dir / "asset.json").write_text(
        json.dumps(
            {
                "name": "network-ext",
                "manager": "local-path",
                "version": "0.0.1",
                "capabilities": ["network"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    install_result = runner.invoke(main, ["external", "install", str(source_skill_dir)])
    approve_result = runner.invoke(main, ["external", "approve", "network-ext"])
    audit_result = runner.invoke(main, ["external", "audit"])

    assert install_result.exit_code == 0
    assert approve_result.exit_code != 0
    assert "capability declaration belum valid" in approve_result.output
    assert "blocked_capability_count: 1" in audit_result.output
    assert "allowed_capabilities: workspace_read" in audit_result.output

    monkeypatch.setenv("OTONOMASSIST_EXTERNAL_CAPABILITY_ALLOW", "workspace_read,network")
    runner.invoke(main, ["external", "sync"])
    approve_after_allow = runner.invoke(main, ["external", "approve", "network-ext"])
    assert approve_after_allow.exit_code == 0


def test_external_install_rejects_invalid_source_and_logs_failure(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(workspace_guard, "INTERNAL_STATE_ROOT", tmp_path / ".otonomassist")

    with pytest.raises(ValueError):
        external_installer.install_external_skill("not-a-valid-source", actor="test-suite")

    state = external_assets.load_external_asset_registry()
    assert len(state["events"]) == 1
    assert state["events"][0]["result"] == "failed"
    assert state["events"][0]["action"] == "install-request"


def test_skill_loader_parses_autonomy_metadata(tmp_path):
    skills_dir = tmp_path / "skills"
    skill_dir = skills_dir / "taxonomy-skill"
    (skill_dir / "script").mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "# Taxonomy Skill",
                "",
                "## Metadata",
                "- name: taxonomy-skill",
                "- description: Skill dengan metadata otonom",
                "- aliases: [tax-skill]",
                "- category: utility",
                "- autonomy_category: execution",
                "- risk_level: high",
                "- side_effects: [planner_write, memory_write]",
                "- requires: [ai_provider, workspace_access]",
                "- idempotency: non_idempotent",
                "",
                "## Triggers",
                "- taxonomy-skill",
                "",
                "## AI Instructions",
                "Gunakan untuk test metadata.",
            ]
        ),
        encoding="utf-8",
    )
    (skill_dir / "script" / "handler.py").write_text(
        "def handle(args: str) -> str:\n    return 'ok'\n",
        encoding="utf-8",
    )

    registry = SkillRegistry()
    loader = SkillLoader(skills_dir)

    count = loader.load_all(registry)

    assert count == 1
    skill = registry.get("taxonomy-skill")
    assert skill is not None
    assert skill.definition.autonomy_category == "execution"
    assert skill.definition.risk_level == "high"
    assert skill.definition.side_effects == ["planner_write", "memory_write"]
    assert skill.definition.requires == ["ai_provider", "workspace_access"]
    assert skill.definition.idempotency == "non_idempotent"


def test_assistant_and_cli_expose_skill_layer_audit(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=ollama",
                f"OTONOMASSIST_WORKSPACE_ROOT={tmp_path}",
                "OTONOMASSIST_WORKSPACE_ACCESS=ro",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "ENV_FILE", env_file)
    import otonomassist.core.config_doctor as config_doctor  # noqa: E402

    monkeypatch.setattr(config_doctor, "ENV_FILE", env_file)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    audit_text = assistant.execute("skills audit")

    assert "Skill Layer Audit" in audit_text
    assert "[planning]" in audit_text
    assert "[governance]" in audit_text
    assert "secrets [risk=critical" in audit_text
    assert "workspace [risk=medium, idempotency=idempotent]" in audit_text

    runner = CliRunner()
    cli_result = runner.invoke(main, ["skills", "audit"])

    assert cli_result.exit_code == 0
    assert "Skill Layer Audit" in cli_result.output
