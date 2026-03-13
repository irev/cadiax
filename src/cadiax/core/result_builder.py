"""Helpers for building structured result envelopes."""

from __future__ import annotations

from typing import Any


def build_result(
    result_type: str,
    data: dict[str, Any],
    *,
    source_skill: str,
    default_view: str = "json",
    status: str = "ok",
    **meta: Any,
) -> dict[str, Any]:
    """Build a shared structured-result envelope."""
    payload = {
        "type": result_type,
        "status": status,
        "data": data,
        "meta": {
            "source_skill": source_skill,
            "default_view": default_view,
        },
    }
    payload["meta"].update(meta)
    return payload
