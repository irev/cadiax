"""Worker skill handler."""

from __future__ import annotations

from pathlib import Path

from otonomassist.core.job_runtime import complete_job, enqueue_ready_planner_task, lease_next_job, render_job_queue
from otonomassist.core.assistant import Assistant


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = PROJECT_ROOT / "skills"


def handle(args: str) -> str:
    """Process jobs from the runtime queue."""
    text = args.strip().lower()
    if not text or text == "list":
        return render_job_queue()
    if text in {"once", "once --enqueue", "--enqueue once"}:
        return _run_jobs(1, enqueue_first="--enqueue" in text)
    if text.startswith("steps "):
        _, _, count_text = text.partition(" ")
        try:
            count = max(1, min(20, int(count_text.strip())))
        except ValueError:
            return "Format: worker steps <angka> [--enqueue]"
        return _run_jobs(count, enqueue_first="--enqueue" in text)
    return "Usage: worker <list|once|once --enqueue|steps N>"


def _run_jobs(count: int, enqueue_first: bool) -> str:
    assistant = Assistant(skills_dir=SKILLS_DIR)
    assistant.initialize()
    lines = [f"Worker processing {count} job(s):"]
    processed = 0
    for _ in range(count):
        if enqueue_first:
            enqueue_ready_planner_task()
        job = lease_next_job()
        if not job:
            lines.append("- idle: tidak ada job queued")
            break
        result = assistant.execute("executor next")
        status = "done"
        if "dijadwalkan ulang" in result:
            status = "requeued"
        elif "gagal dieksekusi" in result:
            status = "failed"
        complete_job(int(job["id"]), status)
        processed += 1
        lines.append(f"- job {job['id']}: task #{job['task_id']} -> {status}")
    lines.append(f"- processed: {processed}")
    return "\n".join(lines)
