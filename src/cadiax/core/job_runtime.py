"""Runtime job queue for autonomous execution."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from cadiax.core.agent_context import (
    get_next_planner_task,
    load_job_queue_state,
    save_job_queue_state,
    update_planner_task_fields,
)
from cadiax.core.execution_history import append_execution_event, new_trace_id
from cadiax.core.execution_metrics import record_execution_metric, record_queue_depth_metric
from cadiax.core.transport import TransportContext


def enqueue_ready_planner_task(
    *,
    trace_id: str = "",
    source: str = "runtime",
) -> dict[str, Any] | None:
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
    job_trace_id = new_trace_id()

    job = {
        "id": len(jobs) + 1,
        "task_id": task.get("id"),
        "task_text": task.get("text", ""),
        "agent_scope": str(task.get("agent_scope") or "default"),
        "session_mode": str(task.get("session_mode") or "main"),
        "priority": int(task.get("priority", 0) or 0),
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "leased_at": "",
        "completed_at": "",
        "trace_id": job_trace_id,
        "parent_trace_id": trace_id,
        "last_trace_id": job_trace_id,
    }
    jobs.append(job)
    save_job_queue_state(state)
    update_planner_task_fields(
        int(task.get("id", 0) or 0),
        queued_job_id=job["id"],
        last_job_trace_id=job_trace_id,
        last_job_parent_trace_id=trace_id,
        last_job_status="queued",
        last_queued_at=job["created_at"],
    )
    append_execution_event(
        "job_enqueued",
        trace_id=job_trace_id,
        status="queued",
        source=source,
        command=task.get("text", ""),
        data={
            "parent_trace_id": trace_id,
            "job_id": job["id"],
            "task_id": job["task_id"],
            "task_text": job["task_text"],
            "priority": job["priority"],
        },
    )
    record_execution_metric("job_enqueued", status="queued", source=source)
    _record_runtime_queue_depth(state)
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
        "last_worker_trace_id": worker.get("last_trace_id", ""),
    }


def lease_next_job(
    *,
    trace_id: str = "",
    source: str = "worker",
) -> dict[str, Any] | None:
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
    job_trace_id = str(job.get("trace_id") or new_trace_id())
    job["status"] = "leased"
    job["leased_at"] = datetime.now(timezone.utc).isoformat()
    job["trace_id"] = job_trace_id
    job["last_trace_id"] = job_trace_id
    job["last_cycle_trace_id"] = trace_id
    save_job_queue_state(state)
    append_execution_event(
        "job_leased",
        trace_id=job_trace_id,
        status="leased",
        source=source,
        command=str(job.get("task_text", "")),
        data={
            "parent_trace_id": str(job.get("parent_trace_id", "")),
            "cycle_trace_id": trace_id,
            "job_id": int(job.get("id", 0) or 0),
            "task_id": int(job.get("task_id", 0) or 0),
        },
    )
    record_execution_metric("job_leased", status="leased", source=source)
    _record_runtime_queue_depth(state)
    return job


def complete_job(
    job_id: int,
    status: str,
    *,
    trace_id: str = "",
    source: str = "worker",
    parent_trace_id: str = "",
    result_preview: str = "",
    duration_ms: int | None = None,
) -> bool:
    """Mark one job as completed/failed."""
    state = load_job_queue_state()
    for job in state.get("jobs", []):
        if int(job.get("id", 0) or 0) == job_id:
            job_trace_id = trace_id or str(job.get("trace_id") or new_trace_id())
            job["status"] = status
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            job["trace_id"] = job_trace_id
            job["last_trace_id"] = job_trace_id
            job["last_result_status"] = status
            save_job_queue_state(state)
            update_planner_task_fields(
                int(job.get("task_id", 0) or 0),
                last_job_status=status,
                last_job_trace_id=job_trace_id,
                last_job_parent_trace_id=parent_trace_id,
                last_job_completed_at=job["completed_at"],
                last_result_status=status,
                last_result_preview=result_preview[:240],
                last_executed_at=job["completed_at"],
            )
            append_execution_event(
                "job_completed",
                trace_id=job_trace_id,
                status=status,
                source=source,
                command=str(job.get("task_text", "")),
                duration_ms=duration_ms,
                data={
                    "parent_trace_id": parent_trace_id or str(job.get("parent_trace_id", "")),
                    "job_id": int(job.get("id", 0) or 0),
                    "task_id": int(job.get("task_id", 0) or 0),
                    "task_text": str(job.get("task_text", "")),
                    "result_preview": result_preview[:240],
                },
            )
            record_execution_metric(
                "job_completed",
                status=status,
                source=source,
                duration_ms=duration_ms,
            )
            _record_runtime_queue_depth(state)
            return True
    return False


def record_worker_run(processed: int, status: str, *, trace_id: str = "") -> None:
    """Record the latest worker runtime activity in the queue state."""
    state = load_job_queue_state()
    worker = state.setdefault("worker", {})
    worker["last_run_at"] = datetime.now(timezone.utc).isoformat()
    worker["last_status"] = status
    worker["last_processed"] = int(processed)
    if trace_id:
        worker["last_trace_id"] = trace_id
    save_job_queue_state(state)
    _record_runtime_queue_depth(state)


def process_job_queue(
    assistant: Any,
    *,
    max_jobs: int = 1,
    enqueue_first: bool = False,
    until_idle: bool = False,
    trace_id: str = "",
    source: str = "worker",
    cycle_label: str = "worker-cycle",
) -> dict[str, Any]:
    """Process runtime jobs through the assistant until count or idle."""
    limit = max(1, int(max_jobs or 1))
    cycle_trace_id = trace_id or new_trace_id()
    cycle_started = time.perf_counter()
    lines = [
        (
            f"Worker processing until idle (max_jobs={limit}):"
            if until_idle
            else f"Worker processing {limit} job(s):"
        )
    ]
    processed = 0
    idle = False
    append_execution_event(
        "worker_cycle_started",
        trace_id=cycle_trace_id,
        status="started",
        source=source,
        command="executor next",
        data={
            "cycle_label": cycle_label,
            "max_jobs": limit,
            "enqueue_first": enqueue_first,
            "until_idle": until_idle,
        },
    )

    while processed < limit:
        if enqueue_first:
            enqueue_ready_planner_task(trace_id=cycle_trace_id, source=source)
        job = lease_next_job(trace_id=cycle_trace_id, source=source)
        if not job:
            idle = True
            lines.append("- idle: tidak ada job queued")
            break

        job_trace_id = str(job.get("trace_id") or new_trace_id())
        task_started = time.perf_counter()
        append_execution_event(
            "task_execution_started",
            trace_id=job_trace_id,
            status="started",
            source=source,
            command="executor next",
            data={
                "parent_trace_id": cycle_trace_id,
                "job_id": int(job.get("id", 0) or 0),
                "task_id": int(job.get("task_id", 0) or 0),
                "task_text": str(job.get("task_text", "")),
            },
        )
        result = assistant.handle_message(
            "executor next",
            TransportContext(source=source, trace_id=job_trace_id),
        )
        status = "done"
        if result.startswith("Task #") and "dijadwalkan ulang" in result:
            status = "requeued"
        elif result.startswith("Task #") and "gagal dieksekusi" in result:
            status = "failed"
        task_duration_ms = int((time.perf_counter() - task_started) * 1000)
        append_execution_event(
            "task_execution_completed",
            trace_id=job_trace_id,
            status=status,
            source=source,
            command="executor next",
            duration_ms=task_duration_ms,
            data={
                "parent_trace_id": cycle_trace_id,
                "job_id": int(job.get("id", 0) or 0),
                "task_id": int(job.get("task_id", 0) or 0),
                "task_text": str(job.get("task_text", "")),
                "result_preview": result[:240],
            },
        )
        record_execution_metric(
            "task_execution_completed",
            status=status,
            source=source,
            duration_ms=task_duration_ms,
        )
        complete_job(
            int(job["id"]),
            status,
            trace_id=job_trace_id,
            source=source,
            parent_trace_id=cycle_trace_id,
            result_preview=result[:240],
            duration_ms=task_duration_ms,
        )
        processed += 1
        lines.append(f"- job {job['id']}: task #{job['task_id']} -> {status}")

        if not until_idle and processed >= limit:
            break

    if processed >= limit and until_idle:
        lines.append(f"- max_jobs_reached: {limit}")
    lines.append(f"- processed: {processed}")
    final_status = "idle" if idle else "active"
    record_worker_run(processed, final_status, trace_id=cycle_trace_id)
    cycle_duration_ms = int((time.perf_counter() - cycle_started) * 1000)
    append_execution_event(
        "worker_cycle_completed",
        trace_id=cycle_trace_id,
        status=final_status,
        source=source,
        command="executor next",
        duration_ms=cycle_duration_ms,
        data={
            "cycle_label": cycle_label,
            "processed": processed,
            "idle": idle,
            "max_jobs": limit,
        },
    )
    record_execution_metric(
        "worker_cycle_completed",
        status=final_status,
        source=source,
        duration_ms=cycle_duration_ms,
    )
    return {
        "processed": processed,
        "idle": idle,
        "trace_id": cycle_trace_id,
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
        f"- last_worker_trace_id: {summary['last_worker_trace_id'] or '-'}",
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


def get_job_queue_snapshot(
    *,
    agent_scope: str | None = None,
    roles: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return queue summary and jobs, optionally filtered by scope visibility."""
    state = load_job_queue_state()
    jobs = list(state.get("jobs", []))
    if agent_scope:
        jobs = _filter_jobs_by_scope(jobs, agent_scope=agent_scope, roles=roles)
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
        "summary": {
            "total_jobs": len(jobs),
            "queued_jobs": counts["queued"],
            "leased_jobs": counts["leased"],
            "done_jobs": counts["done"],
            "failed_jobs": counts["failed"],
            "requeued_jobs": counts["requeued"],
            "last_worker_run_at": worker.get("last_run_at", ""),
            "last_worker_status": worker.get("last_status", ""),
            "last_worker_processed": int(worker.get("last_processed", 0) or 0),
            "last_worker_trace_id": worker.get("last_trace_id", ""),
        },
        "queue": {
            "jobs": jobs,
            "worker": worker,
        },
        "scope_filter": {
            "agent_scope": str(agent_scope or "").strip().lower(),
            "roles": list(roles),
        },
    }


def _record_runtime_queue_depth(state: dict[str, Any]) -> None:
    """Update runtime queue depth metrics from the current queue state."""
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
    record_queue_depth_metric(
        queue_name="runtime_jobs",
        queued=counts["queued"],
        leased=counts["leased"],
        done=counts["done"],
        failed=counts["failed"],
        requeued=counts["requeued"],
    )


def _filter_jobs_by_scope(
    jobs: list[dict[str, Any]],
    *,
    agent_scope: str,
    roles: tuple[str, ...],
) -> list[dict[str, Any]]:
    from cadiax.core.agent_context import _is_scope_visible  # type: ignore[attr-defined]

    requested_scope = str(agent_scope or "").strip().lower() or "default"
    return [
        job
        for job in jobs
        if _is_scope_visible(str(job.get("agent_scope", "default") or "default"), requested_scope, roles=roles)
    ]
