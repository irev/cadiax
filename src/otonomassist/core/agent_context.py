"""Persistent agent context utilities."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import os

from otonomassist.core.secure_storage import decrypt_secret
from otonomassist.core.workspace_guard import ensure_internal_state_write_allowed, ensure_read_allowed

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / ".otonomassist"
MEMORY_FILE = DATA_DIR / "memory.jsonl"
PLANNER_FILE = DATA_DIR / "planner.json"
PROFILE_FILE = DATA_DIR / "profile.md"
LESSONS_FILE = DATA_DIR / "lessons.md"
SECRETS_FILE = DATA_DIR / "secrets.json"

DEFAULT_PROFILE = """# Agent Profile

## Purpose
- Menjadi private AI yang bekerja mandiri di workspace lokal.

## Preferences
- Utamakan bahasa Indonesia kecuali diminta sebaliknya.
- Utamakan solusi pragmatis dan berbasis data lokal.

## Constraints
- Jangan berasumsi bahwa internet selalu diperlukan.
- Gunakan memori lokal dan file workspace sebagai sumber konteks utama.

## Long-term Context
- Belum ada konteks jangka panjang yang ditetapkan.
"""

DEFAULT_LESSONS = """# Learned Lessons

- Belum ada pelajaran yang dikonsolidasikan.
"""


def ensure_agent_storage() -> None:
    """Ensure persistent agent files exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists():
        ensure_internal_state_write_allowed(MEMORY_FILE)
        MEMORY_FILE.touch()
    if not PLANNER_FILE.exists():
        ensure_internal_state_write_allowed(PLANNER_FILE)
        PLANNER_FILE.write_text(json.dumps({"goal": "", "tasks": []}, indent=2), encoding="utf-8")
    if not PROFILE_FILE.exists():
        ensure_internal_state_write_allowed(PROFILE_FILE)
        PROFILE_FILE.write_text(DEFAULT_PROFILE, encoding="utf-8")
    if not LESSONS_FILE.exists():
        ensure_internal_state_write_allowed(LESSONS_FILE)
        LESSONS_FILE.write_text(DEFAULT_LESSONS, encoding="utf-8")
    if not SECRETS_FILE.exists():
        ensure_internal_state_write_allowed(SECRETS_FILE)
        SECRETS_FILE.write_text(json.dumps({"secrets": {}}, indent=2), encoding="utf-8")


def load_markdown(path: Path, max_chars: int = 1600) -> str:
    """Load a markdown file with truncation."""
    ensure_agent_storage()
    ensure_read_allowed(path)
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n... (truncated)"


def load_recent_memories(limit: int = 8) -> list[dict[str, Any]]:
    """Load recent memory entries."""
    ensure_agent_storage()
    entries: list[dict[str, Any]] = []
    ensure_read_allowed(MEMORY_FILE)
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries[-limit:]


def load_planner_state() -> dict[str, Any]:
    """Load planner state."""
    ensure_agent_storage()
    ensure_read_allowed(PLANNER_FILE)
    return json.loads(PLANNER_FILE.read_text(encoding="utf-8"))


def save_planner_state(state: dict[str, Any]) -> None:
    """Persist planner state."""
    ensure_agent_storage()
    ensure_internal_state_write_allowed(PLANNER_FILE)
    _write_text_atomic(PLANNER_FILE, json.dumps(state, indent=2))


def build_agent_context_block() -> str:
    """Build a compact persistent context block for prompting."""
    ensure_agent_storage()
    parts = [
        "Persistent agent context:",
        "",
        "## Profile",
        load_markdown(PROFILE_FILE, max_chars=1200),
        "",
        "## Learned Lessons",
        load_markdown(LESSONS_FILE, max_chars=1200),
    ]

    planner = load_planner_state()
    tasks = planner.get("tasks", [])
    parts.extend(
        [
            "",
            "## Planner",
            f"- goal: {planner.get('goal') or '-'}",
            f"- total_tasks: {len(tasks)}",
        ]
    )
    next_task = next((task for task in tasks if task.get("status") == "todo"), None)
    if next_task:
        parts.append(f"- next_task: #{next_task.get('id')} {next_task.get('text')}")

    memories = load_recent_memories(limit=5)
    parts.extend(["", "## Recent Memories"])
    if memories:
        for entry in memories:
            parts.append(f"- #{entry.get('id')}: {entry.get('text', '')}")
    else:
        parts.append("- belum ada memori")

    return "\n".join(parts)


def append_memory_entry(text: str, source: str = "manual") -> dict[str, Any]:
    """Append a memory entry and return it."""
    ensure_agent_storage()
    entries = load_recent_memories(limit=10_000)
    entry = {
        "id": len(entries) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "text": text,
    }
    ensure_internal_state_write_allowed(MEMORY_FILE)
    with MEMORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
    return entry


def append_lesson(text: str) -> None:
    """Append a lesson bullet to lessons.md."""
    ensure_agent_storage()
    ensure_read_allowed(LESSONS_FILE)
    content = LESSONS_FILE.read_text(encoding="utf-8", errors="replace").rstrip()
    stamp = datetime.now(timezone.utc).date().isoformat()
    bullet = f"- {stamp}: {text}"
    recent_lines = [line.strip() for line in content.splitlines()[-20:] if line.strip()]
    if bullet in recent_lines:
        return
    ensure_internal_state_write_allowed(LESSONS_FILE)
    LESSONS_FILE.write_text(f"{content}\n{bullet}\n", encoding="utf-8")


def add_planner_task(text: str, status: str = "todo") -> dict[str, Any]:
    """Add a task to planner.json."""
    state = load_planner_state()
    tasks = state.setdefault("tasks", [])
    task = {
        "id": len(tasks) + 1,
        "text": text,
        "status": status,
        "notes": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    tasks.append(task)
    state["updated_at"] = task["created_at"]
    save_planner_state(state)
    return task


def add_planner_note(task_id: int, note: str) -> bool:
    """Append a note to a planner task."""
    state = load_planner_state()
    for task in state.get("tasks", []):
        if task.get("id") == task_id:
            task.setdefault("notes", []).append(note)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_planner_state(state)
            return True
    return False


def get_next_planner_task() -> dict[str, Any] | None:
    """Return the first todo task."""
    state = load_planner_state()
    return next((task for task in state.get("tasks", []) if task.get("status") == "todo"), None)


def update_planner_task_status(task_id: int, status: str) -> bool:
    """Update planner task status."""
    state = load_planner_state()
    for task in state.get("tasks", []):
        if task.get("id") == task_id:
            task["status"] = status
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_planner_state(state)
            return True
    return False


def load_secrets_state() -> dict[str, Any]:
    """Load secrets state."""
    ensure_agent_storage()
    ensure_read_allowed(SECRETS_FILE)
    raw = SECRETS_FILE.read_text(encoding="utf-8")
    if not raw.strip():
        return {"secrets": {}}
    return json.loads(raw)


def save_secrets_state(state: dict[str, Any]) -> None:
    """Persist secrets state."""
    ensure_agent_storage()
    ensure_internal_state_write_allowed(SECRETS_FILE)
    _write_text_atomic(SECRETS_FILE, json.dumps(state, indent=2))


def get_secret_value(name: str) -> str | None:
    """Get a decrypted secret value by name for internal runtime use."""
    state = load_secrets_state()
    meta = state.get("secrets", {}).get(name)
    if not meta:
        return None

    encrypted_value = meta.get("encrypted_value")
    if encrypted_value:
        return decrypt_secret(encrypted_value)

    # Legacy plaintext fallback.
    return meta.get("value")


def get_env_or_secret(env_name: str, secret_name: str | None = None) -> str | None:
    """Read a value from environment first, then local encrypted secrets."""
    value = os.getenv(env_name)
    if value:
        return value
    return get_secret_value(secret_name or env_name.lower())


def _write_text_atomic(path: Path, text: str) -> None:
    """Write a file atomically to avoid partial reads of JSON state."""
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def append_markdown_bullet(path: Path, section_title: str, text: str) -> None:
    """Append a bullet under a markdown section."""
    ensure_agent_storage()
    ensure_read_allowed(path)
    content = path.read_text(encoding="utf-8", errors="replace")
    marker = f"## {section_title}"
    if marker not in content:
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n{marker}\n- {text}\n"
        ensure_internal_state_write_allowed(path)
        path.write_text(content, encoding="utf-8")
        return

    lines = content.splitlines()
    updated: list[str] = []
    inserted = False
    for index, line in enumerate(lines):
        updated.append(line)
        if line.strip() == marker:
            insert_at = index + 1
            while insert_at < len(lines) and not lines[insert_at].startswith("## "):
                insert_at += 1
            # Rebuild once with insertion before next section.
            prefix = lines[:insert_at]
            suffix = lines[insert_at:]
            if prefix and prefix[-1].strip():
                prefix.append(f"- {text}")
            else:
                prefix.extend([f"- {text}"])
            new_content = "\n".join(prefix + suffix).rstrip() + "\n"
            ensure_internal_state_write_allowed(path)
            path.write_text(new_content, encoding="utf-8")
            inserted = True
            break

    if not inserted:
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n{marker}\n- {text}\n"
        ensure_internal_state_write_allowed(path)
        path.write_text(content, encoding="utf-8")


def replace_section(path: Path, section_title: str, bullet_text: str) -> None:
    """Replace the contents of a markdown section with one bullet."""
    ensure_agent_storage()
    ensure_read_allowed(path)
    content = path.read_text(encoding="utf-8", errors="replace")
    marker = f"## {section_title}"
    lines = content.splitlines()
    start = None
    end = None
    for idx, line in enumerate(lines):
        if line.strip() == marker:
            start = idx
            continue
        if start is not None and line.startswith("## "):
            end = idx
            break
    if start is None:
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n{marker}\n- {bullet_text}\n"
        ensure_internal_state_write_allowed(path)
        path.write_text(content, encoding="utf-8")
        return
    if end is None:
        end = len(lines)
    rebuilt = lines[: start + 1] + [f"- {bullet_text}"] + lines[end:]
    ensure_internal_state_write_allowed(path)
    path.write_text("\n".join(rebuilt).rstrip() + "\n", encoding="utf-8")
