"""Runtime job queue for autonomous execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from otonomassist.core.agent_context import (
    get_next_planner_task,
    load_job_queue_state,
    save_job_queue_state,
    update_planner_task_fields,
)


def enqueue_ready_planner_task() -> dict[str, Any] | None:
    """Enqueue the next ready planner task if it is not already queued."""
    task = get_next_planner_task()
    if not task:
        return None

    state = load_job_queue_state()
    jobs = state.setdefault("jobs", [])
    existing = next(
        (
            job for job in jobs
            if int(job.get("task_id", 0) or 0) == int(task.get("id", 0) or 0)
            and job.get("status") in {"queued", "leased"}
        ),
        None,
    )
    if existing:
        return existing

    job = {
        "id": len(jobs) + 1,
        "task_id": task.get("id"),
        "task_text": task.get("text", ""),
        "priority": int(task.get("priority", 0) or 0),
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "leased_at": "",
        "completed_at": "",
    }
    jobs.append(job)
    save_job_queue_state(state)
    update_planner_task_fields(int(task.get("id", 0) or 0), queued_job_id=job["id"])
    return job


def lease_next_job() -> dict[str, Any] | None:
    """Lease the highest-priority queued job."""
    state = load_job_queue_state()
    queued = [
        job for job in state.get("jobs", [])
        if job.get("status") == "queued"
    ]
    if not queued:
        return None

    job = sorted(
        queued,
        key=lambda item: (-int(item.get("priority", 0) or 0), int(item.get("id", 0) or 0)),
    )[0]
    job["status"] = "leased"
    job["leased_at"] = datetime.now(timezone.utc).isoformat()
    save_job_queue_state(state)
    return job


def complete_job(job_id: int, status: str) -> bool:
    """Mark one job as completed/failed."""
    state = load_job_queue_state()
    for job in state.get("jobs", []):
        if int(job.get("id", 0) or 0) == job_id:
            job["status"] = status
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            save_job_queue_state(state)
            return True
    return False


def render_job_queue() -> str:
    """Render the current job queue for operator inspection."""
    state = load_job_queue_state()
    jobs = state.get("jobs", [])
    lines = [
        "Job Queue",
        "",
        "[Summary]",
        f"- total_jobs: {len(jobs)}",
    ]
    if not jobs:
        lines.extend(["", "[Jobs]", "- belum ada job runtime"])
        return "\n".join(lines)

    lines.extend(["", "[Jobs]"])
    for job in jobs:
        lines.append(
            f"- #{job.get('id')} task#{job.get('task_id')} "
            f"[status={job.get('status')}, priority={job.get('priority')}] {job.get('task_text')}"
        )
    return "\n".join(lines)
