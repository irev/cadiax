"""Persistent agent context utilities."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import os

from otonomassist.storage import SQLiteStateStore
from otonomassist.core.secure_storage import decrypt_secret
from otonomassist.core.workspace_guard import ensure_internal_state_write_allowed, ensure_read_allowed, ensure_workspace_root_exists, ensure_write_allowed, get_workspace_root
from otonomassist.memory import SemanticMemoryService

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("OTONOMASSIST_STATE_DIR", str(PROJECT_ROOT / ".otonomassist"))).expanduser().resolve()
MEMORY_FILE = DATA_DIR / "memory.jsonl"
PLANNER_FILE = DATA_DIR / "planner.json"
PROFILE_FILE = DATA_DIR / "profile.md"
PREFERENCES_FILE = DATA_DIR / "preferences.json"
HABITS_FILE = DATA_DIR / "habits.json"
MEMORY_SUMMARIES_FILE = DATA_DIR / "memory_summaries.json"
EPISODES_FILE = DATA_DIR / "episodes.json"
PROACTIVE_INSIGHTS_FILE = DATA_DIR / "proactive_insights.json"
HEARTBEAT_STATE_FILE = DATA_DIR / "heartbeat.json"
IDENTITIES_FILE = DATA_DIR / "identities.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"
EMAIL_MESSAGES_FILE = DATA_DIR / "email_messages.json"
WHATSAPP_MESSAGES_FILE = DATA_DIR / "whatsapp_messages.json"
PRIVACY_CONTROLS_FILE = DATA_DIR / "privacy_controls.json"
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
HABIT_STATE_KEY = "habits"
MEMORY_SUMMARY_STATE_KEY = "memory_summaries"
EPISODE_STATE_KEY = "episodes"
PROACTIVE_INSIGHT_STATE_KEY = "proactive_insights"
HEARTBEAT_STATE_KEY = "heartbeat"
IDENTITY_STATE_KEY = "identities"
SESSION_STATE_KEY = "sessions"
NOTIFICATION_STATE_KEY = "notifications"
EMAIL_MESSAGE_STATE_KEY = "email_messages"
WHATSAPP_MESSAGE_STATE_KEY = "whatsapp_messages"
PRIVACY_CONTROL_STATE_KEY = "privacy_controls"

DEFAULT_PLANNER_STATE = {"goal": "", "tasks": []}
DEFAULT_METRICS_STATE = {"counters": {}, "timings": {}, "updated_at": ""}
DEFAULT_JOB_QUEUE_STATE = {"jobs": []}
DEFAULT_SCHEDULER_STATE = {
    "last_run_at": "",
    "last_status": "",
    "last_cycles": 0,
    "last_processed": 0,
    "last_heartbeat_mode": "",
}
DEFAULT_PREFERENCE_STATE = {
    "preferences": [],
    "profile": {
        "preferred_channels": [],
        "preferred_brevity": "",
        "formality": "",
        "proactive_mode": "",
        "summary_style": "",
    },
}
DEFAULT_HABIT_STATE = {"habits": [], "updated_at": "", "signals_analyzed": 0}
DEFAULT_MEMORY_SUMMARY_STATE = {"summaries": [], "updated_at": "", "prune_candidates": 0}
DEFAULT_EPISODE_STATE = {"episodes": [], "updated_at": "", "episodes_analyzed": 0}
DEFAULT_PROACTIVE_INSIGHT_STATE = {"insights": [], "updated_at": "", "insights_generated": 0}
DEFAULT_HEARTBEAT_STATE = {
    "pulse_count": 0,
    "last_pulse_at": "",
    "last_mode": "",
    "last_summary": "",
    "last_trigger": "",
    "last_actions": [],
}
DEFAULT_IDENTITY_STATE = {"identities": [], "updated_at": ""}
DEFAULT_SESSION_STATE = {"sessions": [], "updated_at": ""}
DEFAULT_NOTIFICATION_STATE = {"notifications": [], "updated_at": ""}
DEFAULT_EMAIL_MESSAGE_STATE = {"messages": [], "updated_at": ""}
DEFAULT_WHATSAPP_MESSAGE_STATE = {"messages": [], "updated_at": ""}
DEFAULT_PRIVACY_CONTROL_STATE = {
    "quiet_hours": {"enabled": False, "start": "22:00", "end": "07:00"},
    "consent_required_for_proactive": True,
    "proactive_assistance_enabled": True,
    "memory_retention_days": 365,
    "scoped_controls": {},
    "updated_at": "",
}


def ensure_agent_storage() -> None:
    """Ensure persistent agent files exist."""
    workspace_root = get_workspace_root()
    workspace_was_missing = not workspace_root.exists()
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
    if not HABITS_FILE.exists():
        ensure_internal_state_write_allowed(HABITS_FILE)
        HABITS_FILE.write_text(json.dumps(DEFAULT_HABIT_STATE, indent=2), encoding="utf-8")
    if not MEMORY_SUMMARIES_FILE.exists():
        ensure_internal_state_write_allowed(MEMORY_SUMMARIES_FILE)
        MEMORY_SUMMARIES_FILE.write_text(json.dumps(DEFAULT_MEMORY_SUMMARY_STATE, indent=2), encoding="utf-8")
    if not EPISODES_FILE.exists():
        ensure_internal_state_write_allowed(EPISODES_FILE)
        EPISODES_FILE.write_text(json.dumps(DEFAULT_EPISODE_STATE, indent=2), encoding="utf-8")
    if not PROACTIVE_INSIGHTS_FILE.exists():
        ensure_internal_state_write_allowed(PROACTIVE_INSIGHTS_FILE)
        PROACTIVE_INSIGHTS_FILE.write_text(json.dumps(DEFAULT_PROACTIVE_INSIGHT_STATE, indent=2), encoding="utf-8")
    if not HEARTBEAT_STATE_FILE.exists():
        ensure_internal_state_write_allowed(HEARTBEAT_STATE_FILE)
        HEARTBEAT_STATE_FILE.write_text(json.dumps(DEFAULT_HEARTBEAT_STATE, indent=2), encoding="utf-8")
    if not IDENTITIES_FILE.exists():
        ensure_internal_state_write_allowed(IDENTITIES_FILE)
        IDENTITIES_FILE.write_text(json.dumps(DEFAULT_IDENTITY_STATE, indent=2), encoding="utf-8")
    if not SESSIONS_FILE.exists():
        ensure_internal_state_write_allowed(SESSIONS_FILE)
        SESSIONS_FILE.write_text(json.dumps(DEFAULT_SESSION_STATE, indent=2), encoding="utf-8")
    if not NOTIFICATIONS_FILE.exists():
        ensure_internal_state_write_allowed(NOTIFICATIONS_FILE)
        NOTIFICATIONS_FILE.write_text(json.dumps(DEFAULT_NOTIFICATION_STATE, indent=2), encoding="utf-8")
    if not EMAIL_MESSAGES_FILE.exists():
        ensure_internal_state_write_allowed(EMAIL_MESSAGES_FILE)
        EMAIL_MESSAGES_FILE.write_text(json.dumps(DEFAULT_EMAIL_MESSAGE_STATE, indent=2), encoding="utf-8")
    if not WHATSAPP_MESSAGES_FILE.exists():
        ensure_internal_state_write_allowed(WHATSAPP_MESSAGES_FILE)
        WHATSAPP_MESSAGES_FILE.write_text(json.dumps(DEFAULT_WHATSAPP_MESSAGE_STATE, indent=2), encoding="utf-8")
    if not PRIVACY_CONTROLS_FILE.exists():
        ensure_internal_state_write_allowed(PRIVACY_CONTROLS_FILE)
        PRIVACY_CONTROLS_FILE.write_text(json.dumps(DEFAULT_PRIVACY_CONTROL_STATE, indent=2), encoding="utf-8")
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
    if workspace_was_missing:
        from otonomassist.core.workspace_bootstrap import ensure_workspace_skeleton

        ensure_workspace_skeleton(only_if_workspace_empty=True)


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


def load_all_memories() -> list[dict[str, Any]]:
    """Load the full memory journal."""
    return load_recent_memories(limit=10_000)


def replace_memory_entries(entries: list[dict[str, Any]]) -> None:
    """Replace the full memory journal with normalized entries."""
    ensure_agent_storage()
    ensure_internal_state_write_allowed(MEMORY_FILE)
    lines = [json.dumps(entry, ensure_ascii=True) for entry in entries if isinstance(entry, dict)]
    text = "\n".join(lines)
    if text:
        text += "\n"
    _write_text_atomic(MEMORY_FILE, text)


def load_planner_state() -> dict[str, Any]:
    """Load planner state."""
    return _load_durable_json_state(PLANNER_STATE_KEY, PLANNER_FILE, DEFAULT_PLANNER_STATE)


def save_planner_state(state: dict[str, Any]) -> None:
    """Persist planner state."""
    _save_durable_json_state(PLANNER_STATE_KEY, PLANNER_FILE, state)


def load_identity_state() -> dict[str, Any]:
    """Load canonical identity mapping state."""
    return _load_durable_json_state(IDENTITY_STATE_KEY, IDENTITIES_FILE, DEFAULT_IDENTITY_STATE)


def save_identity_state(state: dict[str, Any]) -> None:
    """Persist canonical identity mapping state."""
    _save_durable_json_state(IDENTITY_STATE_KEY, IDENTITIES_FILE, state)


def load_session_state() -> dict[str, Any]:
    """Load canonical cross-channel session state."""
    return _load_durable_json_state(SESSION_STATE_KEY, SESSIONS_FILE, DEFAULT_SESSION_STATE)


def save_session_state(state: dict[str, Any]) -> None:
    """Persist canonical cross-channel session state."""
    _save_durable_json_state(SESSION_STATE_KEY, SESSIONS_FILE, state)


def load_notification_state() -> dict[str, Any]:
    """Load notification dispatch state."""
    return _load_durable_json_state(NOTIFICATION_STATE_KEY, NOTIFICATIONS_FILE, DEFAULT_NOTIFICATION_STATE)


def save_notification_state(state: dict[str, Any]) -> None:
    """Persist notification dispatch state."""
    _save_durable_json_state(NOTIFICATION_STATE_KEY, NOTIFICATIONS_FILE, state)


def load_email_message_state() -> dict[str, Any]:
    """Load email interface message history state."""
    return _load_durable_json_state(
        EMAIL_MESSAGE_STATE_KEY,
        EMAIL_MESSAGES_FILE,
        DEFAULT_EMAIL_MESSAGE_STATE,
    )


def save_email_message_state(state: dict[str, Any]) -> None:
    """Persist email interface message history state."""
    _save_durable_json_state(EMAIL_MESSAGE_STATE_KEY, EMAIL_MESSAGES_FILE, state)


def load_whatsapp_message_state() -> dict[str, Any]:
    """Load WhatsApp interface message history state."""
    return _load_durable_json_state(
        WHATSAPP_MESSAGE_STATE_KEY,
        WHATSAPP_MESSAGES_FILE,
        DEFAULT_WHATSAPP_MESSAGE_STATE,
    )


def save_whatsapp_message_state(state: dict[str, Any]) -> None:
    """Persist WhatsApp interface message history state."""
    _save_durable_json_state(
        WHATSAPP_MESSAGE_STATE_KEY,
        WHATSAPP_MESSAGES_FILE,
        state,
    )


def load_privacy_control_state() -> dict[str, Any]:
    """Load privacy governance and quiet-hours controls."""
    return _load_durable_json_state(
        PRIVACY_CONTROL_STATE_KEY,
        PRIVACY_CONTROLS_FILE,
        DEFAULT_PRIVACY_CONTROL_STATE,
    )


def save_privacy_control_state(state: dict[str, Any]) -> None:
    """Persist privacy governance and quiet-hours controls."""
    quiet_hours = state.get("quiet_hours", {})
    raw_scoped = state.get("scoped_controls", {})
    scoped_controls: dict[str, Any] = {}
    if isinstance(raw_scoped, dict):
        for raw_scope, raw_payload in raw_scoped.items():
            if not isinstance(raw_payload, dict):
                continue
            scoped_controls[str(raw_scope).strip()] = {
                "proactive_assistance_enabled": bool(
                    raw_payload.get("proactive_assistance_enabled", True)
                ),
                "consent_required_for_proactive": bool(
                    raw_payload.get("consent_required_for_proactive", True)
                ),
                "allowed_roles": [
                    str(item).strip().lower()
                    for item in list(raw_payload.get("allowed_roles", []))
                    if str(item).strip()
                ],
                "updated_at": str(raw_payload.get("updated_at", "")),
            }
    normalized = {
        "quiet_hours": {
            "enabled": bool(quiet_hours.get("enabled", False)),
            "start": str(quiet_hours.get("start", "22:00") or "22:00"),
            "end": str(quiet_hours.get("end", "07:00") or "07:00"),
        },
        "consent_required_for_proactive": bool(state.get("consent_required_for_proactive", True)),
        "proactive_assistance_enabled": bool(state.get("proactive_assistance_enabled", True)),
        "memory_retention_days": int(state.get("memory_retention_days", 365) or 365),
        "scoped_controls": scoped_controls,
        "updated_at": str(state.get("updated_at", "")),
    }
    _save_durable_json_state(
        PRIVACY_CONTROL_STATE_KEY,
        PRIVACY_CONTROLS_FILE,
        normalized,
    )


def load_episode_state() -> dict[str, Any]:
    """Load durable episodic learning state."""
    return _load_durable_json_state(
        EPISODE_STATE_KEY,
        EPISODES_FILE,
        DEFAULT_EPISODE_STATE,
    )


def save_episode_state(state: dict[str, Any]) -> None:
    """Persist durable episodic learning state."""
    normalized = {
        "episodes": list(state.get("episodes", [])),
        "updated_at": str(state.get("updated_at", "")),
        "episodes_analyzed": int(state.get("episodes_analyzed", 0) or 0),
    }
    _save_durable_json_state(EPISODE_STATE_KEY, EPISODES_FILE, normalized)


def load_proactive_insight_state() -> dict[str, Any]:
    """Load durable proactive assistance insight state."""
    return _load_durable_json_state(
        PROACTIVE_INSIGHT_STATE_KEY,
        PROACTIVE_INSIGHTS_FILE,
        DEFAULT_PROACTIVE_INSIGHT_STATE,
    )


def save_proactive_insight_state(state: dict[str, Any]) -> None:
    """Persist durable proactive assistance insight state."""
    normalized = {
        "insights": list(state.get("insights", [])),
        "updated_at": str(state.get("updated_at", "")),
        "insights_generated": int(state.get("insights_generated", 0) or 0),
    }
    _save_durable_json_state(PROACTIVE_INSIGHT_STATE_KEY, PROACTIVE_INSIGHTS_FILE, normalized)


def load_heartbeat_state() -> dict[str, Any]:
    """Load current heartbeat state."""
    return _load_durable_json_state(
        HEARTBEAT_STATE_KEY,
        HEARTBEAT_STATE_FILE,
        DEFAULT_HEARTBEAT_STATE,
    )


def save_heartbeat_state(state: dict[str, Any]) -> None:
    """Persist heartbeat state."""
    normalized = {
        "pulse_count": int(state.get("pulse_count", 0) or 0),
        "last_pulse_at": str(state.get("last_pulse_at", "") or ""),
        "last_mode": str(state.get("last_mode", "") or ""),
        "last_summary": str(state.get("last_summary", "") or ""),
        "last_trigger": str(state.get("last_trigger", "") or ""),
        "last_actions": [str(item) for item in list(state.get("last_actions", []))[:6]],
    }
    _save_durable_json_state(HEARTBEAT_STATE_KEY, HEARTBEAT_STATE_FILE, normalized)


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


def build_runtime_context_block(query: str | None = None, *, session_mode: str = "main") -> str:
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

    normalized_session_mode = str(session_mode or "main").strip().lower()
    parts.extend(["", "## Daily Journal"])
    daily_notes = load_recent_workspace_daily_notes(days=2, max_chars=1200)
    parts.append(daily_notes or "- belum ada daily journal workspace")
    parts.extend(["", "## Session Memory Boundary"])
    parts.append(f"- session_mode: {normalized_session_mode}")
    if normalized_session_mode == "main":
        parts.extend(["", "## Curated Memory"])
        curated_memory = load_workspace_curated_memory(max_chars=1200)
        parts.append(curated_memory or "- belum ada curated memory workspace")
    else:
        parts.extend(["", "## Curated Memory"])
        parts.append("- tidak dimuat pada shared session")

    memories = retrieve_relevant_memories(query, limit=5) if query and query.strip() else load_recent_memories(limit=5)
    parts.extend(["", "## Relevant Memories" if query and query.strip() else "## Recent Memories"])
    if memories:
        for entry in memories:
            parts.append(f"- #{entry.get('id')}: {entry.get('text', '')}")
    else:
        parts.append("- tidak ada memori relevan" if query and query.strip() else "- belum ada memori")

    return "\n".join(parts)


def load_workspace_curated_memory(max_chars: int = 1600) -> str:
    """Load workspace curated long-term memory when present."""
    ensure_agent_storage()
    memory_file = get_workspace_root() / "MEMORY.md"
    if not memory_file.exists():
        return ""
    return load_markdown(memory_file, max_chars=max_chars)


def get_daily_memory_dir() -> Path:
    """Return the workspace directory for daily memory journals."""
    return get_workspace_root() / "memory"


def get_daily_memory_journal_path(day: date | None = None) -> Path:
    """Return the workspace path for one daily memory journal file."""
    target_day = day or datetime.now(timezone.utc).date()
    return get_daily_memory_dir() / f"{target_day.isoformat()}.md"


def get_workspace_heartbeat_state_path() -> Path:
    """Return the workspace path for projected heartbeat state."""
    return get_daily_memory_dir() / "heartbeat-state.json"


def append_daily_memory_note(
    text: str,
    source: str = "manual",
    *,
    session_mode: str = "main",
    agent_scope: str = "default",
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Project one operational memory note into the workspace daily journal."""
    ensure_agent_storage()
    moment = timestamp or datetime.now(timezone.utc)
    journal_path = get_daily_memory_journal_path(moment.date())
    payload = {
        "path": str(journal_path),
        "written": False,
        "session_mode": str(session_mode or "main").strip().lower() or "main",
        "agent_scope": str(agent_scope or "default").strip().lower() or "default",
    }
    try:
        journal_dir = get_daily_memory_dir()
        ensure_write_allowed(journal_dir)
        journal_dir.mkdir(parents=True, exist_ok=True)
        if not journal_path.exists():
            ensure_write_allowed(journal_path)
            journal_path.write_text(
                f"# Daily Memory {moment.date().isoformat()}\n\n",
                encoding="utf-8",
            )
        ensure_read_allowed(journal_path)
        content = journal_path.read_text(encoding="utf-8", errors="replace").rstrip()
        line = (
            f"- {moment.astimezone(timezone.utc).strftime('%H:%M:%S')} "
            f"[{payload['session_mode']}|{payload['agent_scope']}|{source}]: {text}"
        )
        ensure_write_allowed(journal_path)
        journal_path.write_text(f"{content}\n{line}\n", encoding="utf-8")
        payload["written"] = True
    except PermissionError:
        payload["written"] = False
    return payload


def load_recent_workspace_daily_notes(days: int = 2, max_chars: int = 1600) -> str:
    """Load recent workspace daily memory journals for session startup context."""
    ensure_agent_storage()
    snippets: list[str] = []
    today = datetime.now(timezone.utc).date()
    for offset in range(max(1, days)):
        journal_path = get_daily_memory_journal_path(today - timedelta(days=offset))
        if not journal_path.exists():
            continue
        ensure_read_allowed(journal_path)
        text = journal_path.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            snippets.append(text)
    combined = "\n\n".join(reversed(snippets))
    if len(combined) <= max_chars:
        return combined
    return combined[:max_chars].rstrip() + "\n... (truncated)"


def project_workspace_heartbeat_state(state: dict[str, Any]) -> dict[str, Any]:
    """Project heartbeat state into a workspace-readable JSON file when writable."""
    ensure_agent_storage()
    path = get_workspace_heartbeat_state_path()
    payload = {"path": str(path), "written": False}
    try:
        directory = get_daily_memory_dir()
        ensure_write_allowed(directory)
        directory.mkdir(parents=True, exist_ok=True)
        ensure_write_allowed(path)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["written"] = True
    except PermissionError:
        payload["written"] = False
    return payload


def append_memory_entry(
    text: str,
    source: str = "manual",
    *,
    session_mode: str = "main",
    agent_scope: str = "default",
) -> dict[str, Any]:
    """Append a memory entry and return it."""
    ensure_agent_storage()
    entries = load_recent_memories(limit=10_000)
    entry = {
        "id": len(entries) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "session_mode": str(session_mode or "main").strip().lower() or "main",
        "agent_scope": str(agent_scope or "default").strip().lower() or "default",
        "text": text,
    }
    ensure_internal_state_write_allowed(MEMORY_FILE)
    with MEMORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
    journal = append_daily_memory_note(
        text,
        source=source,
        session_mode=entry["session_mode"],
        agent_scope=entry["agent_scope"],
        timestamp=datetime.fromisoformat(entry["timestamp"]),
    )
    entry["daily_journal_path"] = journal["path"]
    entry["daily_journal_written"] = journal["written"]
    return entry


def append_curated_memory(text: str, source: str = "manual", *, session_mode: str = "main", agent_scope: str = "default") -> dict[str, Any]:
    """Append one curated long-term memory note in the workspace."""
    ensure_agent_storage()
    normalized_mode = str(session_mode or "main").strip().lower() or "main"
    if normalized_mode != "main":
        raise PermissionError("Curated memory hanya boleh ditulis dari main session.")
    memory_file = get_workspace_root() / "MEMORY.md"
    if not memory_file.exists():
        ensure_write_allowed(memory_file)
        memory_file.write_text("# Memory\n\n", encoding="utf-8")
    ensure_read_allowed(memory_file)
    content = memory_file.read_text(encoding="utf-8", errors="replace").rstrip()
    stamp = datetime.now(timezone.utc).date().isoformat()
    bullet = f"- {stamp} [{str(agent_scope or 'default').strip().lower() or 'default'}|{source}]: {text}"
    recent_lines = [line.strip() for line in content.splitlines()[-20:] if line.strip()]
    if bullet not in recent_lines:
        ensure_write_allowed(memory_file)
        memory_file.write_text(f"{content}\n{bullet}\n", encoding="utf-8")
    return {
        "path": str(memory_file),
        "session_mode": normalized_mode,
        "agent_scope": str(agent_scope or "default").strip().lower() or "default",
        "text": text,
        "source": source,
    }


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
    """Retrieve memory entries via semantic ranking service."""
    return SemanticMemoryService().retrieve(
        load_recent_memories(limit=10_000),
        query,
        limit=limit,
    )


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
    normalized = _normalize_preference_state(state)
    if normalized.get("preferences"):
        return normalized
    preferences = parse_markdown_section_bullets(PROFILE_FILE, "Preferences")
    if preferences:
        normalized["preferences"] = preferences
        state = normalized
        save_preference_state(state)
        return state
    return normalized


def save_preference_state(state: dict[str, Any]) -> None:
    """Persist structured personality preferences."""
    normalized = _normalize_preference_state(state)
    _save_durable_json_state(PREFERENCE_STATE_KEY, PREFERENCES_FILE, normalized)


def load_habit_state() -> dict[str, Any]:
    """Load structured habit model state."""
    return _load_durable_json_state(HABIT_STATE_KEY, HABITS_FILE, DEFAULT_HABIT_STATE)


def save_habit_state(state: dict[str, Any]) -> None:
    """Persist structured habit model state."""
    normalized = {
        "habits": list(state.get("habits", [])),
        "updated_at": str(state.get("updated_at", "")),
        "signals_analyzed": int(state.get("signals_analyzed", 0) or 0),
    }
    _save_durable_json_state(HABIT_STATE_KEY, HABITS_FILE, normalized)


def load_memory_summary_state() -> dict[str, Any]:
    """Load durable memory summary/pruning state."""
    return _load_durable_json_state(MEMORY_SUMMARY_STATE_KEY, MEMORY_SUMMARIES_FILE, DEFAULT_MEMORY_SUMMARY_STATE)


def save_memory_summary_state(state: dict[str, Any]) -> None:
    """Persist durable memory summary/pruning state."""
    normalized = {
        "summaries": list(state.get("summaries", [])),
        "updated_at": str(state.get("updated_at", "")),
        "prune_candidates": int(state.get("prune_candidates", 0) or 0),
    }
    _save_durable_json_state(MEMORY_SUMMARY_STATE_KEY, MEMORY_SUMMARIES_FILE, normalized)


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


def get_preference_profile() -> dict[str, Any]:
    """Return normalized structured preference profile fields."""
    return dict(load_preference_state().get("profile", {}))


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
    _ensure_state_in_store(store, HABIT_STATE_KEY, HABITS_FILE, DEFAULT_HABIT_STATE)
    _ensure_state_in_store(store, MEMORY_SUMMARY_STATE_KEY, MEMORY_SUMMARIES_FILE, DEFAULT_MEMORY_SUMMARY_STATE)
    _ensure_state_in_store(store, EPISODE_STATE_KEY, EPISODES_FILE, DEFAULT_EPISODE_STATE)
    _ensure_state_in_store(store, PROACTIVE_INSIGHT_STATE_KEY, PROACTIVE_INSIGHTS_FILE, DEFAULT_PROACTIVE_INSIGHT_STATE)
    _ensure_state_in_store(store, HEARTBEAT_STATE_KEY, HEARTBEAT_STATE_FILE, DEFAULT_HEARTBEAT_STATE)
    _ensure_state_in_store(store, IDENTITY_STATE_KEY, IDENTITIES_FILE, DEFAULT_IDENTITY_STATE)
    _ensure_state_in_store(store, SESSION_STATE_KEY, SESSIONS_FILE, DEFAULT_SESSION_STATE)
    _ensure_state_in_store(store, NOTIFICATION_STATE_KEY, NOTIFICATIONS_FILE, DEFAULT_NOTIFICATION_STATE)
    _ensure_state_in_store(store, EMAIL_MESSAGE_STATE_KEY, EMAIL_MESSAGES_FILE, DEFAULT_EMAIL_MESSAGE_STATE)
    _ensure_state_in_store(store, WHATSAPP_MESSAGE_STATE_KEY, WHATSAPP_MESSAGES_FILE, DEFAULT_WHATSAPP_MESSAGE_STATE)
    _ensure_state_in_store(store, PRIVACY_CONTROL_STATE_KEY, PRIVACY_CONTROLS_FILE, DEFAULT_PRIVACY_CONTROL_STATE)
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
    if record is not None:
        normalized_record = _normalize_preference_state(record.value)
        if normalized_record.get("preferences") or any(normalized_record.get("profile", {}).values()):
            store.upsert_json_state(PREFERENCE_STATE_KEY, normalized_record)
            serialized = json.dumps(normalized_record, indent=2)
            existing_text = ""
            if PREFERENCES_FILE.exists():
                ensure_read_allowed(PREFERENCES_FILE)
                existing_text = PREFERENCES_FILE.read_text(encoding="utf-8", errors="replace")
            if existing_text.strip() != serialized.strip():
                ensure_internal_state_write_allowed(PREFERENCES_FILE)
                _write_text_atomic(PREFERENCES_FILE, serialized)
            return
    legacy_value, _ = _read_legacy_json_state(PREFERENCES_FILE, DEFAULT_PREFERENCE_STATE)
    preferences = [
        str(item).strip()
        for item in legacy_value.get("preferences", [])
        if str(item).strip()
    ]
    normalized = _normalize_preference_state(legacy_value)
    if not preferences:
        preferences = parse_markdown_section_bullets(PROFILE_FILE, "Preferences")
    normalized["preferences"] = preferences
    store.upsert_json_state(PREFERENCE_STATE_KEY, normalized)
    ensure_internal_state_write_allowed(PREFERENCES_FILE)
    _write_text_atomic(PREFERENCES_FILE, json.dumps(normalized, indent=2))


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


def _normalize_preference_state(state: dict[str, Any]) -> dict[str, Any]:
    profile = state.get("profile", {}) if isinstance(state.get("profile"), dict) else {}
    return {
        "preferences": [
            str(item).strip()
            for item in state.get("preferences", [])
            if str(item).strip()
        ],
        "profile": {
            "preferred_channels": [
                str(item).strip()
                for item in profile.get("preferred_channels", [])
                if str(item).strip()
            ],
            "preferred_brevity": str(profile.get("preferred_brevity", "") or "").strip(),
            "formality": str(profile.get("formality", "") or "").strip(),
            "proactive_mode": str(profile.get("proactive_mode", "") or "").strip(),
            "summary_style": str(profile.get("summary_style", "") or "").strip(),
        },
    }


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
