"""Self-review skill handler."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from otonomassist.core.agent_context import add_planner_task, append_lesson, append_memory_entry, load_planner_state
from otonomassist.core.result_builder import build_result
from otonomassist.core.workspace_guard import get_workspace_root, resolve_workspace_path
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"api[_-]?key", re.IGNORECASE),
]


def _project_root() -> Path:
    """Return the effective workspace root at call time."""
    return get_workspace_root()


def handle(args: str) -> str:
    """Run a heuristic self-review."""
    args = args.strip()
    if not args:
        return _usage()

    command, _, remainder = args.partition(" ")
    command = command.lower().strip()
    remainder = remainder.strip()

    if command == "file":
        return _review_file(remainder)
    if command == "text":
        return _review_text(remainder)

    return _review_text(args)


def _usage() -> str:
    return (
        "Usage: self-review <file|text> ...\n"
        "Examples:\n"
        "- self-review file src/otonomassist/core/assistant.py\n"
        "- self-review text hasil implementasi memory dan planner"
    )


def _review_file(path_text: str) -> str:
    if not path_text:
        return "Self-review file membutuhkan path."

    try:
        path = resolve_workspace_path(path_text)
    except ValueError:
        return "Path di luar workspace tidak diizinkan."
    if not path.exists() or not path.is_file():
        return f"File tidak ditemukan: {path_text}"

    content = path.read_text(encoding="utf-8", errors="replace")
    findings = _collect_findings(content, path)
    project_root = _project_root()
    source = f"file:{path.relative_to(project_root)}"
    persistence = _persist_review(findings, source)
    return _build_review_result(
        findings=findings,
        target=str(path.relative_to(project_root)),
        target_type="file",
        source=source,
        persistence=persistence,
    )


def _review_text(text: str) -> str:
    if not text:
        return "Self-review text membutuhkan isi."

    findings = _collect_findings(text, None)
    persistence = _persist_review(findings, "text")
    return _build_review_result(
        findings=findings,
        target="text",
        target_type="text",
        source="text",
        persistence=persistence,
    )


def _collect_findings(content: str, path: Path | None) -> list[str]:
    findings: list[str] = []
    if "TODO" in content or "FIXME" in content or "XXX" in content:
        findings.append("Ada marker TODO/FIXME/XXX yang menunjukkan pekerjaan belum selesai.")

    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            findings.append("Ada indikasi secret atau API key di konten yang perlu diamankan.")
            break

    long_lines = sum(1 for line in content.splitlines() if len(line) > 120)
    if long_lines:
        findings.append(f"Ada {long_lines} baris yang lebih panjang dari 120 karakter.")

    if path and path.suffix == ".py":
        try:
            ast.parse(content)
        except SyntaxError as exc:
            findings.append(f"Syntax error Python terdeteksi: {exc.msg} line {exc.lineno}.")

    if not findings:
        findings.append("Tidak ada masalah heuristik yang menonjol; lanjutkan dengan review manual bila tugasnya sensitif.")

    return findings


def _build_review_result(
    findings: list[str],
    target: str,
    target_type: str,
    source: str,
    persistence: dict[str, object],
) -> dict[str, object]:
    """Build the structured self-review result."""
    has_risk = bool(findings and "Tidak ada masalah heuristik" not in findings[0])
    return build_result(
        "self_review_result",
        {
            "target": target,
            "target_type": target_type,
            "source": source,
            "finding_count": len(findings),
            "risk_level": "attention" if has_risk else "low",
            "findings": [{"index": index, "text": finding} for index, finding in enumerate(findings, start=1)],
            "next_step": (
                "Verifikasi manual area yang paling berisiko lebih dulu."
                if has_risk
                else "Lanjutkan hanya jika area ini memang bukan area sensitif."
            ),
            "persistence": persistence,
            "summary": (
                f"Self-review pada {target_type} '{target}' menghasilkan {len(findings)} temuan."
            ),
        },
        source_skill="self-review",
        default_view="summary",
        review_source=source,
    )


def _persist_review(findings: list[str], source: str) -> dict[str, object]:
    material = " | ".join(findings)
    append_memory_entry(f"self-review {source}: {material}", source="self-review")
    persistence: dict[str, object] = {
        "memory_written": True,
        "lesson_written": False,
        "follow_up_tasks": [],
        "duplicate_follow_up_skipped": [],
    }
    if findings and "Tidak ada masalah heuristik" not in findings[0]:
        append_lesson(f"self-review {source}: {material}")
        persistence["lesson_written"] = True
        for task_text in (
            "agent-loop next",
            f"memory add follow-up self-review diperlukan untuk {source}",
        ):
            if _has_open_follow_up(task_text):
                persistence["duplicate_follow_up_skipped"].append(task_text)
                continue

            follow_up = add_planner_task(task_text, status="todo")
            persistence["follow_up_tasks"].append(
                {"id": follow_up["id"], "text": follow_up["text"], "status": follow_up["status"]}
            )
            append_memory_entry(
                f"self-review created follow-up task #{follow_up['id']} for {source}",
                source="self-review",
            )
    return persistence


def _has_open_follow_up(task_text: str) -> bool:
    """Check whether the same follow-up task is already open."""
    state = load_planner_state()
    return any(
        task.get("text") == task_text and task.get("status") in {"todo", "blocked"}
        for task in state.get("tasks", [])
    )
