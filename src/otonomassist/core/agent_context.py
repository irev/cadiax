"""Persistent agent context utilities."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import os

from otonomassist.storage import SQLiteStateStore
from otonomassist.core.secure_storage import decrypt_secret
from otonomassist.core.workspace_guard import ensure_internal_state_write_allowed, ensure_read_allowed, ensure_workspace_root_exists

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("OTONOMASSIST_STATE_DIR", str(PROJECT_ROOT / ".otonomassist"))).expanduser().resolve()
MEMORY_FILE = DATA_DIR / "memory.jsonl"
PLANNER_FILE = DATA_DIR / "planner.json"
PROFILE_FILE = DATA_DIR / "profile.md"
PREFERENCES_FILE = DATA_DIR / "preferences.json"
LESSONS_FILE = DATA_DIR / "lessons.md"
SECRETS_FILE = DATA_DIR / "secrets.json"
EXECUTION_HISTORY_FILE = DATA_DIR / "execution_history.jsonl"
METRICS_FILE = DATA_DIR / "execution_metrics.json"
JOB_QUEUE_FILE = DATA_DIR / "job_queue.json"
SCHEDULER_STATE_FILE = DATA_DIR / "scheduler_state.json"
STATE_DB_FILENAME = "state.db"
SECRET_NAME_ALIASES = {
    "OPENAI_API_KEY": "openai_api_key",
    "openai_api_key": "openai_api_key",
    "ANTHROPIC_API_KEY": "anthropic_api_key",
    "anthropic_api_key": "anthropic_api_key",
    "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
    "telegram_bot_token": "telegram_bot_token",
}

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

PLANNER_STATE_KEY = "planner"
JOB_QUEUE_STATE_KEY = "job_queue"
METRICS_STATE_KEY = "metrics"
SCHEDULER_STATE_KEY = "scheduler"
PREFERENCE_STATE_KEY = "preferences"

DEFAULT_PLANNER_STATE = {"goal": "", "tasks": []}
DEFAULT_METRICS_STATE = {"counters": {}, "timings": {}, "updated_at": ""}
DEFAULT_JOB_QUEUE_STATE = {"jobs": []}
DEFAULT_SCHEDULER_STATE = {"last_run_at": "", "last_status": "", "last_cycles": 0, "last_processed": 0}
DEFAULT_PREFERENCE_STATE = {"preferences": []}


def ensure_agent_storage() -> None:
    """Ensure persistent agent files exist."""
    ensure_workspace_root_exists()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists():
        ensure_internal_state_write_allowed(MEMORY_FILE)
        MEMORY_FILE.touch()
    if not PLANNER_FILE.exists():
        ensure_internal_state_write_allowed(PLANNER_FILE)
        PLANNER_FILE.write_text(json.dumps(DEFAULT_PLANNER_STATE, indent=2), encoding="utf-8")
    if not PROFILE_FILE.exists():
        ensure_internal_state_write_allowed(PROFILE_FILE)
        PROFILE_FILE.write_text(DEFAULT_PROFILE, encoding="utf-8")
    if not PREFERENCES_FILE.exists():
        ensure_internal_state_write_allowed(PREFERENCES_FILE)
        PREFERENCES_FILE.write_text(json.dumps(DEFAULT_PREFERENCE_STATE, indent=2), encoding="utf-8")
    if not LESSONS_FILE.exists():
        ensure_internal_state_write_allowed(LESSONS_FILE)
        LESSONS_FILE.write_text(DEFAULT_LESSONS, encoding="utf-8")
    if not SECRETS_FILE.exists():
        ensure_internal_state_write_allowed(SECRETS_FILE)
        SECRETS_FILE.write_text(json.dumps({"secrets": {}}, indent=2), encoding="utf-8")
    if not EXECUTION_HISTORY_FILE.exists():
        ensure_internal_state_write_allowed(EXECUTION_HISTORY_FILE)
        EXECUTION_HISTORY_FILE.touch()
    if not METRICS_FILE.exists():
        ensure_internal_state_write_allowed(METRICS_FILE)
        METRICS_FILE.write_text(
            json.dumps(DEFAULT_METRICS_STATE, indent=2),
            encoding="utf-8",
        )
    if not JOB_QUEUE_FILE.exists():
        ensure_internal_state_write_allowed(JOB_QUEUE_FILE)
        JOB_QUEUE_FILE.write_text(json.dumps(DEFAULT_JOB_QUEUE_STATE, indent=2), encoding="utf-8")
    if not SCHEDULER_STATE_FILE.exists():
        ensure_internal_state_write_allowed(SCHEDULER_STATE_FILE)
        SCHEDULER_STATE_FILE.write_text(
            json.dumps(DEFAULT_SCHEDULER_STATE, indent=2),
            encoding="utf-8",
        )
    ensure_internal_state_write_allowed(get_state_db_path())
    _get_state_store().ensure_initialized()
    _bootstrap_durable_state()


def get_state_db_path() -> Path:
    """Return the durable SQLite state database path."""
    raw = os.getenv("OTONOMASSIST_STATE_DB", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (DATA_DIR / STATE_DB_FILENAME).resolve()


def get_state_storage_info() -> dict[str, str]:
    """Describe the current durable state backend."""
    db_path = get_state_db_path()
    return {
        "backend": "sqlite",
        "path": str(db_path),
        "legacy_mirror": "enabled",
        "exists": "yes" if db_path.exists() else "no",
    }


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
    return _load_durable_json_state(PLANNER_STATE_KEY, PLANNER_FILE, DEFAULT_PLANNER_STATE)


def save_planner_state(state: dict[str, Any]) -> None:
    """Persist planner state."""
    _save_durable_json_state(PLANNER_STATE_KEY, PLANNER_FILE, state)


def build_agent_context_block(query: str | None = None) -> str:
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

    memories = retrieve_relevant_memories(query, limit=5) if query and query.strip() else load_recent_memories(limit=5)
    parts.extend(["", "## Relevant Memories" if query and query.strip() else "## Recent Memories"])
    if memories:
        for entry in memories:
            parts.append(f"- #{entry.get('id')}: {entry.get('text', '')}")
    else:
        parts.append("- tidak ada memori relevan" if query and query.strip() else "- belum ada memori")

    return "\n".join(parts)


def build_runtime_context_block(query: str | None = None) -> str:
    """Build planner, lessons, and memory context without personality/profile."""
    ensure_agent_storage()
    parts = [
        "Persistent runtime context:",
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

    memories = retrieve_relevant_memories(query, limit=5) if query and query.strip() else load_recent_memories(limit=5)
    parts.extend(["", "## Relevant Memories" if query and query.strip() else "## Recent Memories"])
    if memories:
        for entry in memories:
            parts.append(f"- #{entry.get('id')}: {entry.get('text', '')}")
    else:
        parts.append("- tidak ada memori relevan" if query and query.strip() else "- belum ada memori")

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
        "retry_count": 0,
        "max_retries": 2,
        "last_error": "",
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
    """Return the highest-priority ready todo task."""
    state = load_planner_state()
    tasks = state.get("tasks", [])
    done_ids = {int(task.get("id", 0)) for task in tasks if task.get("status") == "done"}
    ready_tasks = [
        task
        for task in tasks
        if task.get("status") == "todo" and _task_dependencies_satisfied(task, done_ids)
    ]
    if not ready_tasks:
        return None
    return sorted(
        ready_tasks,
        key=lambda item: (-int(item.get("priority", 0) or 0), int(item.get("id", 0) or 0)),
    )[0]


def list_ready_planner_tasks() -> list[dict[str, Any]]:
    """List planner tasks that are currently ready to run."""
    state = load_planner_state()
    tasks = state.get("tasks", [])
    done_ids = {int(task.get("id", 0)) for task in tasks if task.get("status") == "done"}
    return [
        task
        for task in sorted(
            tasks,
            key=lambda item: (-int(item.get("priority", 0) or 0), int(item.get("id", 0) or 0)),
        )
        if task.get("status") == "todo" and _task_dependencies_satisfied(task, done_ids)
    ]


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


def get_planner_task(task_id: int) -> dict[str, Any] | None:
    """Return a planner task by id."""
    state = load_planner_state()
    return next((task for task in state.get("tasks", []) if task.get("id") == task_id), None)


def update_planner_task_fields(task_id: int, **fields: Any) -> bool:
    """Update arbitrary planner task fields."""
    state = load_planner_state()
    for task in state.get("tasks", []):
        if task.get("id") == task_id:
            task.update(fields)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_planner_state(state)
            return True
    return False


def retrieve_relevant_memories(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve memory entries by simple token overlap and recency weighting."""
    normalized = _tokenize_text(query)
    if not normalized:
        return load_recent_memories(limit=limit)

    scored: list[tuple[float, dict[str, Any]]] = []
    for entry in load_recent_memories(limit=10_000):
        text = str(entry.get("text", ""))
        tokens = _tokenize_text(text)
        if not tokens:
            continue
        overlap = len(normalized.intersection(tokens))
        if overlap <= 0:
            continue
        recency_bonus = min(int(entry.get("id", 0) or 0) / 10_000.0, 0.25)
        scored.append((float(overlap) + recency_bonus, entry))

    return [
        entry
        for _, entry in sorted(
            scored,
            key=lambda item: (-item[0], -int(item[1].get("id", 0) or 0)),
        )[: max(1, limit)]
    ]


def load_job_queue_state() -> dict[str, Any]:
    """Load runtime job queue state."""
    return _load_durable_json_state(JOB_QUEUE_STATE_KEY, JOB_QUEUE_FILE, DEFAULT_JOB_QUEUE_STATE)


def save_job_queue_state(state: dict[str, Any]) -> None:
    """Persist runtime job queue state."""
    _save_durable_json_state(JOB_QUEUE_STATE_KEY, JOB_QUEUE_FILE, state)


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


def load_metrics_state() -> dict[str, Any]:
    """Load aggregated execution metrics state."""
    return _load_durable_json_state(METRICS_STATE_KEY, METRICS_FILE, DEFAULT_METRICS_STATE)


def save_metrics_state(state: dict[str, Any]) -> None:
    """Persist aggregated execution metrics state."""
    _save_durable_json_state(METRICS_STATE_KEY, METRICS_FILE, state)


def load_scheduler_state() -> dict[str, Any]:
    """Load scheduler runtime state."""
    return _load_durable_json_state(SCHEDULER_STATE_KEY, SCHEDULER_STATE_FILE, DEFAULT_SCHEDULER_STATE)


def save_scheduler_state(state: dict[str, Any]) -> None:
    """Persist scheduler runtime state."""
    _save_durable_json_state(SCHEDULER_STATE_KEY, SCHEDULER_STATE_FILE, state)


def load_preference_state() -> dict[str, Any]:
    """Load structured personality preferences from durable state."""
    state = _load_durable_json_state(PREFERENCE_STATE_KEY, PREFERENCES_FILE, DEFAULT_PREFERENCE_STATE)
    if state.get("preferences"):
        return state
    preferences = parse_markdown_section_bullets(PROFILE_FILE, "Preferences")
    if preferences:
        state = {"preferences": preferences}
        save_preference_state(state)
    return state


def save_preference_state(state: dict[str, Any]) -> None:
    """Persist structured personality preferences."""
    normalized = {
        "preferences": [
            str(item).strip()
            for item in state.get("preferences", [])
            if str(item).strip()
        ]
    }
    _save_durable_json_state(PREFERENCE_STATE_KEY, PREFERENCES_FILE, normalized)


def list_preferences() -> list[str]:
    """Return normalized preference items."""
    state = load_preference_state()
    seen: set[str] = set()
    items: list[str] = []
    for raw in state.get("preferences", []):
        text = str(raw).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    return items


def get_secret_value(name: str) -> str | None:
    """Get a decrypted secret value by name for internal runtime use."""
    state = load_secrets_state()
    secrets = state.get("secrets", {})
    meta = secrets.get(name)
    if not meta:
        canonical_name = canonicalize_secret_name(name)
        if canonical_name != name:
            meta = secrets.get(canonical_name)
    if not meta:
        lowered = name.lower()
        for secret_name, secret_meta in secrets.items():
            if secret_name.lower() == lowered:
                meta = secret_meta
                break
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
    return get_secret_value(secret_name or canonicalize_secret_name(env_name))


def canonicalize_secret_name(name: str) -> str:
    """Normalize a secret name to its canonical runtime key where known."""
    return SECRET_NAME_ALIASES.get(name.strip(), name.strip())


def _task_dependencies_satisfied(task: dict[str, Any], done_ids: set[int]) -> bool:
    depends_on = task.get("depends_on", [])
    if not isinstance(depends_on, list):
        return True
    normalized = {int(item) for item in depends_on if str(item).strip().isdigit()}
    return normalized.issubset(done_ids)


def _tokenize_text(text: str) -> set[str]:
    return {
        cleaned.lower()
        for raw in str(text).replace("\n", " ").split()
        for cleaned in [raw.strip(".,:;!?()[]{}\"'")]
        if len(cleaned) >= 4
    }


def _write_text_atomic(path: Path, text: str) -> None:
    """Write a file atomically to avoid partial reads of JSON state."""
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def _get_state_store() -> SQLiteStateStore:
    return SQLiteStateStore(get_state_db_path())


def _bootstrap_durable_state() -> None:
    store = _get_state_store()
    _ensure_state_in_store(store, PLANNER_STATE_KEY, PLANNER_FILE, DEFAULT_PLANNER_STATE)
    _ensure_state_in_store(store, JOB_QUEUE_STATE_KEY, JOB_QUEUE_FILE, DEFAULT_JOB_QUEUE_STATE)
    _ensure_state_in_store(store, METRICS_STATE_KEY, METRICS_FILE, DEFAULT_METRICS_STATE)
    _ensure_state_in_store(store, SCHEDULER_STATE_KEY, SCHEDULER_STATE_FILE, DEFAULT_SCHEDULER_STATE)
    _ensure_preference_state_in_store(store)


def _ensure_state_in_store(
    store: SQLiteStateStore,
    state_key: str,
    legacy_path: Path,
    default: dict[str, Any],
) -> None:
    if store.get_json_state(state_key) is not None:
        return
    value, _ = _read_legacy_json_state(legacy_path, default)
    store.upsert_json_state(state_key, value)


def _ensure_preference_state_in_store(store: SQLiteStateStore) -> None:
    record = store.get_json_state(PREFERENCE_STATE_KEY)
    if record is not None and record.value.get("preferences"):
        return
    legacy_value, _ = _read_legacy_json_state(PREFERENCES_FILE, DEFAULT_PREFERENCE_STATE)
    preferences = [
        str(item).strip()
        for item in legacy_value.get("preferences", [])
        if str(item).strip()
    ]
    if not preferences:
        preferences = parse_markdown_section_bullets(PROFILE_FILE, "Preferences")
    store.upsert_json_state(PREFERENCE_STATE_KEY, {"preferences": preferences})
    ensure_internal_state_write_allowed(PREFERENCES_FILE)
    _write_text_atomic(PREFERENCES_FILE, json.dumps({"preferences": preferences}, indent=2))


def _load_durable_json_state(
    state_key: str,
    legacy_path: Path,
    default: dict[str, Any],
) -> dict[str, Any]:
    ensure_agent_storage()
    store = _get_state_store()
    record = store.get_json_state(state_key)
    legacy_value, legacy_mtime = _read_legacy_json_state(legacy_path, default)
    if record is None:
        store.upsert_json_state(state_key, legacy_value)
        return legacy_value

    record_time = _parse_datetime(record.updated_at)
    if legacy_mtime is not None and (record_time is None or legacy_mtime >= record_time):
        store.upsert_json_state(state_key, legacy_value)
        return legacy_value
    return record.value


def _save_durable_json_state(
    state_key: str,
    legacy_path: Path,
    state: dict[str, Any],
) -> None:
    ensure_agent_storage()
    ensure_internal_state_write_allowed(legacy_path)
    _write_text_atomic(legacy_path, json.dumps(state, indent=2))
    _get_state_store().upsert_json_state(state_key, state)


def _read_legacy_json_state(
    path: Path,
    default: dict[str, Any],
) -> tuple[dict[str, Any], datetime | None]:
    ensure_read_allowed(path)
    if not path.exists():
        return _clone_json_dict(default), None
    raw = path.read_text(encoding="utf-8")
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    if not raw.strip():
        return _clone_json_dict(default), mtime
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _clone_json_dict(default), mtime
    if not isinstance(payload, dict):
        return _clone_json_dict(default), mtime
    return payload, mtime


def _parse_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _clone_json_dict(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value))


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


def parse_markdown_section_bullets(path: Path, section_title: str) -> list[str]:
    """Extract bullet items from one markdown section."""
    if not path.exists():
        return []
    ensure_read_allowed(path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    marker = f"## {section_title}"
    inside_section = False
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == marker:
            inside_section = True
            continue
        if inside_section and stripped.startswith("## "):
            break
        if inside_section and stripped.startswith("- "):
            value = stripped[2:].strip()
            if value:
                items.append(value)
    return items


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
