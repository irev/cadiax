"""Planner skill handler."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from otonomassist.core.agent_context import load_planner_state, save_planner_state
from otonomassist.core.result_builder import build_result
from otonomassist.core.workspace_guard import ensure_internal_state_write_allowed


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / ".otonomassist"
PLANNER_FILE = DATA_DIR / "planner.json"


def handle(args: str) -> str:
    """Manage autonomous planning state."""
    args = args.strip()
    if not args:
        return _usage()

    command, _, remainder = args.partition(" ")
    command = command.lower().strip()
    remainder = remainder.strip()

    if command == "set-goal":
        return _set_goal(remainder)
    if command == "add":
        return _add_task(remainder)
    if command == "list":
        return _list_tasks()
    if command == "next":
        return _next_task()
    if command == "done":
        return _update_status(remainder, "done")
    if command == "blocked":
        return _mark_blocked(remainder)
    if command == "note":
        return _add_note(remainder)
    if command == "clear":
        return _clear_plan()
    if command == "summary":
        return _summary()

    return _usage()


def _usage() -> str:
    return (
        "Usage: planner <set-goal|add|list|next|done|blocked|note|clear|summary> ...\n"
        "Examples:\n"
        "- planner set-goal bangun private ai lokal\n"
        "- planner add buat skill memory\n"
        "- planner next"
    )


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PLANNER_FILE.exists():
        _save_state({"goal": "", "tasks": []})


def _load_state() -> dict[str, Any]:
    _ensure_storage()
    return load_planner_state()


def _save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ensure_internal_state_write_allowed(PLANNER_FILE)
    save_planner_state(state)


def _set_goal(goal: str) -> str:
    if not goal:
        return "Planner set-goal membutuhkan tujuan."

    state = _load_state()
    state["goal"] = goal
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)
    return "Tujuan planner diperbarui."


def _add_task(task_text: str) -> str:
    if not task_text:
        return "Planner add membutuhkan isi task."

    state = _load_state()
    tasks = state.setdefault("tasks", [])
    task = {
        "id": len(tasks) + 1,
        "text": task_text,
        "status": "todo",
        "notes": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    tasks.append(task)
    state["updated_at"] = task["created_at"]
    _save_state(state)
    return f"Task #{task['id']} ditambahkan."


def _list_tasks() -> str:
    state = _load_state()
    tasks = state.get("tasks", [])
    if not tasks:
        return _wrap_result(
            result_type="planner_list",
            data={
                "goal": state.get("goal") or "-",
                "task_count": 0,
                "tasks": [],
                "summary": "Tidak ada task di planner.",
            },
            default_view="table",
        )

    return _wrap_result(
        result_type="planner_list",
        data={
            "goal": state.get("goal") or "-",
            "task_count": len(tasks),
            "tasks": [
                {
                    "id": task.get("id"),
                    "status": task.get("status", ""),
                    "text": task.get("text", ""),
                    "notes_count": len(task.get("notes", [])),
                }
                for task in tasks
            ],
            "summary": f"Planner memiliki {len(tasks)} task.",
        },
        default_view="table",
    )


def _next_task() -> str:
    state = _load_state()
    for task in state.get("tasks", []):
        if task.get("status") == "todo":
            return _wrap_result(
                result_type="planner_next",
                data={
                    "goal": state.get("goal") or "-",
                    "next_task": {
                        "id": task.get("id"),
                        "status": task.get("status", ""),
                        "text": task.get("text", ""),
                        "notes": task.get("notes", []),
                    },
                    "summary": f"Task berikutnya adalah #{task['id']} {task['text']}",
                },
                default_view="summary",
            )
    return "Tidak ada task berikutnya. Semua task selesai atau terblokir."


def _update_status(id_text: str, status: str) -> str:
    try:
        task_id = int(id_text)
    except ValueError:
        return "ID task harus berupa angka."

    state = _load_state()
    for task in state.get("tasks", []):
        if task.get("id") == task_id:
            task["status"] = status
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_state(state)
            return f"Task #{task_id} ditandai {status}."

    return f"Task #{task_id} tidak ditemukan."


def _mark_blocked(args: str) -> str:
    id_text, _, note = args.partition(" ")
    try:
        task_id = int(id_text)
    except ValueError:
        return "Format: planner blocked <id> <alasan>"

    state = _load_state()
    for task in state.get("tasks", []):
        if task.get("id") == task_id:
            task["status"] = "blocked"
            if note:
                task.setdefault("notes", []).append(note)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_state(state)
            return f"Task #{task_id} ditandai blocked."

    return f"Task #{task_id} tidak ditemukan."


def _add_note(args: str) -> str:
    id_text, _, note = args.partition(" ")
    try:
        task_id = int(id_text)
    except ValueError:
        return "Format: planner note <id> <catatan>"

    if not note:
        return "Planner note membutuhkan catatan."

    state = _load_state()
    for task in state.get("tasks", []):
        if task.get("id") == task_id:
            task.setdefault("notes", []).append(note)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_state(state)
            return f"Catatan ditambahkan ke task #{task_id}."

    return f"Task #{task_id} tidak ditemukan."


def _clear_plan() -> str:
    _save_state({"goal": "", "tasks": []})
    return "Planner dibersihkan."


def _summary() -> str:
    state = _load_state()
    tasks = state.get("tasks", [])
    counts = {"todo": 0, "done": 0, "blocked": 0}
    for task in tasks:
        counts[task.get("status", "todo")] = counts.get(task.get("status", "todo"), 0) + 1

    return _wrap_result(
        result_type="planner_summary",
        data={
            "goal": state.get("goal") or "-",
            "total_tasks": len(tasks),
            "todo": counts.get("todo", 0),
            "done": counts.get("done", 0),
            "blocked": counts.get("blocked", 0),
            "summary": (
                f"Planner memiliki {len(tasks)} task: "
                f"{counts.get('todo', 0)} todo, {counts.get('done', 0)} done, "
                f"{counts.get('blocked', 0)} blocked."
            ),
        },
        default_view="summary",
    )


def _wrap_result(result_type: str, data: dict[str, object], default_view: str) -> dict[str, object]:
    """Wrap planner output into the shared structured-result envelope."""
    return build_result(
        result_type,
        data,
        source_skill="planner",
        default_view=default_view,
    )
