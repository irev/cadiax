"""Lightweight semantic retrieval and consolidation for local memory."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{3,}")
SEMANTIC_ALIASES = {
    "anggaran": "budget",
    "biaya": "cost",
    "dependensi": "dependency",
    "jadwal": "schedule",
    "kebiasaan": "habit",
    "memori": "memory",
    "otomasi": "automation",
    "preferensi": "preference",
    "ringkasan": "summary",
}


class SemanticMemoryService:
    """Rank memory entries using lexical overlap, alias expansion, and fuzzy similarity."""

    def retrieve(
        self,
        entries: list[dict[str, Any]],
        query: str,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        normalized = _normalize_terms(query)
        if not normalized:
            return entries[-limit:]

        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in entries:
            text = str(entry.get("text", ""))
            tokens = _normalize_terms(text)
            if not tokens:
                continue

            overlap = len(normalized.intersection(tokens))
            trigram_similarity = _trigram_similarity(" ".join(sorted(normalized)), " ".join(sorted(tokens)))
            exact_phrase_bonus = 1.5 if query.strip().lower() in text.lower() else 0.0
            recency_bonus = min(int(entry.get("id", 0) or 0) / 10_000.0, 0.25)
            score = overlap * 1.8 + trigram_similarity + exact_phrase_bonus + recency_bonus
            if score <= 0:
                continue
            scored.append((score, entry))

        return [
            entry
            for _, entry in sorted(
                scored,
                key=lambda item: (-item[0], -int(item[1].get("id", 0) or 0)),
            )[: max(1, limit)]
        ]


class MemoryConsolidationService:
    """Produce compact lesson summaries from memory entries."""

    def summarize_collection(
        self,
        entries: list[dict[str, Any]],
        *,
        chunk_size: int = 5,
        max_chunks: int = 6,
        retain_recent_entries: int = 10,
    ) -> dict[str, Any]:
        """Build durable rolling summaries and prune hints for a memory collection."""
        selected = [entry for entry in entries if str(entry.get("text", "")).strip()]
        chunks = [
            selected[index : index + max(1, chunk_size)]
            for index in range(0, len(selected), max(1, chunk_size))
        ]
        rendered: list[dict[str, Any]] = []
        for chunk_index, chunk in enumerate(chunks[-max(1, max_chunks):], start=max(1, len(chunks) - max_chunks + 1)):
            summary = self.summarize(chunk)
            if not summary:
                continue
            rendered.append(
                {
                    "chunk_index": chunk_index,
                    "entry_ids": [int(item.get("id", 0) or 0) for item in chunk],
                    "entry_count": len(chunk),
                    "summary": summary,
                }
            )
        prune_candidates = max(0, len(selected) - max(1, retain_recent_entries))
        return {
            "summaries": rendered,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "prune_candidates": prune_candidates,
        }

    def summarize(self, entries: list[dict[str, Any]], *, topic: str = "") -> str:
        selected = [
            entry for entry in entries
            if not topic or topic.lower() in str(entry.get("text", "")).lower()
        ]
        if not selected:
            return ""

        recent = selected[-5:]
        tokens = Counter()
        for entry in recent:
            tokens.update(_normalize_terms(str(entry.get("text", ""))))
        top_terms = [term for term, _ in tokens.most_common(4)]
        highlights = "; ".join(str(entry.get("text", "")).strip() for entry in recent[:3] if str(entry.get("text", "")).strip())

        parts = []
        if topic:
            parts.append(f"topic={topic}")
        if top_terms:
            parts.append("terms=" + ", ".join(top_terms))
        if highlights:
            parts.append("highlights=" + highlights)
        return "memory consolidation: " + " | ".join(parts)


def _normalize_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for token in TOKEN_PATTERN.findall(str(text).lower()):
        terms.add(token)
        if token.endswith("s") and len(token) > 4:
            terms.add(token[:-1])
        alias = SEMANTIC_ALIASES.get(token)
        if alias:
            terms.add(alias)
    return terms


def _trigram_similarity(left: str, right: str) -> float:
    left_grams = _trigrams(left)
    right_grams = _trigrams(right)
    if not left_grams or not right_grams:
        return 0.0
    overlap = len(left_grams.intersection(right_grams))
    union = len(left_grams.union(right_grams))
    return overlap / max(1, union)


def _trigrams(text: str) -> set[str]:
    compact = f"  {text.strip().lower()}  "
    if len(compact.strip()) < 3:
        return set()
    return {compact[index : index + 3] for index in range(len(compact) - 2)}
