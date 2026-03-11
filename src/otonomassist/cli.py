"""CLI interface for OtonomAssist."""

import sys
from pathlib import Path

import click

from otonomassist.core import Assistant, TransportContext


@click.command()
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Run in interactive mode",
)
@click.argument("command", required=False)
def main(skills_dir: Path, interactive: bool, command: str | None) -> None:
    """OtonomAssist - Autonomous Assistant."""
    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()

    if interactive or command is None:
        run_interactive(assistant)
    else:
        result = assistant.handle_message(command, TransportContext(source="cli"))
        click.echo(result)


def run_interactive(assistant: Assistant) -> None:
    """Run the assistant in interactive mode."""
    click.echo("OtonomAssist v0.1.0")
    click.echo("Type 'help' for available commands, 'exit' to quit.")
    click.echo("")

    while True:
        try:
            user_input = input("assistant: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                click.echo("Goodbye!")
                break

            result = assistant.handle_message(user_input, TransportContext(source="cli"))
            click.echo(result)

        except KeyboardInterrupt:
            click.echo("\nGoodbye!")
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()
