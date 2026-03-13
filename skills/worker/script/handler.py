"""Worker skill handler."""

from __future__ import annotations

from pathlib import Path

from cadiax.core.job_runtime import process_job_queue, render_job_queue
from cadiax.core.assistant import Assistant


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = PROJECT_ROOT / "skills"


def handle(args: str) -> str:
    """Process jobs from the runtime queue."""
    text = args.strip().lower()
    if not text or text == "list":
        return render_job_queue()
    if text in {"once", "once --enqueue", "--enqueue once"}:
        return _run_jobs(1, enqueue_first="--enqueue" in text, until_idle=False)
    if text in {"until-idle", "until-idle --enqueue", "--enqueue until-idle"}:
        return _run_jobs(20, enqueue_first="--enqueue" in text, until_idle=True)
    if text.startswith("steps "):
        _, _, count_text = text.partition(" ")
        count_part = count_text.replace("--enqueue", "").strip()
        try:
            count = max(1, min(20, int(count_part)))
        except ValueError:
            return "Format: worker steps <angka> [--enqueue]"
        return _run_jobs(count, enqueue_first="--enqueue" in text, until_idle=False)
    return "Usage: worker <list|once|once --enqueue|until-idle|until-idle --enqueue|steps N>"


def _run_jobs(count: int, enqueue_first: bool, until_idle: bool) -> str:
    assistant = Assistant(skills_dir=SKILLS_DIR)
    assistant.initialize()
    result = process_job_queue(
        assistant,
        max_jobs=count,
        enqueue_first=enqueue_first,
        until_idle=until_idle,
    )
    return str(result["output"])
