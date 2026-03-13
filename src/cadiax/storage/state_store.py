"""SQLite-backed durable store for runtime state and execution events."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class JsonStateRecord:
    """One JSON state document stored in SQLite."""

    key: str
    value: dict[str, Any]
    updated_at: str


class SQLiteStateStore:
    """Minimal durable storage for JSON state documents and execution events."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def ensure_initialized(self) -> None:
        """Create the SQLite database and required tables if missing."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS json_state (
                    state_key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    command TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    duration_ms INTEGER,
                    data_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS event_bus_events (
                    bus_event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    data_json TEXT NOT NULL
                )
                """
            )

    def get_json_state(self, key: str) -> JsonStateRecord | None:
        """Load one JSON state document by key."""
        self.ensure_initialized()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT state_key, value_json, updated_at
                FROM json_state
                WHERE state_key = ?
                """,
                (key,),
            ).fetchone()
        if row is None:
            return None
        return JsonStateRecord(
            key=str(row["state_key"]),
            value=_decode_json_dict(str(row["value_json"])),
            updated_at=str(row["updated_at"]),
        )

    def upsert_json_state(
        self,
        key: str,
        value: dict[str, Any],
        *,
        updated_at: str | None = None,
    ) -> JsonStateRecord:
        """Insert or replace one JSON state document."""
        self.ensure_initialized()
        stamp = updated_at or _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO json_state (state_key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE
                SET value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, json.dumps(value, ensure_ascii=False, indent=2), stamp),
            )
        return JsonStateRecord(key=key, value=value, updated_at=stamp)

    def count_execution_events(self) -> int:
        """Return the number of execution events persisted in SQLite."""
        self.ensure_initialized()
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM execution_events").fetchone()
        return int(row["total"] if row is not None else 0)

    def append_execution_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Persist one execution event."""
        self.ensure_initialized()
        payload = dict(event)
        data = payload.get("data") or {}
        if not isinstance(data, dict):
            data = {"value": data}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO execution_events (
                    event_id,
                    timestamp,
                    trace_id,
                    event_type,
                    status,
                    source,
                    command,
                    skill_name,
                    duration_ms,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(payload.get("event_id") or ""),
                    str(payload.get("timestamp") or _utc_now_iso()),
                    str(payload.get("trace_id") or ""),
                    str(payload.get("event_type") or ""),
                    str(payload.get("status") or ""),
                    str(payload.get("source") or ""),
                    str(payload.get("command") or ""),
                    str(payload.get("skill_name") or ""),
                    payload.get("duration_ms"),
                    json.dumps(data, ensure_ascii=False, sort_keys=True),
                ),
            )
        payload["data"] = data
        return payload

    def load_execution_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """Load the most recent execution events from SQLite."""
        self.ensure_initialized()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    event_id,
                    timestamp,
                    trace_id,
                    event_type,
                    status,
                    source,
                    command,
                    skill_name,
                    duration_ms,
                    data_json
                FROM execution_events
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (max(1, int(limit or 1)),),
            ).fetchall()
        rows = list(reversed(rows))
        return [
            {
                "event_id": str(row["event_id"]),
                "timestamp": str(row["timestamp"]),
                "trace_id": str(row["trace_id"]),
                "event_type": str(row["event_type"]),
                "status": str(row["status"]),
                "source": str(row["source"]),
                "command": str(row["command"]),
                "skill_name": str(row["skill_name"]),
                "duration_ms": row["duration_ms"],
                "data": _decode_json_dict(str(row["data_json"])),
            }
            for row in rows
        ]

    def count_event_bus_events(self) -> int:
        """Return the number of internal event bus entries."""
        self.ensure_initialized()
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM event_bus_events").fetchone()
        return int(row["total"] if row is not None else 0)

    def append_event_bus_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Persist one event bus entry."""
        self.ensure_initialized()
        payload = dict(event)
        data = payload.get("data") or {}
        if not isinstance(data, dict):
            data = {"value": data}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO event_bus_events (
                    bus_event_id,
                    timestamp,
                    topic,
                    event_type,
                    trace_id,
                    source,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(payload.get("bus_event_id") or ""),
                    str(payload.get("timestamp") or _utc_now_iso()),
                    str(payload.get("topic") or ""),
                    str(payload.get("event_type") or ""),
                    str(payload.get("trace_id") or ""),
                    str(payload.get("source") or ""),
                    json.dumps(data, ensure_ascii=False, sort_keys=True),
                ),
            )
        payload["data"] = data
        return payload

    def load_event_bus_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """Load recent event bus entries from SQLite."""
        self.ensure_initialized()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    bus_event_id,
                    timestamp,
                    topic,
                    event_type,
                    trace_id,
                    source,
                    data_json
                FROM event_bus_events
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (max(1, int(limit or 1)),),
            ).fetchall()
        rows = list(reversed(rows))
        return [
            {
                "bus_event_id": str(row["bus_event_id"]),
                "timestamp": str(row["timestamp"]),
                "topic": str(row["topic"]),
                "event_type": str(row["event_type"]),
                "trace_id": str(row["trace_id"]),
                "source": str(row["source"]),
                "data": _decode_json_dict(str(row["data_json"])),
            }
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn


def _decode_json_dict(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
