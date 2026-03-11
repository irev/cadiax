"""Executor skill handler."""

from __future__ import annotations

import asyncio
from pathlib import Path

from otonomassist.ai.factory import AIProviderFactory
from otonomassist.core.agent_context import (
    add_planner_note,
    append_lesson,
    append_memory_entry,
    build_agent_context_block,
    get_next_planner_task,
    update_planner_task_status,
)
from otonomassist.core.assistant import Assistant


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = PROJECT_ROOT / "skills"
KNOWN_PREFIXES = [
    "memory",
    "planner",
    "profile",
    "workspace",
    "self-review",
    "agent-loop",
    "executor",
    "runner",
    "research",
    "secrets",
    "ai",
    "help",
    "list",
    "debug-config",
    "list-models",
]


def handle(args: str) -> str:
    """Execute the next planner task or a provided command."""
    args = args.strip()
    if not args:
        args = "next"

    command, _, remainder = args.partition(" ")
    command = command.lower().strip()
    remainder = remainder.strip()

    if command == "next":
        return _execute_next_task()
    if command == "run":
        if not remainder:
            return "Executor run membutuhkan command."
        return _execute_command(remainder, task_id=None)

    resolved_command = _resolve_command(args)
    return _execute_command(resolved_command, task_id=None, original_task=args)


def _execute_next_task() -> str:
    task = get_next_planner_task()
    if not task:
        return "Tidak ada task todo untuk dieksekusi."

    task_text = task.get("text", "").strip()
    if not task_text:
        update_planner_task_status(task["id"], "blocked")
        add_planner_note(task["id"], "Task kosong dan tidak bisa dieksekusi.")
        return f"Task #{task['id']} kosong, ditandai blocked."

    if task_text.lower().startswith("executor "):
        update_planner_task_status(task["id"], "blocked")
        add_planner_note(task["id"], "Task executor rekursif diblokir.")
        return f"Task #{task['id']} diblokir karena memicu executor secara rekursif."

    resolved_command = _resolve_command(task_text)
    return _execute_command(resolved_command, task_id=task["id"], original_task=task_text)


def _execute_command(command: str, task_id: int | None, original_task: str | None = None) -> str:
    guard_error = _guard_autonomous_command(command, task_id)
    if guard_error:
        if task_id is not None:
            update_planner_task_status(task_id, "blocked")
            add_planner_note(task_id, guard_error)
            append_lesson(f"executor memblokir task #{task_id}: {command}")
            return f"Task #{task_id} diblokir.\n{guard_error}"
        return guard_error

    assistant = Assistant(skills_dir=SKILLS_DIR)
    assistant.initialize()

    result = assistant.execute(command)
    append_memory_entry(
        f"executor run command='{command}' result='{result[:500]}'",
        source="executor",
    )

    if task_id is not None:
        if original_task and original_task != command:
            add_planner_note(task_id, f"Resolved task to command: {command}")
        add_planner_note(task_id, f"Executed command: {command}")
        add_planner_note(task_id, f"Result: {result[:500]}")

        if result.startswith("[ERROR]") or result.lower().startswith("error"):
            update_planner_task_status(task_id, "blocked")
            append_lesson(f"executor gagal untuk task #{task_id}: {command}")
            return f"Task #{task_id} gagal dieksekusi.\n{result}"

        update_planner_task_status(task_id, "done")
        append_lesson(f"executor menyelesaikan task #{task_id}: {command}")
        return f"Task #{task_id} selesai dieksekusi.\n{result}"

    if result.startswith("[ERROR]") or result.lower().startswith("error"):
        append_lesson(f"executor run gagal: {command}")
    else:
        append_lesson(f"executor run berhasil: {command}")
    return result


def _guard_autonomous_command(command: str, task_id: int | None) -> str | None:
    """Block high-risk autonomous mutations while preserving manual executor runs."""
    if task_id is None:
        return None

    normalized = command.strip().lower()
    blocked_prefixes = {
        "secrets set": "Task otonom tidak boleh mengubah secrets secara otomatis.",
        "secrets delete": "Task otonom tidak boleh menghapus secrets secara otomatis.",
        "secrets import-env": "Task otonom tidak boleh mengimpor secrets dari environment secara otomatis.",
        "profile set-purpose": "Task otonom tidak boleh mengubah purpose profile secara otomatis.",
        "profile add-preference": "Task otonom tidak boleh menambah preference profile secara otomatis.",
        "profile add-constraint": "Task otonom tidak boleh menambah constraint profile secara otomatis.",
        "profile add-context": "Task otonom tidak boleh menambah long-term context profile secara otomatis.",
    }
    for prefix, message in blocked_prefixes.items():
        if normalized == prefix or normalized.startswith(prefix + " "):
            return message
    return None


def _resolve_command(task_text: str) -> str:
    task_text = task_text.strip()
    for prefix in KNOWN_PREFIXES:
        if task_text == prefix or task_text.startswith(prefix + " "):
            return task_text

    provider = AIProviderFactory.auto_detect()
    if not provider:
        return task_text

    prompt = (
        f"{build_agent_context_block()}\n\n"
        f"Task backlog: {task_text}\n\n"
        "Ubah task backlog ini menjadi SATU command internal yang executable.\n"
        "Gunakan salah satu prefix berikut: "
        + ", ".join(KNOWN_PREFIXES)
        + ".\n"
        "Jika tidak yakin, gunakan `agent-loop next` atau `ai ...`.\n"
        "Jawab HANYA command final tanpa penjelasan."
    )
    try:
        resolved = asyncio.run(
            provider.chat_completion(
                prompt=prompt,
                system_prompt=(
                    "Anda adalah resolver executor. Ubah task natural language "
                    "menjadi command internal OtonomAssist yang aman dan executable."
                ),
            )
        ).strip()
    except Exception:
        return task_text

    if not resolved:
        return task_text

    for prefix in KNOWN_PREFIXES:
        if resolved == prefix or resolved.startswith(prefix + " "):
            return resolved

    return f"ai {task_text}"
