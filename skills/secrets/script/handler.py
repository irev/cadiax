"""Secrets skill handler."""

from __future__ import annotations

from datetime import datetime, timezone
import os

from otonomassist.core.agent_context import load_secrets_state, save_secrets_state
from otonomassist.core.secure_storage import decrypt_secret, encrypt_secret


ENV_SECRET_MAP = {
    "OPENAI_API_KEY": "openai_api_key",
    "ANTHROPIC_API_KEY": "anthropic_api_key",
    "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
}


def handle(args: str) -> str:
    """Manage local secrets storage."""
    args = args.strip()
    if not args:
        return _usage()

    command, _, remainder = args.partition(" ")
    command = command.lower().strip()
    remainder = remainder.strip()

    if command == "set":
        return _set_secret(remainder)
    if command == "list":
        return _list_secrets()
    if command == "show":
        return _show_secret(remainder)
    if command == "delete":
        return _delete_secret(remainder)
    if command == "import-env":
        return _import_env_secrets()

    return _usage()


def _usage() -> str:
    return (
        "Usage: secrets <set|list|show|delete|import-env> ...\n"
        "Examples:\n"
        "- secrets set github_token ghp_xxx\n"
        "- secrets list\n"
        "- secrets show github_token\n"
        "- secrets import-env"
    )


def _set_secret(args: str) -> str:
    name, _, value = args.partition(" ")
    name = name.strip()
    value = value.strip()
    if not name or not value:
        return "Format: secrets set <name> <value>"

    state = load_secrets_state()
    _migrate_plaintext_secrets(state)
    secrets = state.setdefault("secrets", {})
    secrets[name] = {
        "encrypted_value": encrypt_secret(value),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": _fingerprint(value),
    }
    save_secrets_state(state)
    return f"Secret '{name}' tersimpan."


def _list_secrets() -> str:
    state = load_secrets_state()
    _migrate_plaintext_secrets(state)
    secrets = state.get("secrets", {})
    if not secrets:
        return "Belum ada secret tersimpan."

    lines = ["Stored secrets:"]
    for name, meta in sorted(secrets.items()):
        lines.append(f"- {name}: {meta.get('fingerprint', '(unknown)')}")
    return "\n".join(lines)


def _show_secret(name: str) -> str:
    if not name:
        return "Secrets show membutuhkan nama secret."

    state = load_secrets_state()
    _migrate_plaintext_secrets(state)
    meta = state.get("secrets", {}).get(name)
    if not meta:
        return f"Secret '{name}' tidak ditemukan."

    return (
        f"Secret '{name}'\n"
        f"- fingerprint: {meta.get('fingerprint', '-')}\n"
        f"- updated_at: {meta.get('updated_at', '-')}\n"
        "- value: (hidden)"
    )


def _delete_secret(name: str) -> str:
    if not name:
        return "Secrets delete membutuhkan nama secret."

    state = load_secrets_state()
    _migrate_plaintext_secrets(state)
    secrets = state.get("secrets", {})
    if name not in secrets:
        return f"Secret '{name}' tidak ditemukan."

    del secrets[name]
    save_secrets_state(state)
    return f"Secret '{name}' dihapus."


def _import_env_secrets() -> str:
    """Import known credentials from environment variables into secrets."""
    state = load_secrets_state()
    _migrate_plaintext_secrets(state)
    secrets = state.setdefault("secrets", {})
    imported: list[str] = []
    skipped: list[str] = []

    for env_name, secret_name in ENV_SECRET_MAP.items():
        value = os.getenv(env_name, "").strip()
        if not value:
            continue

        existing = secrets.get(secret_name, {})
        existing_fingerprint = existing.get("fingerprint")
        incoming_fingerprint = _fingerprint(value)
        if existing_fingerprint == incoming_fingerprint:
            skipped.append(secret_name)
            continue

        secrets[secret_name] = {
            "encrypted_value": encrypt_secret(value),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "fingerprint": incoming_fingerprint,
            "source": f"env:{env_name}",
        }
        imported.append(secret_name)

    if imported:
        save_secrets_state(state)

    if not imported and not skipped:
        return "Tidak ada credential environment yang bisa di-import."

    lines: list[str] = []
    if imported:
        lines.append("Imported secrets:")
        for name in imported:
            lines.append(f"- {name}")
    if skipped:
        lines.append("Skipped secrets:")
        for name in skipped:
            lines.append(f"- {name} (fingerprint sama)")
    lines.append(
        "Nilai di .env tidak dihapus otomatis; pindahkan manual jika ingin mengurangi jejak secret di environment."
    )
    return "\n".join(lines)


def _fingerprint(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * 8}...{value[-4:]}"


def _migrate_plaintext_secrets(state: dict) -> None:
    """Migrate legacy plaintext secrets to encrypted storage."""
    changed = False
    for meta in state.get("secrets", {}).values():
        raw_value = meta.pop("value", None)
        if raw_value and "encrypted_value" not in meta:
            meta["encrypted_value"] = encrypt_secret(raw_value)
            meta["fingerprint"] = _fingerprint(raw_value)
            changed = True
        if "encrypted_value" in meta and "fingerprint" not in meta:
            try:
                decrypted = decrypt_secret(meta["encrypted_value"])
                meta["fingerprint"] = _fingerprint(decrypted)
                changed = True
            except Exception:
                continue
    if changed:
        save_secrets_state(state)
