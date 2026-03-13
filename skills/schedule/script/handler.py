"""Schedule skill handler."""

from __future__ import annotations

from pathlib import Path

from cadiax.core.assistant import Assistant
from cadiax.core.job_runtime import enqueue_ready_planner_task
from cadiax.core.result_builder import build_result
from cadiax.core.scheduler_runtime import get_scheduler_summary, run_scheduler
from cadiax.services.privacy.privacy_control_service import PrivacyControlService


def handle(args: str) -> dict[str, object] | str:
    """Inspect or run the scheduler capability surface."""
    args = args.strip()
    if not args:
        args = "show"

    command, options = _parse_args(args)
    if command == "show":
        return _show_scheduler()
    if command == "run":
        return _run_scheduler(options)
    if command == "enqueue":
        return _enqueue_ready_task()
    return _usage()


def _usage() -> str:
    return (
        "Usage: schedule <show|run|enqueue> "
        "[cycles=<n>] [steps=<n>] [interval=<seconds>] "
        "[enqueue_first=true|false] [until_idle=true|false]"
    )


def _parse_args(args: str) -> tuple[str, dict[str, object]]:
    tokens = [token for token in args.split() if token.strip()]
    command = "show"
    if tokens and "=" not in tokens[0]:
        command = tokens[0].strip().lower()
        tokens = tokens[1:]
    options: dict[str, object] = {}
    for token in tokens:
        key, separator, value = token.partition("=")
        if not separator:
            continue
        key = key.strip().lower()
        value = value.strip()
        if key in {"cycles", "steps"}:
            try:
                options[key] = max(1, int(value))
            except ValueError:
                continue
        elif key == "interval":
            try:
                options[key] = max(0.0, float(value))
            except ValueError:
                continue
        elif key in {"enqueue_first", "until_idle"}:
            options[key] = value.strip().lower() not in {"false", "0", "no"}
    return command, options


def _show_scheduler() -> dict[str, object]:
    summary = get_scheduler_summary()
    quiet_hours = PrivacyControlService().get_diagnostics()
    text = (
        f"Schedule show: last_status={summary['last_status'] or '-'}, "
        f"last_cycles={summary['last_cycles']}, "
        f"last_processed={summary['last_processed']}, "
        f"quiet_hours_active={'yes' if quiet_hours['quiet_hours_active'] else 'no'}."
    )
    return build_result(
        "schedule_show",
        {
            "summary": text,
            "scheduler": summary,
            "quiet_hours": quiet_hours["quiet_hours"],
            "quiet_hours_active": quiet_hours["quiet_hours_active"],
        },
        source_skill="schedule",
        default_view="summary",
    )


def _run_scheduler(options: dict[str, object]) -> dict[str, object]:
    assistant = Assistant(skills_dir=Path("skills"))
    assistant.initialize()
    result = run_scheduler(
        assistant,
        cycles=int(options.get("cycles", 1) or 1),
        max_jobs_per_cycle=int(options.get("steps", 1) or 1),
        interval_seconds=float(options.get("interval", 0.0) or 0.0),
        enqueue_first=bool(options.get("enqueue_first", True)),
        until_idle=bool(options.get("until_idle", True)),
        source="schedule-skill",
    )
    return build_result(
        "schedule_run",
        {
            "summary": (
                f"Schedule run: status={result['status']}, "
                f"cycles={result['cycles']}, processed={result['processed']}."
            ),
            "run": result,
        },
        source_skill="schedule",
        default_view="summary",
        status="ok" if result["status"] != "quiet_hours" else "deferred",
    )


def _enqueue_ready_task() -> dict[str, object] | str:
    job = enqueue_ready_planner_task(source="schedule-skill")
    if not job:
        return "Schedule enqueue: tidak ada task ready untuk dimasukkan ke job queue."
    return build_result(
        "schedule_enqueue",
        {
            "summary": (
                f"Schedule enqueue: job_id={job['id']}, "
                f"task_id={job['task_id']}, priority={job['priority']}."
            ),
            "job": job,
        },
        source_skill="schedule",
        default_view="summary",
    )
