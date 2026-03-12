"""CLI interface for OtonomAssist."""

from __future__ import annotations

from pathlib import Path
import json
import time

import click

from otonomassist.core import (
    Assistant,
    TransportContext,
    get_config_status_data,
    get_config_status_report,
    render_event_bus,
    render_execution_history,
)
from otonomassist.core.admin_api import run_admin_api
from otonomassist.core.execution_metrics import get_execution_metrics_snapshot, render_execution_metrics
from otonomassist.core.external_assets import (
    render_external_asset_audit,
    set_external_asset_approval,
    sync_external_skill_inventory,
)
from otonomassist.core.external_installer import install_external_skill, render_external_install_result
from otonomassist.core.workspace_bootstrap import (
    ensure_workspace_skeleton,
    get_workspace_bootstrap_status,
    render_workspace_bootstrap_status,
)
from otonomassist.core.job_runtime import enqueue_ready_planner_task, process_job_queue, render_job_queue
from otonomassist.core.scheduler_runtime import run_scheduler
from otonomassist.core.setup_wizard import run_setup_wizard, should_recommend_setup
from otonomassist.platform import (
    get_service_wrapper_output_dir,
    render_service_runtime_status,
    render_service_wrapper_artifacts,
    run_named_service_target,
    write_service_wrapper_artifacts,
)
from otonomassist.interfaces.email import EmailInterfaceService
from otonomassist.interfaces.whatsapp import WhatsAppInterfaceService
from otonomassist.services.personality.heartbeat_service import HeartbeatService
from otonomassist.services.personality.proactive_assistance_service import ProactiveAssistanceService
from otonomassist.services.interactions import ConversationService, NotificationDispatcher, run_conversation_api
from otonomassist.telegram_cli import run_telegram_transport


def _build_assistant(skills_dir: Path) -> Assistant:
    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()
    return assistant


def _build_conversation_service(skills_dir: Path) -> ConversationService:
    return ConversationService(_build_assistant(skills_dir))


def _run_interactive(service: ConversationService) -> None:
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

            result = service.handle_message(user_input, TransportContext(source="cli"))
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

    service = _build_conversation_service(skills_dir)
    if interactive or not ctx.args:
        _run_interactive(service)
        return

    command = " ".join(ctx.args).strip()
    result = service.handle_message(command, TransportContext(source="cli"))
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


@main.command("events")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable event bus snapshot")
def events_command(as_json: bool) -> None:
    """Show recent internal event bus activity."""
    from otonomassist.core.event_bus import get_event_bus_snapshot

    if as_json:
        click.echo(json.dumps(get_event_bus_snapshot(), ensure_ascii=False, indent=2))
        return
    click.echo(render_event_bus())


@main.command("metrics")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON metrics")
def metrics_command(as_json: bool) -> None:
    """Show aggregated execution metrics."""
    if as_json:
        click.echo(json.dumps(get_execution_metrics_snapshot(), ensure_ascii=False, indent=2))
        return
    click.echo(render_execution_metrics())


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
@click.option("--until-idle", is_flag=True, help="Proses queue sampai tidak ada job queued")
@click.option("--enqueue-first", is_flag=True, help="Enqueue ready planner task sebelum memproses")
@click.option("--interval", default=0.0, type=float, show_default=True, help="Jeda antar cycle worker (detik)")
@click.option("--max-cycles", default=1, type=int, show_default=True, help="Jumlah cycle worker terjadwal")
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def worker_command(
    steps: int,
    until_idle: bool,
    enqueue_first: bool,
    interval: float,
    max_cycles: int,
    skills_dir: Path,
) -> None:
    """Process runtime jobs from the queue."""
    assistant = _build_assistant(skills_dir)
    cycles = max(1, max_cycles)
    lines: list[str] = [
        (
            f"Worker scheduled for {cycles} cycle(s) until idle "
            f"(max_jobs={max(1, steps)}, interval={max(0.0, interval):.2f}s):"
            if until_idle or cycles > 1
            else f"Worker processing up to {max(1, steps)} job(s):"
        )
    ]
    total_processed = 0
    for cycle_index in range(cycles):
        result = process_job_queue(
            assistant,
            max_jobs=max(1, steps),
            enqueue_first=enqueue_first,
            until_idle=until_idle,
        )
        lines.append(f"[cycle {cycle_index + 1}]")
        lines.extend(result["lines"][1:])
        total_processed += int(result["processed"])
        if result["idle"] and cycle_index + 1 < cycles and interval <= 0:
            break
        if cycle_index + 1 < cycles and interval > 0:
            time.sleep(max(0.0, interval))
    lines.append(f"- total_processed: {total_processed}")
    click.echo("\n".join(lines))


@main.group("config")
def config_group() -> None:
    """Configuration commands."""


@main.group("bootstrap")
def bootstrap_group() -> None:
    """Workspace bootstrap commands."""


@bootstrap_group.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON bootstrap status")
def bootstrap_status_command(as_json: bool) -> None:
    """Show workspace bootstrap template status."""
    payload = get_workspace_bootstrap_status()
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(render_workspace_bootstrap_status())


@bootstrap_group.command("foundation")
@click.option("--force", is_flag=True, help="Overwrite existing foundation skeleton files in workspace")
def bootstrap_foundation_command(force: bool) -> None:
    """Seed foundation templates into the workspace root."""
    result = ensure_workspace_skeleton(force=force, only_if_workspace_empty=not force)
    click.echo(
        f"Foundation bootstrap written={result['written_count']} existing={result['existing_count']} "
        f"skipped={result['skipped'] or '-'}"
    )


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
    _run_interactive(_build_conversation_service(skills_dir))


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
    service = _build_conversation_service(skills_dir)
    result = service.handle_message(message, TransportContext(source="cli"))
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


@main.command("api")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind address for the admin API")
@click.option("--port", default=8787, type=int, show_default=True, help="Bind port for the admin API")
def api_command(host: str, port: int) -> None:
    """Run the local read-only admin API."""
    click.echo(f"Admin API listening on http://{host}:{port}")
    run_admin_api(host=host, port=port)


@main.command("conversation-api")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind address for the conversation API")
@click.option("--port", default=8788, type=int, show_default=True, help="Bind port for the conversation API")
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def conversation_api_command(host: str, port: int, skills_dir: Path) -> None:
    """Run the local conversation API."""
    click.echo(f"Conversation API listening on http://{host}:{port}")
    run_conversation_api(_build_conversation_service(skills_dir), host=host, port=port)


@main.group("notify")
def notify_group() -> None:
    """Notification dispatch commands."""


@notify_group.command("send")
@click.argument("message", required=True)
@click.option("--channel", default="internal", show_default=True, help="Notification channel label")
@click.option("--title", default="Notification", show_default=True, help="Notification title")
@click.option("--target", default="", help="Optional target descriptor")
@click.option(
    "--delivery",
    "deliveries",
    multiple=True,
    help="Multi-channel delivery in format channel:target, repeatable",
)
def notify_send_command(
    message: str,
    channel: str,
    title: str,
    target: str,
    deliveries: tuple[str, ...],
) -> None:
    """Dispatch one durable notification entry."""
    dispatcher = NotificationDispatcher()
    if deliveries:
        normalized: list[dict[str, str]] = []
        for raw in deliveries:
            item = raw.strip()
            if not item:
                continue
            channel_name, _, delivery_target = item.partition(":")
            normalized.append(
                {
                    "channel": channel_name.strip() or "internal",
                    "target": delivery_target.strip(),
                }
            )
        batch = dispatcher.dispatch_many(
            title=title,
            message=message,
            deliveries=normalized,
        )
        click.echo(
            f"Notification batch {batch['batch_id']} dispatched "
            f"to {batch['delivery_count']} delivery target(s)"
        )
        return
    payload = dispatcher.dispatch(
        channel=channel,
        title=title,
        message=message,
        target=target,
    )
    click.echo(
        f"Notification #{payload['id']} dispatched via {payload['channel']} "
        f"to {payload['target'] or '-'}"
    )


@main.group("email")
def email_group() -> None:
    """Email interface commands."""


@email_group.command("send")
@click.argument("message", required=True)
@click.option("--to", "to_address", required=True, help="Destination email address")
@click.option("--subject", default="Notification", show_default=True, help="Email subject")
@click.option("--from", "from_address", default="", help="Optional sender address label")
def email_send_command(message: str, to_address: str, subject: str, from_address: str) -> None:
    """Dispatch one outbound email-shaped notification."""
    payload = EmailInterfaceService().send(
        to_address=to_address,
        from_address=from_address,
        subject=subject,
        body=message,
    )
    click.echo(
        f"Email #{payload['id']} queued to {payload['to_address']} "
        f"with subject {payload['subject'] or '-'}"
    )


@main.group("whatsapp")
def whatsapp_group() -> None:
    """WhatsApp interface commands."""


@whatsapp_group.command("send")
@click.argument("message", required=True)
@click.option("--to", "phone_number", required=True, help="Destination WhatsApp number")
@click.option("--name", "display_name", default="", help="Optional display name")
def whatsapp_send_command(message: str, phone_number: str, display_name: str) -> None:
    """Dispatch one outbound WhatsApp-shaped notification."""
    payload = WhatsAppInterfaceService().send(
        phone_number=phone_number,
        body=message,
        display_name=display_name,
    )
    click.echo(
        f"WhatsApp #{payload['id']} queued to {payload['phone_number']} "
        f"for {payload['display_name'] or '-'}"
    )


@main.group("privacy")
def privacy_group() -> None:
    """Privacy controls and user data commands."""


@privacy_group.command("show")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON privacy controls")
def privacy_show_command(as_json: bool) -> None:
    """Show privacy governance controls."""
    from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

    payload = PrivacyControlService().get_diagnostics()
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(
        "\n".join(
            [
                "Privacy Controls",
                "",
                f"- quiet_hours_enabled: {'yes' if payload['quiet_hours'].get('enabled') else 'no'}",
                f"- quiet_hours_start: {payload['quiet_hours'].get('start', '-')}",
                f"- quiet_hours_end: {payload['quiet_hours'].get('end', '-')}",
                f"- quiet_hours_active: {'yes' if payload['quiet_hours_active'] else 'no'}",
                f"- consent_required_for_proactive: {'yes' if payload['consent_required_for_proactive'] else 'no'}",
                f"- proactive_assistance_enabled: {'yes' if payload['proactive_assistance_enabled'] else 'no'}",
                f"- memory_retention_days: {payload['memory_retention_days']}",
                f"- memory_entry_count: {payload['memory_entry_count']}",
            ]
        )
    )


@privacy_group.command("quiet-hours")
@click.option("--start", required=True, help="Start time in HH:MM")
@click.option("--end", required=True, help="End time in HH:MM")
@click.option("--disable", is_flag=True, help="Disable quiet hours after updating the configured window")
def privacy_quiet_hours_command(start: str, end: str, disable: bool) -> None:
    """Configure quiet-hours controls."""
    from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

    state = PrivacyControlService().set_quiet_hours(start=start, end=end, enabled=not disable)
    click.echo(
        f"Quiet hours updated: enabled={'yes' if state['quiet_hours']['enabled'] else 'no'} "
        f"{state['quiet_hours']['start']}-{state['quiet_hours']['end']}"
    )


@privacy_group.command("scope")
@click.option("--scope", "scope_name", required=True, help="Agent/domain scope label")
@click.option("--proactive-enabled/--proactive-disabled", default=None, help="Enable or disable proactive delivery for the scope")
@click.option("--consent-required/--consent-optional", default=None, help="Require consent for proactive delivery in the scope")
@click.option("--allow-role", "allowed_roles", multiple=True, help="Allowed role for the scope, repeatable")
def privacy_scope_command(
    scope_name: str,
    proactive_enabled: bool | None,
    consent_required: bool | None,
    allowed_roles: tuple[str, ...],
) -> None:
    """Configure scope-specific privacy controls."""
    from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

    payload = PrivacyControlService().set_scope_controls(
        scope=scope_name,
        proactive_enabled=proactive_enabled,
        consent_required=consent_required,
        allowed_roles=list(allowed_roles) if allowed_roles else None,
    )
    click.echo(
        f"Scope `{payload['scope']}` updated: proactive="
        f"{'yes' if payload['proactive_assistance_enabled'] else 'no'} consent="
        f"{'yes' if payload['consent_required_for_proactive'] else 'no'} roles="
        f"{', '.join(payload['allowed_roles']) or '-'}"
    )


@privacy_group.command("retention")
@click.option("--days", required=True, type=int, help="Retention period in days")
def privacy_retention_command(days: int) -> None:
    """Configure personal-data retention period."""
    from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

    state = PrivacyControlService().set_proactive_controls(memory_retention_days=days)
    click.echo(f"Memory retention updated to {state['memory_retention_days']} day(s)")


@privacy_group.command("export")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path(".otonomassist") / "privacy_export.json",
    show_default=True,
    help="Destination JSON file",
)
def privacy_export_command(output: Path) -> None:
    """Export privacy-relevant local user data."""
    from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

    written = PrivacyControlService().export_user_data_to_path(output)
    click.echo(f"Privacy export written to {written}")


@privacy_group.command("delete-memory")
def privacy_delete_memory_command() -> None:
    """Delete stored memory journal and summaries."""
    from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

    result = PrivacyControlService().delete_memory_data()
    click.echo(
        f"Deleted {result['deleted_memory_entries']} memory entry(ies) and "
        f"{result['deleted_memory_summaries']} memory summary chunk(s)"
    )


@privacy_group.command("prune")
def privacy_prune_command() -> None:
    """Prune personal data older than the configured retention period."""
    from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

    result = PrivacyControlService().prune_expired_personal_data()
    total = sum(int(value or 0) for value in result.values())
    click.echo(f"Pruned {total} expired personal-data record(s)")


@privacy_group.command("delete-personal-data")
def privacy_delete_personal_data_command() -> None:
    """Delete privacy-relevant personal data stores."""
    from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

    result = PrivacyControlService().delete_personal_data()
    total = sum(int(value or 0) for value in result.values())
    click.echo(f"Deleted {total} personal-data record(s) across privacy stores")


@main.group("proactive")
def proactive_group() -> None:
    """Contextual proactive assistance commands."""


@proactive_group.command("show")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON proactive insights")
def proactive_show_command(as_json: bool) -> None:
    """Show current proactive assistance recommendations."""
    payload = ProactiveAssistanceService().load_or_refresh()
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(ProactiveAssistanceService().render_report())


@proactive_group.command("notify")
@click.option("--channel", default="internal", show_default=True, help="Notification channel label")
@click.option("--target", default="", help="Delivery target")
@click.option("--consented/--no-consented", default=False, show_default=True, help="Mark that the user consented to proactive delivery")
@click.option("--scope", "scope_name", default="default", show_default=True, help="Agent/domain scope label")
@click.option("--role", "roles", multiple=True, help="Role surface for scope checks, repeatable")
def proactive_notify_command(channel: str, target: str, consented: bool, scope_name: str, roles: tuple[str, ...]) -> None:
    """Dispatch the top proactive insight as a proactive notification."""
    service = ProactiveAssistanceService()
    insights = service.list_insights(limit=1)
    if not insights:
        click.echo("Belum ada proactive insight untuk dikirim.")
        return
    top = insights[0]
    payload = NotificationDispatcher().dispatch(
        channel=channel,
        title="Proactive Suggestion",
        message=top["summary"],
        target=target,
        metadata={
            "proactive": True,
            "user_consented": consented,
            "reason": top.get("reason", ""),
            "agent_scope": scope_name,
            "roles": list(roles),
        },
    )
    click.echo(
        f"Proactive notification #{payload['id']} status={payload['status']} "
        f"via {payload['channel']} to {payload['target'] or '-'}"
    )


@main.group("heartbeat")
def heartbeat_group() -> None:
    """Heartbeat rhythm commands."""


@heartbeat_group.command("show")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON heartbeat state")
def heartbeat_show_command(as_json: bool) -> None:
    """Show durable heartbeat state."""
    payload = HeartbeatService().load_or_pulse(trigger="cli-show")
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(HeartbeatService().render_report())


@heartbeat_group.command("pulse")
@click.option("--trigger", default="manual", show_default=True, help="Heartbeat trigger label")
def heartbeat_pulse_command(trigger: str) -> None:
    """Force one heartbeat pulse."""
    payload = HeartbeatService().pulse(trigger=trigger)
    click.echo(
        f"Heartbeat pulse #{payload['pulse_count']} mode={payload['last_mode'] or '-'} "
        f"summary={payload['last_summary'] or '-'}"
    )


@main.group("service")
def service_group() -> None:
    """Foreground service runtime and wrapper commands."""


@service_group.command("status")
def service_status_command() -> None:
    """Show service runtime readiness and supported targets."""
    click.echo(render_service_runtime_status())


@service_group.command("show")
@click.argument(
    "target",
    type=click.Choice(["worker", "scheduler", "admin-api", "conversation-api"], case_sensitive=False),
)
@click.option(
    "--runtime",
    type=click.Choice(["auto", "windows", "posix", "all"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Which wrapper runtime to render",
)
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def service_show_command(target: str, runtime: str, skills_dir: Path) -> None:
    """Render generated wrapper artifacts for one service target."""
    click.echo(render_service_wrapper_artifacts(target, runtime=runtime, skills_dir=skills_dir))


@service_group.command("write")
@click.argument(
    "target",
    required=False,
    type=click.Choice(["worker", "scheduler", "admin-api", "conversation-api"], case_sensitive=False),
)
@click.option(
    "--runtime",
    type=click.Choice(["auto", "windows", "posix", "all"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Which wrapper runtime to generate",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Directory where wrapper files will be written",
)
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def service_write_command(
    target: str | None,
    runtime: str,
    output_dir: Path | None,
    skills_dir: Path,
) -> None:
    """Write generated wrapper artifacts to disk."""
    written = write_service_wrapper_artifacts(
        target=target,
        output_dir=output_dir or get_service_wrapper_output_dir(),
        runtime=runtime,
        skills_dir=skills_dir,
    )
    click.echo(f"Wrote {len(written)} service wrapper file(s):")
    for path in written:
        click.echo(str(path))


@service_group.command("run")
@click.argument(
    "target",
    type=click.Choice(["worker", "scheduler", "admin-api", "conversation-api"], case_sensitive=False),
)
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind address for API targets")
@click.option("--port", default=None, type=int, help="Bind port for API targets")
@click.option("--interval", default=None, type=float, help="Loop interval in seconds for worker/scheduler targets")
@click.option("--steps", default=None, type=int, help="Maximum jobs per loop for worker/scheduler targets")
@click.option("--enqueue-first/--no-enqueue-first", default=True, show_default=True, help="Enqueue ready planner task before processing")
@click.option("--until-idle/--single-pass", default=True, show_default=True, help="Run worker loop until queue becomes idle")
@click.option("--max-loops", default=0, type=int, show_default=True, help="Number of service loops; 0 means run until stopped")
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def service_run_command(
    target: str,
    host: str,
    port: int | None,
    interval: float | None,
    steps: int | None,
    enqueue_first: bool,
    until_idle: bool,
    max_loops: int,
    skills_dir: Path,
) -> None:
    """Run one foreground service target suitable for supervision."""
    result = run_named_service_target(
        target,
        skills_dir=skills_dir,
        host=host,
        port=port,
        interval_seconds=interval,
        steps=steps,
        enqueue_first=enqueue_first,
        until_idle=until_idle,
        max_loops=max(0, max_loops),
    )
    if result is not None:
        click.echo(result["output"])


@main.command("scheduler")
@click.option("--cycles", default=1, type=int, show_default=True, help="Jumlah cycle scheduler")
@click.option("--interval", default=0.0, type=float, show_default=True, help="Jeda antar cycle (detik)")
@click.option("--steps", default=5, type=int, show_default=True, help="Maksimum job per cycle")
@click.option("--enqueue-first/--no-enqueue-first", default=True, show_default=True, help="Enqueue task ready di awal cycle")
@click.option("--until-idle/--single-pass", default=True, show_default=True, help="Jalankan worker sampai idle per cycle")
@click.option(
    "--skills-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="skills",
    help="Directory containing skill markdown files",
)
def scheduler_command(
    cycles: int,
    interval: float,
    steps: int,
    enqueue_first: bool,
    until_idle: bool,
    skills_dir: Path,
) -> None:
    """Run scheduled autonomous worker cycles."""
    assistant = _build_assistant(skills_dir)
    result = run_scheduler(
        assistant,
        cycles=max(1, cycles),
        interval_seconds=max(0.0, interval),
        max_jobs_per_cycle=max(1, steps),
        enqueue_first=enqueue_first,
        until_idle=until_idle,
    )
    click.echo(result["output"])


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


@external_group.command("approve")
@click.argument("name", required=True)
def external_approve_command(name: str) -> None:
    """Approve one external skill for loading."""    
    try:
        asset = set_external_asset_approval(name, "approved", actor="cli")
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"External asset `{asset['name']}` diset ke approved.")


@external_group.command("reject")
@click.argument("name", required=True)
def external_reject_command(name: str) -> None:
    """Reject one external skill from loading."""    
    try:
        asset = set_external_asset_approval(name, "rejected", actor="cli")
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"External asset `{asset['name']}` diset ke rejected.")


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
