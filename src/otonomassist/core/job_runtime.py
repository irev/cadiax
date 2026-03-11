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


def get_job_queue_summary() -> dict[str, Any]:
    """Return a compact summary of the runtime job queue."""
    state = load_job_queue_state()
    jobs = state.get("jobs", [])
    counts = {
        "queued": 0,
        "leased": 0,
        "done": 0,
        "failed": 0,
        "requeued": 0,
    }
    for job in jobs:
        status = str(job.get("status", "")).strip().lower()
        if status in counts:
            counts[status] += 1
    worker = state.get("worker", {}) if isinstance(state.get("worker", {}), dict) else {}
    return {
        "total_jobs": len(jobs),
        "queued_jobs": counts["queued"],
        "leased_jobs": counts["leased"],
        "done_jobs": counts["done"],
        "failed_jobs": counts["failed"],
        "requeued_jobs": counts["requeued"],
        "last_worker_run_at": worker.get("last_run_at", ""),
        "last_worker_status": worker.get("last_status", ""),
        "last_worker_processed": int(worker.get("last_processed", 0) or 0),
    }


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


def record_worker_run(processed: int, status: str) -> None:
    """Record the latest worker runtime activity in the queue state."""
    state = load_job_queue_state()
    worker = state.setdefault("worker", {})
    worker["last_run_at"] = datetime.now(timezone.utc).isoformat()
    worker["last_status"] = status
    worker["last_processed"] = int(processed)
    save_job_queue_state(state)


def process_job_queue(
    assistant: Any,
    *,
    max_jobs: int = 1,
    enqueue_first: bool = False,
    until_idle: bool = False,
) -> dict[str, Any]:
    """Process runtime jobs through the assistant until count or idle."""
    limit = max(1, int(max_jobs or 1))
    lines = [
        (
            f"Worker processing until idle (max_jobs={limit}):"
            if until_idle
            else f"Worker processing {limit} job(s):"
        )
    ]
    processed = 0
    idle = False

    while processed < limit:
        if enqueue_first:
            enqueue_ready_planner_task()
        job = lease_next_job()
        if not job:
            idle = True
            lines.append("- idle: tidak ada job queued")
            break

        result = assistant.handle_message("executor next")
        status = "done"
        if result.startswith("Task #") and "dijadwalkan ulang" in result:
            status = "requeued"
        elif result.startswith("Task #") and "gagal dieksekusi" in result:
            status = "failed"
        complete_job(int(job["id"]), status)
        processed += 1
        lines.append(f"- job {job['id']}: task #{job['task_id']} -> {status}")

        if not until_idle and processed >= limit:
            break

    if processed >= limit and until_idle:
        lines.append(f"- max_jobs_reached: {limit}")
    lines.append(f"- processed: {processed}")
    record_worker_run(processed, "idle" if idle else "active")
    return {
        "processed": processed,
        "idle": idle,
        "lines": lines,
        "output": "\n".join(lines),
    }


def render_job_queue() -> str:
    """Render the current job queue for operator inspection."""
    state = load_job_queue_state()
    jobs = state.get("jobs", [])
    summary = get_job_queue_summary()
    lines = [
        "Job Queue",
        "",
        "[Summary]",
        f"- total_jobs: {summary['total_jobs']}",
        f"- queued_jobs: {summary['queued_jobs']}",
        f"- leased_jobs: {summary['leased_jobs']}",
        f"- done_jobs: {summary['done_jobs']}",
        f"- failed_jobs: {summary['failed_jobs']}",
        f"- requeued_jobs: {summary['requeued_jobs']}",
        f"- last_worker_run_at: {summary['last_worker_run_at'] or '-'}",
        f"- last_worker_status: {summary['last_worker_status'] or '-'}",
        f"- last_worker_processed: {summary['last_worker_processed']}",
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
