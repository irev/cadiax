"""Interactive setup wizard for first-run and reconfiguration."""

from __future__ import annotations

import os
import re
from pathlib import Path

import click
from dotenv import dotenv_values

import cadiax.core.agent_context as agent_context
from cadiax.core.secure_storage import encrypt_secret, get_secret_storage_info


ENV_FILE = agent_context.PROJECT_ROOT / ".env"
REMOTE_PROVIDER_SECRETS = {
    "openai": ("OPENAI_API_KEY", "openai_api_key"),
    "claude": ("ANTHROPIC_API_KEY", "anthropic_api_key"),
}


def should_recommend_setup() -> bool:
    """Check whether the user should be nudged to run setup."""
    env_values = _load_env_values(ENV_FILE)
    provider = (env_values.get("AI_PROVIDER") or "openai").strip().lower()
    if "AI_PROVIDER" not in env_values:
        return True
    if "OTONOMASSIST_WORKSPACE_ACCESS" not in env_values:
        return True
    secret_name = REMOTE_PROVIDER_SECRETS.get(provider, ("", ""))[1]
    if secret_name and not agent_context.get_secret_value(secret_name) and not env_values.get(
        REMOTE_PROVIDER_SECRETS[provider][0]
    ):
        return True
    return False


def run_setup_wizard() -> str:
    """Run interactive setup and persist the resulting configuration."""
    agent_context.ensure_agent_storage()
    env_values = _load_env_values(ENV_FILE)
    env_updates: dict[str, str] = {}
    secret_updates: dict[str, str] = {}

    click.echo("Cadiax setup")
    click.echo("Wizard ini menyiapkan konfigurasi first-run atau reconfigure yang aman.")
    click.echo(f"Secret backend aktif: {get_secret_storage_info()['backend']}")
    click.echo("")

    provider = _prompt_choice(
        "Pilih AI provider",
        ["openai", "claude", "ollama", "lmstudio"],
        default=(env_values.get("AI_PROVIDER") or "openai").strip().lower(),
    )
    env_updates["AI_PROVIDER"] = provider

    workspace_root = click.prompt(
        "Workspace root",
        default=env_values.get("OTONOMASSIST_WORKSPACE_ROOT") or str(agent_context.PROJECT_ROOT / "workspace"),
        show_default=True,
    ).strip()
    env_updates["OTONOMASSIST_WORKSPACE_ROOT"] = workspace_root

    workspace_access = _prompt_choice(
        "Mode akses workspace",
        ["ro", "rw"],
        default=(env_values.get("OTONOMASSIST_WORKSPACE_ACCESS") or "ro").strip().lower(),
    )
    if workspace_access == "rw":
        confirmed = click.confirm(
            "Mode 'rw' mengizinkan perubahan file workspace. Lanjutkan?",
            default=False,
        )
        if not confirmed:
            workspace_access = "ro"
    env_updates["OTONOMASSIST_WORKSPACE_ACCESS"] = workspace_access

    _collect_provider_settings(provider, env_values, env_updates, secret_updates)
    telegram_enabled = click.confirm(
        "Konfigurasi Telegram sekarang?",
        default=_has_existing_telegram_config(env_values),
    )
    if telegram_enabled:
        _collect_telegram_settings(env_values, env_updates, secret_updates)

    summary_lines = _build_summary(env_updates, secret_updates)
    click.echo("")
    click.echo("Ringkasan konfigurasi:")
    for line in summary_lines:
        click.echo(f"- {line}")
    click.echo("")

    if not click.confirm("Simpan konfigurasi ini?", default=True):
        return "Setup dibatalkan."

    _upsert_env_file(ENV_FILE, env_updates)
    _store_secrets(secret_updates)
    _apply_runtime_env(env_updates)

    return (
        "Setup selesai.\n"
        f"- file env: {ENV_FILE}\n"
        f"- provider: {provider}\n"
        f"- workspace_access: {workspace_access}\n"
        f"- secret tersimpan: {len(secret_updates)}"
    )


def _collect_provider_settings(
    provider: str,
    env_values: dict[str, str],
    env_updates: dict[str, str],
    secret_updates: dict[str, str],
) -> None:
    if provider == "openai":
        env_updates["OPENAI_BASE_URL"] = click.prompt(
            "OpenAI base URL",
            default=env_values.get("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            show_default=True,
        ).strip()
        env_updates["OPENAI_MODEL"] = click.prompt(
            "OpenAI model",
            default=env_values.get("OPENAI_MODEL") or "gpt-4.1-mini",
            show_default=True,
        ).strip()
        env_updates["OPENAI_FALLBACK_MODEL"] = click.prompt(
            "OpenAI fallback model",
            default=env_values.get("OPENAI_FALLBACK_MODEL") or "gpt-4o",
            show_default=True,
        ).strip()
        env_updates["OPENAI_WEB_MODEL"] = click.prompt(
            "OpenAI web model",
            default=env_values.get("OPENAI_WEB_MODEL") or "gpt-4.1",
            show_default=True,
        ).strip()
        _collect_secret_preference(
            "OPENAI_API_KEY",
            "openai_api_key",
            "Simpan OpenAI API key ke encrypted secrets lokal?",
            env_values,
            env_updates,
            secret_updates,
        )
        return

    if provider == "claude":
        env_updates["CLAUDE_BASE_URL"] = click.prompt(
            "Claude base URL",
            default=env_values.get("CLAUDE_BASE_URL") or "https://api.anthropic.com",
            show_default=True,
        ).strip()
        env_updates["CLAUDE_MODEL"] = click.prompt(
            "Claude model",
            default=env_values.get("CLAUDE_MODEL") or "claude-3-haiku-20240307",
            show_default=True,
        ).strip()
        _collect_secret_preference(
            "ANTHROPIC_API_KEY",
            "anthropic_api_key",
            "Simpan Anthropic API key ke encrypted secrets lokal?",
            env_values,
            env_updates,
            secret_updates,
        )
        return

    if provider == "ollama":
        env_updates["OLLAMA_BASE_URL"] = click.prompt(
            "Ollama base URL",
            default=env_values.get("OLLAMA_BASE_URL") or "http://localhost:11434",
            show_default=True,
        ).strip()
        env_updates["OLLAMA_MODEL"] = click.prompt(
            "Ollama model",
            default=env_values.get("OLLAMA_MODEL") or "llama3.2",
            show_default=True,
        ).strip()
        return

    env_updates["LMSTUDIO_BASE_URL"] = click.prompt(
        "LM Studio base URL",
        default=env_values.get("LMSTUDIO_BASE_URL") or "http://localhost:1234/v1",
        show_default=True,
    ).strip()
    env_updates["LMSTUDIO_MODEL"] = click.prompt(
        "LM Studio model",
        default=env_values.get("LMSTUDIO_MODEL") or "local-model",
        show_default=True,
    ).strip()


def _collect_telegram_settings(
    env_values: dict[str, str],
    env_updates: dict[str, str],
    secret_updates: dict[str, str],
) -> None:
    _collect_secret_preference(
        "TELEGRAM_BOT_TOKEN",
        "telegram_bot_token",
        "Simpan Telegram bot token ke encrypted secrets lokal?",
        env_values,
        env_updates,
        secret_updates,
    )
    env_updates["TELEGRAM_OWNER_IDS"] = click.prompt(
        "Telegram owner IDs (pisahkan dengan koma bila lebih dari satu)",
        default=env_values.get("TELEGRAM_OWNER_IDS") or "",
        show_default=False,
    ).strip()
    env_updates["TELEGRAM_DM_POLICY"] = _prompt_choice(
        "Telegram DM policy",
        ["pairing", "owner", "open", "disabled"],
        default=(env_values.get("TELEGRAM_DM_POLICY") or "pairing").strip().lower(),
    )
    env_updates["TELEGRAM_ALLOW_FROM"] = click.prompt(
        "Telegram approved DM users tambahan (opsional)",
        default=env_values.get("TELEGRAM_ALLOW_FROM") or "",
        show_default=False,
    ).strip()
    env_updates["TELEGRAM_GROUP_POLICY"] = _prompt_choice(
        "Telegram group policy",
        ["allowlist", "disabled"],
        default=(env_values.get("TELEGRAM_GROUP_POLICY") or "allowlist").strip().lower(),
    )
    env_updates["TELEGRAM_GROUPS"] = click.prompt(
        "Telegram group/chat allowlist (opsional)",
        default=env_values.get("TELEGRAM_GROUPS") or "",
        show_default=False,
    ).strip()
    env_updates["TELEGRAM_GROUP_ALLOW_FROM"] = click.prompt(
        "Telegram allowed group senders tambahan (opsional)",
        default=env_values.get("TELEGRAM_GROUP_ALLOW_FROM") or "",
        show_default=False,
    ).strip()
    env_updates["TELEGRAM_REQUIRE_MENTION"] = "true" if click.confirm(
        "Wajib mention/reply bot di group?",
        default=(env_values.get("TELEGRAM_REQUIRE_MENTION") or "true").strip().lower() == "true",
    ) else "false"


def _collect_secret_preference(
    env_name: str,
    secret_name: str,
    store_prompt: str,
    env_values: dict[str, str],
    env_updates: dict[str, str],
    secret_updates: dict[str, str],
) -> None:
    existing_secret = agent_context.get_secret_value(secret_name)
    existing_env = env_values.get(env_name, "")
    has_existing = bool(existing_secret or existing_env)
    use_secret_storage = click.confirm(store_prompt, default=True)
    if use_secret_storage:
        env_updates[env_name] = ""
        replace = click.confirm(
            f"Perbarui nilai {env_name} sekarang?",
            default=not has_existing,
        )
        if replace:
            value = click.prompt(
                f"Masukkan {env_name}",
                default="",
                show_default=False,
                hide_input=True,
            ).strip()
            if value:
                secret_updates[secret_name] = value
        return

    value = click.prompt(
        f"Masukkan {env_name} untuk disimpan di .env",
        default=existing_env,
        show_default=False,
        hide_input=True,
    ).strip()
    env_updates[env_name] = value


def _build_summary(env_updates: dict[str, str], secret_updates: dict[str, str]) -> list[str]:
    summary: list[str] = []
    for key in sorted(env_updates):
        value = env_updates[key]
        if "KEY" in key or "TOKEN" in key:
            if value:
                summary.append(f"{key}=********")
            else:
                summary.append(f"{key}=(kosong)")
            continue
        summary.append(f"{key}={value or '(kosong)'}")
    if secret_updates:
        summary.append(
            "encrypted secrets: " + ", ".join(sorted(secret_updates))
        )
    return summary


def _load_env_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values = dotenv_values(path)
    return {key: value or "" for key, value in values.items()}


def _upsert_env_file(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(updates)
    updated_lines: list[str] = []
    key_pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")

    for line in lines:
        match = key_pattern.match(line)
        if not match:
            updated_lines.append(line)
            continue
        key = match.group(1)
        if key not in remaining:
            updated_lines.append(line)
            continue
        updated_lines.append(f"{key}={_format_env_value(remaining.pop(key))}")

    if updated_lines and updated_lines[-1].strip():
        updated_lines.append("")
    for key, value in remaining.items():
        updated_lines.append(f"{key}={_format_env_value(value)}")

    path.write_text("\n".join(updated_lines).rstrip() + "\n", encoding="utf-8")


def _format_env_value(value: str) -> str:
    if value == "":
        return ""
    if re.search(r"\s|#|=|\"", value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _store_secrets(secret_updates: dict[str, str]) -> None:
    if not secret_updates:
        return
    state = agent_context.load_secrets_state()
    secrets_state = state.setdefault("secrets", {})
    for name, value in secret_updates.items():
        secrets_state[name] = {
            "encrypted_value": encrypt_secret(value),
            "fingerprint": _fingerprint(value),
        }
    agent_context.save_secrets_state(state)


def _apply_runtime_env(env_updates: dict[str, str]) -> None:
    for key, value in env_updates.items():
        os.environ[key] = value


def _has_existing_telegram_config(env_values: dict[str, str]) -> bool:
    if agent_context.get_secret_value("telegram_bot_token"):
        return True
    if env_values.get("TELEGRAM_BOT_TOKEN"):
        return True
    return any(
        env_values.get(key)
        for key in (
            "TELEGRAM_OWNER_IDS",
            "TELEGRAM_ALLOW_FROM",
            "TELEGRAM_GROUPS",
            "TELEGRAM_GROUP_ALLOW_FROM",
        )
    )


def _prompt_choice(label: str, options: list[str], default: str) -> str:
    click.echo(label + ":")
    for index, option in enumerate(options, start=1):
        suffix = " (default)" if option == default else ""
        click.echo(f"  {index}. {option}{suffix}")
    while True:
        raw = click.prompt("Pilih nomor atau ketik nilai", default=default, show_default=True).strip().lower()
        if raw in options:
            return raw
        if raw.isdigit():
            choice_index = int(raw) - 1
            if 0 <= choice_index < len(options):
                return options[choice_index]
        click.echo("Pilihan tidak valid.")


def _fingerprint(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * 8}...{value[-4:]}"
