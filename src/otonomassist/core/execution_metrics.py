"""Aggregated execution metrics for operator and admin surfaces."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from otonomassist.core.agent_context import load_metrics_state, save_metrics_state


def record_execution_metric(
    metric_type: str,
    *,
    status: str = "",
    skill_name: str = "",
    source: str = "",
    duration_ms: int | None = None,
) -> None:
    """Record one aggregated execution metric."""
    state = load_metrics_state()
    counters = state.setdefault("counters", {})
    timings = state.setdefault("timings", {})

    _bump(counters, "events_total")
    _bump(counters, f"{metric_type}_total")
    if status:
        _bump(counters, f"{metric_type}_status_{status}")
    if skill_name:
        _bump(counters, f"skill_{skill_name}_total")
        if status:
            _bump(counters, f"skill_{skill_name}_status_{status}")
    if source:
        _bump(counters, f"source_{source}_total")

    if duration_ms is not None:
        bucket = metric_type if not skill_name else f"{metric_type}:{skill_name}"
        summary = timings.setdefault(
            bucket,
            {
                "count": 0,
                "total_ms": 0,
                "max_ms": 0,
            },
        )
        summary["count"] = int(summary.get("count", 0) or 0) + 1
        summary["total_ms"] = int(summary.get("total_ms", 0) or 0) + int(duration_ms)
        summary["max_ms"] = max(int(summary.get("max_ms", 0) or 0), int(duration_ms))
        summary["avg_ms"] = round(summary["total_ms"] / max(1, summary["count"]), 2)

    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_metrics_state(state)


def record_ai_usage_metric(
    *,
    provider: str,
    model: str,
    usage: dict[str, int] | None,
) -> None:
    """Record aggregated token usage for one AI request when available."""
    if not usage:
        return

    state = load_metrics_state()
    counters = state.setdefault("counters", {})
    token_usage = state.setdefault("token_usage", {})

    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", 0) or 0)

    if total_tokens <= 0 and (prompt_tokens > 0 or completion_tokens > 0):
        total_tokens = prompt_tokens + completion_tokens

    _bump(counters, "ai_requests_total")
    _add(counters, "ai_prompt_tokens_total", prompt_tokens)
    _add(counters, "ai_completion_tokens_total", completion_tokens)
    _add(counters, "ai_total_tokens_total", total_tokens)
    if provider:
        _bump(counters, f"ai_provider_{provider}_requests_total")
    if model:
        _bump(counters, f"ai_model_{model}_requests_total")

    bucket = token_usage.setdefault(
        f"{provider}:{model}" if provider or model else "unknown",
        {
            "provider": provider,
            "model": model,
            "requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    )
    bucket["requests"] = int(bucket.get("requests", 0) or 0) + 1
    bucket["prompt_tokens"] = int(bucket.get("prompt_tokens", 0) or 0) + prompt_tokens
    bucket["completion_tokens"] = int(bucket.get("completion_tokens", 0) or 0) + completion_tokens
    bucket["total_tokens"] = int(bucket.get("total_tokens", 0) or 0) + total_tokens

    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_metrics_state(state)


def get_execution_metrics_snapshot() -> dict[str, Any]:
    """Return a machine-readable snapshot of aggregated metrics."""
    state = load_metrics_state()
    counters = state.get("counters", {})
    timings = state.get("timings", {})
    return {
        "updated_at": state.get("updated_at", ""),
        "counters": counters,
        "timings": timings,
        "token_usage": state.get("token_usage", {}),
        "summary": {
            "events_total": int(counters.get("events_total", 0) or 0),
            "commands_total": int(counters.get("command_completed_total", 0) or 0),
            "skills_total": int(counters.get("skill_completed_total", 0) or 0),
            "timeouts_total": int(counters.get("skill_completed_status_timeout", 0) or 0),
            "errors_total": int(counters.get("command_completed_status_error", 0) or 0)
            + int(counters.get("skill_completed_status_error", 0) or 0),
            "ai_requests_total": int(counters.get("ai_requests_total", 0) or 0),
            "ai_total_tokens": int(counters.get("ai_total_tokens_total", 0) or 0),
        },
    }


def render_execution_metrics() -> str:
    """Render operator-facing execution metrics summary."""
    snapshot = get_execution_metrics_snapshot()
    lines = [
        "Execution Metrics",
        "",
        "[Summary]",
        f"- updated_at: {snapshot['updated_at'] or '-'}",
        f"- events_total: {snapshot['summary']['events_total']}",
        f"- commands_total: {snapshot['summary']['commands_total']}",
        f"- skills_total: {snapshot['summary']['skills_total']}",
        f"- timeouts_total: {snapshot['summary']['timeouts_total']}",
        f"- errors_total: {snapshot['summary']['errors_total']}",
        f"- ai_requests_total: {snapshot['summary']['ai_requests_total']}",
        f"- ai_total_tokens: {snapshot['summary']['ai_total_tokens']}",
    ]
    token_usage = snapshot.get("token_usage", {})
    if token_usage:
        lines.extend(["", "[Token Usage]"])
        for _, summary in sorted(token_usage.items()):
            lines.append(
                f"- {summary.get('provider') or '-'} / {summary.get('model') or '-'}: "
                f"requests={summary.get('requests', 0)}, "
                f"prompt_tokens={summary.get('prompt_tokens', 0)}, "
                f"completion_tokens={summary.get('completion_tokens', 0)}, "
                f"total_tokens={summary.get('total_tokens', 0)}"
            )
    timings = snapshot.get("timings", {})
    if timings:
        lines.extend(["", "[Timings]"])
        for name, summary in sorted(timings.items()):
            lines.append(
                f"- {name}: avg_ms={summary.get('avg_ms', 0)}, "
                f"max_ms={summary.get('max_ms', 0)}, count={summary.get('count', 0)}"
            )
    return "\n".join(lines)


def _bump(counters: dict[str, Any], key: str) -> None:
    counters[key] = int(counters.get(key, 0) or 0) + 1


def _add(counters: dict[str, Any], key: str, amount: int) -> None:
    counters[key] = int(counters.get(key, 0) or 0) + int(amount or 0)
