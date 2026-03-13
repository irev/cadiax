"""Telegram transport runner for Cadiax."""

from __future__ import annotations

from pathlib import Path

import click
from dotenv import dotenv_values

from cadiax.core import Assistant
from cadiax.core.path_layout import get_config_env_file
from cadiax.interfaces.telegram import TelegramPollingTransport
from cadiax.services.interactions import ConversationService


def telegram_is_enabled() -> bool:
    """Return whether Telegram transport is enabled by user configuration."""
    env_file = get_config_env_file()
    env_values = dotenv_values(env_file) if env_file.exists() else {}
    raw = str(env_values.get("TELEGRAM_ENABLED", "") or "").strip().lower()
    if raw:
        return raw in {"1", "true", "yes", "on"}
    return bool(env_values.get("TELEGRAM_BOT_TOKEN"))


def run_telegram_transport(skills_dir: Path) -> None:
    """Run Telegram long polling for Cadiax."""
    if not telegram_is_enabled():
        raise click.ClickException(
            "Telegram sedang nonaktif. Aktifkan lewat `cadiax setup` atau set TELEGRAM_ENABLED=true."
        )
    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()
    service = ConversationService(assistant)

    transport = TelegramPollingTransport()
    if not transport.is_configured():
        raise click.ClickException(
            "Telegram bot token tidak ditemukan. "
            "Set TELEGRAM_BOT_TOKEN atau simpan via `secrets set telegram_bot_token <token>`."
        )

    click.echo("Starting Telegram polling...")
    transport.run(service)


@click.command()
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def main(skills_dir: Path) -> None:
    """Run Telegram long polling for Cadiax."""
    run_telegram_transport(skills_dir)


if __name__ == "__main__":
    main()
