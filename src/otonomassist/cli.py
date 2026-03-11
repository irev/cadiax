"""CLI interface for OtonomAssist."""

from __future__ import annotations

from pathlib import Path
import json

import click

from otonomassist.core import Assistant, TransportContext, get_config_status_data, get_config_status_report, render_execution_history
from otonomassist.core.external_assets import render_external_asset_audit, sync_external_skill_inventory
from otonomassist.core.external_installer import install_external_skill, render_external_install_result
from otonomassist.core.job_runtime import complete_job, enqueue_ready_planner_task, lease_next_job, render_job_queue
from otonomassist.core.setup_wizard import run_setup_wizard, should_recommend_setup
from otonomassist.telegram_cli import run_telegram_transport


def _build_assistant(skills_dir: Path) -> Assistant:
    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()
    return assistant


def _run_interactive(assistant: Assistant) -> None:
    click.echo("OtonomAssist v0.1.0")
    click.echo("Type 'help' for available commands, 'exit' to quit.")
    if should_recommend_setup():
        click.echo("Konfigurasi awal belum lengkap. Jalankan `otonomassist setup` untuk wizard interaktif.")
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


@click.group(
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
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
@click.option(
    "--setup",
    is_flag=True,
    help="Compatibility alias for `otonomassist setup`",
)
@click.option(
    "--doctor",
    is_flag=True,
    help="Compatibility alias for `otonomassist doctor`",
)
@click.pass_context
def main(
    ctx: click.Context,
    skills_dir: Path,
    interactive: bool,
    setup: bool,
    doctor: bool,
) -> None:
    """OtonomAssist - Autonomous Assistant."""
    if setup:
        click.echo(run_setup_wizard())
        return
    if doctor:
        click.echo(get_config_status_report())
        return
    if ctx.invoked_subcommand:
        return

    assistant = _build_assistant(skills_dir)
    if interactive or not ctx.args:
        _run_interactive(assistant)
        return

    command = " ".join(ctx.args).strip()
    result = assistant.handle_message(command, TransportContext(source="cli"))
    click.echo(result)


@main.command("setup")
def setup_command() -> None:
    """Run interactive first-run/reconfigure setup wizard."""
    click.echo(run_setup_wizard())


@main.command("doctor")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON status")
def doctor_command(as_json: bool) -> None:
    """Show read-only configuration status and diagnostics."""
    if as_json:
        click.echo(json.dumps(get_config_status_data(), ensure_ascii=False, indent=2))
        return
    click.echo(get_config_status_report())


@main.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON status")
def status_command(as_json: bool) -> None:
    """Alias for doctor."""
    if as_json:
        click.echo(json.dumps(get_config_status_data(), ensure_ascii=False, indent=2))
        return
    click.echo(get_config_status_report())


@main.command("history")
def history_command() -> None:
    """Show recent execution history."""    
    click.echo(render_execution_history())


@main.group("jobs")
def jobs_group() -> None:
    """Runtime job queue commands."""


@jobs_group.command("list")
def jobs_list_command() -> None:
    """Show runtime job queue."""
    click.echo(render_job_queue())


@jobs_group.command("enqueue")
def jobs_enqueue_command() -> None:
    """Enqueue the next ready planner task."""
    job = enqueue_ready_planner_task()
    if not job:
        click.echo("Tidak ada task ready untuk dimasukkan ke job queue.")
        return
    click.echo(f"Job #{job['id']} dibuat untuk task #{job['task_id']} {job['task_text']}")


@main.command("worker")
@click.option("--steps", default=1, type=int, show_default=True, help="Jumlah job yang diproses")
@click.option("--enqueue-first", is_flag=True, help="Enqueue ready planner task sebelum memproses")
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def worker_command(steps: int, enqueue_first: bool, skills_dir: Path) -> None:
    """Process runtime jobs from the queue."""
    assistant = _build_assistant(skills_dir)
    lines: list[str] = [f"Worker processing up to {max(1, steps)} job(s):"]
    processed = 0
    for _ in range(max(1, steps)):
        if enqueue_first:
            enqueue_ready_planner_task()
        job = lease_next_job()
        if not job:
            lines.append("- idle: tidak ada job queued")
            break
        result = assistant.handle_message("executor next", TransportContext(source="worker"))
        status = "done"
        if result.startswith("Task #") and "dijadwalkan ulang" in result:
            status = "requeued"
        elif result.startswith("Task #") and "gagal dieksekusi" in result:
            status = "failed"
        complete_job(int(job["id"]), status)
        processed += 1
        lines.append(f"- job {job['id']}: task #{job['task_id']} -> {status}")
    lines.append(f"- processed: {processed}")
    click.echo("\n".join(lines))


@main.group("config")
def config_group() -> None:
    """Configuration commands."""


@config_group.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON status")
def config_status_command(as_json: bool) -> None:
    """Show configuration status."""
    if as_json:
        click.echo(json.dumps(get_config_status_data(), ensure_ascii=False, indent=2))
        return
    click.echo(get_config_status_report())


@config_group.command("setup")
def config_setup_command() -> None:
    """Run configuration wizard."""
    click.echo(run_setup_wizard())


@main.command("chat")
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def chat_command(skills_dir: Path) -> None:
    """Run interactive chat mode."""
    assistant = _build_assistant(skills_dir)
    _run_interactive(assistant)


@main.command("run")
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
@click.argument("message", required=True)
def run_command(skills_dir: Path, message: str) -> None:
    """Run a single assistant message."""
    assistant = _build_assistant(skills_dir)
    result = assistant.handle_message(message, TransportContext(source="cli"))
    click.echo(result)


@main.command("telegram")
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def telegram_command(skills_dir: Path) -> None:
    """Run Telegram long polling transport."""
    run_telegram_transport(skills_dir)


@main.group("external")
def external_group() -> None:
    """External asset audit commands."""


@external_group.command("audit")
def external_audit_command() -> None:
    """Show audited external assets and layout."""
    click.echo(render_external_asset_audit())


@external_group.command("list")
def external_list_command() -> None:
    """Alias for external audit."""
    click.echo(render_external_asset_audit())


@external_group.command("sync")
def external_sync_command() -> None:
    """Refresh audited external assets from workspace."""
    result = sync_external_skill_inventory(installed_by="cli")
    click.echo(
        f"External assets synced: {result['discovered_count']} scanned"
    )


@external_group.command("install")
@click.argument("source", required=True)
def external_install_command(source: str) -> None:
    """Install an external skill from local path or git URL."""
    try:
        result = install_external_skill(source, actor="cli")
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(render_external_install_result(result))


@main.group("skills")
def skills_group() -> None:
    """Skill taxonomy and audit commands."""


@skills_group.command("audit")
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def skills_audit_command(skills_dir: Path) -> None:
    """Show autonomous skill-layer audit."""
    assistant = _build_assistant(skills_dir)
    click.echo(assistant.handle_message("skills audit", TransportContext(source="cli")))


if __name__ == "__main__":
    main()
