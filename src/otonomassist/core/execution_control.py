"""Execution timeout and result classification helpers."""

from __future__ import annotations

import concurrent.futures
import os
from typing import Any, Callable


DEFAULT_SKILL_TIMEOUT_SECONDS = 60.0


def get_skill_timeout_seconds() -> float:
    """Return the configured skill timeout in seconds."""
    raw = os.getenv("OTONOMASSIST_SKILL_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_SKILL_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_SKILL_TIMEOUT_SECONDS
    return max(0.0, value)


def run_with_timeout(
    fn: Callable[[], Any],
    *,
    timeout_seconds: float,
) -> tuple[Any, bool]:
    """Run a callable with a timeout. Returns (result, timed_out)."""
    if timeout_seconds <= 0:
        return fn(), False

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout_seconds), False
        except concurrent.futures.TimeoutError:
            future.cancel()
            return None, True


def classify_result_status(result: str) -> str:
    """Classify a human-readable result into a stable status label."""
    text = (result or "").strip()
    lowered = text.lower()
    if not text:
        return "empty"
    if "timed out" in lowered or "timeout" in lowered:
        return "timeout"
    if text.startswith("[ERROR]") or lowered.startswith("error"):
        return "error"
    if "diblok" in lowered or "tidak diizinkan" in lowered:
        return "blocked"
    if "[warning]" in lowered or "degraded" in lowered:
        return "degraded"
    return "ok"


def classify_error_kind(result: str) -> str:
    """Classify an error result into retry-relevant categories."""
    status = classify_result_status(result)
    lowered = (result or "").strip().lower()
    if status == "timeout":
        return "transient"
    if status == "blocked":
        return "blocked"
    if status != "error":
        return "none"
    if any(token in lowered for token in ("api_error", "provider", "connection", "network", "timeout", "rate")):
        return "transient"
    if "no_provider" in lowered:
        return "environment"
    return "permanent"
