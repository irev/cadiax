"""Simple scheduler runtime built on top of the job worker."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from otonomassist.core.agent_context import load_scheduler_state, save_scheduler_state
from otonomassist.core.job_runtime import process_job_queue


def run_scheduler(
    assistant: Any,
    *,
    cycles: int = 1,
    interval_seconds: float = 0.0,
    max_jobs_per_cycle: int = 1,
    enqueue_first: bool = True,
    until_idle: bool = True,
) -> dict[str, Any]:
    """Run scheduled worker cycles and persist scheduler state."""
    total_processed = 0
    lines = [
        (
            f"Scheduler running {max(1, cycles)} cycle(s) "
            f"(interval={max(0.0, interval_seconds):.2f}s, max_jobs={max(1, max_jobs_per_cycle)}):"
        )
    ]
    final_status = "idle"

    for cycle_index in range(max(1, cycles)):
        result = process_job_queue(
            assistant,
            max_jobs=max_jobs_per_cycle,
            enqueue_first=enqueue_first,
            until_idle=until_idle,
        )
        lines.append(f"[cycle {cycle_index + 1}]")
        lines.extend(result["lines"][1:])
        total_processed += int(result["processed"])
        final_status = "idle" if result["idle"] else "active"
        if cycle_index + 1 < max(1, cycles) and interval_seconds > 0:
            time.sleep(max(0.0, interval_seconds))

    save_scheduler_state(
        {
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "last_status": final_status,
            "last_cycles": max(1, cycles),
            "last_processed": total_processed,
        }
    )
    lines.append(f"- total_processed: {total_processed}")
    return {
        "cycles": max(1, cycles),
        "processed": total_processed,
        "status": final_status,
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
    }
