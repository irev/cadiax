"""Simple scheduler runtime built on top of the job worker."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from otonomassist.core.agent_context import load_scheduler_state, save_scheduler_state
from otonomassist.core.execution_history import append_execution_event, new_trace_id
from otonomassist.core.execution_metrics import record_execution_metric
from otonomassist.core.job_runtime import process_job_queue


def run_scheduler(
    assistant: Any,
    *,
    cycles: int = 1,
    interval_seconds: float = 0.0,
    max_jobs_per_cycle: int = 1,
    enqueue_first: bool = True,
    until_idle: bool = True,
    trace_id: str = "",
    source: str = "scheduler",
) -> dict[str, Any]:
    """Run scheduled worker cycles and persist scheduler state."""
    scheduler_trace_id = trace_id or new_trace_id()
    scheduler_started = time.perf_counter()
    total_processed = 0
    lines = [
        (
            f"Scheduler running {max(1, cycles)} cycle(s) "
            f"(interval={max(0.0, interval_seconds):.2f}s, max_jobs={max(1, max_jobs_per_cycle)}):"
        )
    ]
    final_status = "idle"
    append_execution_event(
        "scheduler_run_started",
        trace_id=scheduler_trace_id,
        status="started",
        source=source,
        command="scheduler",
        data={
            "cycles": max(1, cycles),
            "interval_seconds": max(0.0, interval_seconds),
            "max_jobs_per_cycle": max(1, max_jobs_per_cycle),
            "enqueue_first": enqueue_first,
            "until_idle": until_idle,
        },
    )
    from otonomassist.services.privacy.privacy_control_service import PrivacyControlService

    if PrivacyControlService().is_quiet_hours():
        save_scheduler_state(
            {
                "last_run_at": datetime.now(timezone.utc).isoformat(),
                "last_status": "quiet_hours",
                "last_cycles": 0,
                "last_processed": 0,
                "last_trace_id": scheduler_trace_id,
            }
        )
        append_execution_event(
            "scheduler_run_completed",
            trace_id=scheduler_trace_id,
            status="quiet_hours",
            source=source,
            command="scheduler",
            duration_ms=int((time.perf_counter() - scheduler_started) * 1000),
            data={"reason": "quiet_hours_active", "cycles": 0, "processed": 0},
        )
        record_execution_metric(
            "scheduler_run_completed",
            status="quiet_hours",
            source=source,
            duration_ms=int((time.perf_counter() - scheduler_started) * 1000),
        )
        lines.append("- skipped: quiet hours active")
        return {
            "cycles": 0,
            "processed": 0,
            "status": "quiet_hours",
            "trace_id": scheduler_trace_id,
            "output": "\n".join(lines),
        }

    for cycle_index in range(max(1, cycles)):
        cycle_trace_id = new_trace_id()
        cycle_started = time.perf_counter()
        append_execution_event(
            "scheduler_cycle_started",
            trace_id=cycle_trace_id,
            status="started",
            source=source,
            command="scheduler cycle",
            data={
                "parent_trace_id": scheduler_trace_id,
                "cycle_index": cycle_index + 1,
                "max_jobs": max(1, max_jobs_per_cycle),
            },
        )
        result = process_job_queue(
            assistant,
            max_jobs=max_jobs_per_cycle,
            enqueue_first=enqueue_first,
            until_idle=until_idle,
            trace_id=cycle_trace_id,
            source=source,
            cycle_label=f"scheduler-cycle-{cycle_index + 1}",
        )
        lines.append(f"[cycle {cycle_index + 1}]")
        lines.extend(result["lines"][1:])
        total_processed += int(result["processed"])
        final_status = "idle" if result["idle"] else "active"
        cycle_duration_ms = int((time.perf_counter() - cycle_started) * 1000)
        append_execution_event(
            "scheduler_cycle_completed",
            trace_id=cycle_trace_id,
            status=final_status,
            source=source,
            command="scheduler cycle",
            duration_ms=cycle_duration_ms,
            data={
                "parent_trace_id": scheduler_trace_id,
                "cycle_index": cycle_index + 1,
                "processed": int(result["processed"]),
                "idle": bool(result["idle"]),
            },
        )
        record_execution_metric(
            "scheduler_cycle_completed",
            status=final_status,
            source=source,
            duration_ms=cycle_duration_ms,
        )
        if cycle_index + 1 < max(1, cycles) and interval_seconds > 0:
            time.sleep(max(0.0, interval_seconds))

    save_scheduler_state(
        {
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "last_status": final_status,
            "last_cycles": max(1, cycles),
            "last_processed": total_processed,
            "last_trace_id": scheduler_trace_id,
        }
    )
    total_duration_ms = int((time.perf_counter() - scheduler_started) * 1000)
    append_execution_event(
        "scheduler_run_completed",
        trace_id=scheduler_trace_id,
        status=final_status,
        source=source,
        command="scheduler",
        duration_ms=total_duration_ms,
        data={
            "cycles": max(1, cycles),
            "processed": total_processed,
            "interval_seconds": max(0.0, interval_seconds),
        },
    )
    record_execution_metric(
        "scheduler_run_completed",
        status=final_status,
        source=source,
        duration_ms=total_duration_ms,
    )
    lines.append(f"- total_processed: {total_processed}")
    return {
        "cycles": max(1, cycles),
        "processed": total_processed,
        "status": final_status,
        "trace_id": scheduler_trace_id,
        "output": "\n".join(lines),
    }


def get_scheduler_summary() -> dict[str, Any]:
    """Return scheduler state for operator and admin reporting."""
    state = load_scheduler_state()
    return {
        "last_run_at": state.get("last_run_at", ""),
        "last_status": state.get("last_status", ""),
        "last_cycles": int(state.get("last_cycles", 0) or 0),
        "last_processed": int(state.get("last_processed", 0) or 0),
        "last_trace_id": state.get("last_trace_id", ""),
    }
