"""Telegram transport runner for OtonomAssist."""

from __future__ import annotations

from pathlib import Path

import click

from otonomassist.core import Assistant
from otonomassist.transports import TelegramPollingTransport


def run_telegram_transport(skills_dir: Path) -> None:
    """Run Telegram long polling for OtonomAssist."""
    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()

    transport = TelegramPollingTransport()
    if not transport.is_configured():
        raise click.ClickException(
            "Telegram bot token tidak ditemukan. "
            "Set TELEGRAM_BOT_TOKEN atau simpan via `secrets set telegram_bot_token <token>`."
        )

    click.echo("Starting Telegram polling...")
    transport.run(assistant)


@click.command()
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def main(skills_dir: Path) -> None:
    """Run Telegram long polling for OtonomAssist."""
    run_telegram_transport(skills_dir)


if __name__ == "__main__":
    main()
