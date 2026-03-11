"""Memory skill handler."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import re
from typing import Any

from otonomassist.core.agent_context import (
    LESSONS_FILE,
    append_lesson,
    append_memory_entry,
    ensure_agent_storage,
    load_memory_summary_state,
    save_memory_summary_state,
    retrieve_relevant_memories,
)
from otonomassist.memory import MemoryConsolidationService
from otonomassist.core.result_builder import build_result

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / ".otonomassist"
MEMORY_FILE = DATA_DIR / "memory.jsonl"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{4,}")


def handle(args: str) -> str:
    """Manage local agent memory."""
    args = args.strip()
    if not args:
        return _usage()

    command, _, remainder = args.partition(" ")
    command = command.lower().strip()
    remainder = remainder.strip()

    if command in {"add", "remember"}:
        return _add_memory(remainder)
    if command == "list":
        return _list_memories(remainder)
    if command == "search":
        return _search_memories(remainder)
    if command == "get":
        return _get_memory(remainder)
    if command in {"summarize", "summary"}:
        return _summarize_memories()
    if command == "consolidate":
        return _consolidate_memories(remainder)
    if command == "context":
        return _memory_context()

    return _add_memory(args)


def _usage() -> str:
    return (
        "Usage: memory <add|list|search|get|summarize|consolidate|context> ...\n"
        "Examples:\n"
        "- memory add private ai harus fokus lokal\n"
        "- memory search planner\n"
        "- memory summarize\n"
        "- memory consolidate"
    )


def _ensure_storage() -> None:
    ensure_agent_storage()


def _load_memories() -> list[dict[str, Any]]:
    _ensure_storage()
    entries: list[dict[str, Any]] = []
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _append_memory(entry: dict[str, Any]) -> None:
    _ensure_storage()
    with MEMORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")


def _add_memory(text: str) -> str:
    if not text:
        return "Memory add membutuhkan isi memori."

    entry = append_memory_entry(text, source="memory-skill")
    message = f"Memory #{entry['id']} tersimpan."
    if entry["id"] % 5 == 0:
        _consolidate_recent_entries(entries_to_merge=5)
        message += " Auto-consolidation dijalankan."
    return message


def _list_memories(limit_text: str) -> str:
    entries = _load_memories()
    if not entries:
        return "Belum ada memori tersimpan."

    limit = 10
    if limit_text:
        try:
            limit = max(1, int(limit_text))
        except ValueError:
            pass

    selected = entries[-limit:]
    return _wrap_result(
        result_type="memory_list",
        data={
            "total_entries": len(entries),
            "returned_entries": len(selected),
            "entries": [_memory_row(entry) for entry in selected],
            "summary": f"Menampilkan {len(selected)} memory terbaru dari total {len(entries)} entry.",
        },
        default_view="table",
    )


def _search_memories(query: str) -> str:
    if not query:
        return "Memory search membutuhkan query."

    exact_matches = [
        entry for entry in _load_memories()
        if query.lower() in entry.get("text", "").lower()
    ]
    semantic_matches = retrieve_relevant_memories(query, limit=10)
    combined: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for entry in exact_matches + semantic_matches:
        entry_id = int(entry.get("id", 0) or 0)
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        combined.append(entry)
    matches = combined
    if not matches:
        return f"Tidak ada memori yang cocok untuk '{query}'."

    selected = matches[:10]
    return _wrap_result(
        result_type="memory_search",
        data={
            "query": query,
            "match_count": len(matches),
            "returned_entries": len(selected),
            "retrieval_mode": "hybrid_semantic_recency",
            "entries": [_memory_row(entry) for entry in selected],
            "summary": f"Ditemukan {len(matches)} memory yang cocok untuk '{query}'.",
        },
        default_view="table",
    )


def _get_memory(id_text: str) -> str:
    if not id_text:
        return "Memory get membutuhkan id."

    try:
        memory_id = int(id_text)
    except ValueError:
        return "ID memory harus berupa angka."

    for entry in _load_memories():
        if entry.get("id") == memory_id:
            return _wrap_result(
                result_type="memory_get",
                data={
                    "entry": _memory_row(entry),
                    "summary": f"Memory #{entry['id']} ditemukan.",
                },
                default_view="summary",
            )

    return f"Memory #{memory_id} tidak ditemukan."


def _summarize_memories() -> str:
    entries = _load_memories()
    if not entries:
        return "Belum ada memori untuk diringkas."

    tokens = Counter()
    for entry in entries:
        tokens.update(token.lower() for token in TOKEN_PATTERN.findall(entry.get("text", "")))

    top_terms: list[str] = []
    if tokens:
        top_terms = [term for term, _ in tokens.most_common(5)]

    recent_entries = [_memory_row(entry) for entry in entries[-3:]]
    summary_state = MemoryConsolidationService().summarize_collection(entries)
    save_memory_summary_state(summary_state)
    return _wrap_result(
        result_type="memory_summary",
        data={
            "total_entries": len(entries),
            "last_entry_id": entries[-1]["id"],
            "top_terms": top_terms,
            "recent_entries": recent_entries,
            "summary_chunks": summary_state.get("summaries", []),
            "prune_candidates": summary_state.get("prune_candidates", 0),
            "summary": (
                f"Memory berisi {len(entries)} entry"
                + (f"; top terms: {', '.join(top_terms)}." if top_terms else ".")
            ),
        },
        default_view="summary",
    )


def _consolidate_memories(topic: str) -> str:
    entries = _load_memories()
    if not entries:
        return "Belum ada memori untuk dikonsolidasikan."

    selected = entries
    if topic:
        topic_lower = topic.lower()
        selected = [
            entry for entry in entries
            if topic_lower in entry.get("text", "").lower()
        ]
        if not selected:
            return f"Tidak ada memori bertopik '{topic}' untuk dikonsolidasikan."

    recent = selected[-5:]
    summary = MemoryConsolidationService().summarize(recent, topic=topic)
    append_lesson(summary or "memory consolidation: tidak ada ringkasan")
    summary_state = MemoryConsolidationService().summarize_collection(selected)
    save_memory_summary_state(summary_state)
    return f"{len(recent)} memori dikonsolidasikan ke lessons.md."


def _memory_context() -> str:
    return _wrap_result(
        result_type="memory_context",
        data={
            "files": [
                {"name": "jsonl", "path": str(MEMORY_FILE.relative_to(PROJECT_ROOT))},
                {"name": "lessons", "path": str(LESSONS_FILE.relative_to(PROJECT_ROOT))},
            ],
            "summary_state": load_memory_summary_state(),
            "summary": "Lokasi file memory agent.",
        },
        default_view="table",
    )


def _consolidate_recent_entries(entries_to_merge: int) -> None:
    entries = _load_memories()
    if not entries:
        return
    recent = entries[-entries_to_merge:]
    summary = MemoryConsolidationService().summarize(recent)
    append_lesson(summary or "memory consolidation: tidak ada ringkasan")
    save_memory_summary_state(MemoryConsolidationService().summarize_collection(entries))


def _memory_row(entry: dict[str, Any]) -> dict[str, object]:
    """Normalize a memory entry row for presentation."""
    return {
        "id": entry.get("id"),
        "timestamp": entry.get("timestamp", "-"),
        "source": entry.get("source", "-"),
        "text": entry.get("text", ""),
    }


def _wrap_result(result_type: str, data: dict[str, object], default_view: str) -> dict[str, object]:
    """Wrap memory output into the shared structured-result envelope."""
    return build_result(
        result_type,
        data,
        source_skill="memory",
        default_view=default_view,
    )
