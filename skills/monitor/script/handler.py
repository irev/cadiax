"""Monitor skill handler."""

from __future__ import annotations

from otonomassist.core.config_doctor import get_config_status_data
from otonomassist.core.result_builder import build_result

QUEUE_WARNING_DEPTH = 5
LATENCY_WARNING_MS = 2500
LATENCY_CRITICAL_MS = 5000


def handle(args: str) -> dict[str, object] | str:
    """Monitor runtime warnings and health signals."""
    args = args.strip()
    if not args:
        args = "summary"

    command, options = _parse_args(args)
    if command in {"summary", "alerts", "health", "queue", "latency"}:
        return _monitor(command, options)
    return _usage()


def _usage() -> str:
    return "Usage: monitor <summary|alerts|health|queue|latency> [scope=<name>] [roles=<a,b>]"


def _parse_args(args: str) -> tuple[str, dict[str, object]]:
    tokens = [token for token in args.split() if token.strip()]
    command = "summary"
    if tokens and "=" not in tokens[0]:
        command = tokens[0].strip().lower()
        tokens = tokens[1:]
    options: dict[str, object] = {}
    for token in tokens:
        key, separator, value = token.partition("=")
        if not separator:
            continue
        key = key.strip().lower()
        value = value.strip()
        if key == "scope" and value:
            options["agent_scope"] = value.lower()
        elif key in {"roles", "role"}:
            options["roles"] = tuple(item.strip().lower() for item in value.split(",") if item.strip())
    return command, options


def _monitor(command: str, options: dict[str, object]) -> dict[str, object]:
    agent_scope = str(options.get("agent_scope") or "").strip().lower()
    roles = tuple(options.get("roles") or ())
    status = get_config_status_data(agent_scope=agent_scope or None, roles=roles)
    alerts = _collect_alerts(status)
    dominant_alert = alerts[0] if alerts else None
    health_status = _derive_health_status(status, alerts)
    if command == "health":
        summary = (
            f"Monitor health: health={health_status}, "
            f"overall={status['overall']['status']}, "
            f"runtime={status['runtime']['status']}, "
            f"scheduler={status['scheduler']['status']}, "
            f"alert_count={len(alerts)}."
        )
    elif command == "alerts":
        if dominant_alert:
            summary = (
                f"Monitor alerts: {len(alerts)} signal(s) aktif, "
                f"utama={dominant_alert['kind']} ({dominant_alert['severity']})."
            )
        else:
            summary = "Monitor alerts: tidak ada sinyal aktif."
    elif command == "queue":
        queue_snapshot = _summarize_queue(status)
        summary = (
            f"Monitor queue: queued={status['runtime']['queued_jobs']}, "
            f"leased={status['runtime']['leased_jobs']}, "
            f"failed={status['runtime']['failed_jobs']}, "
            f"high_watermark={queue_snapshot['high_watermark']}."
        )
    elif command == "latency":
        latency_snapshot = _summarize_latency(status)
        summary = (
            f"Monitor latency: providers={latency_snapshot['provider_count']}, "
            f"samples={status['metrics']['summary']['provider_latency_samples']}, "
            f"max_avg_ms={latency_snapshot['max_avg_ms']}."
        )
    else:
        summary = (
            f"Monitor summary: health={health_status}, "
            f"issues={len(status['issues'])}, alerts={len(alerts)}."
        )
    return build_result(
        f"monitor_{command}",
        {
            "summary": summary,
            "health_status": health_status,
            "overall_status": status["overall"]["status"],
            "alerts": alerts,
            "dominant_alert": dominant_alert,
            "issues": status["issues"],
            "scope_filter": status["scope_filter"],
            "queue": status["runtime"],
            "queue_depth": status["metrics"].get("queue_depth", {}),
            "provider_latency": status["metrics"].get("provider_latency", {}),
        },
        source_skill="monitor",
        default_view="summary",
        status="ok" if health_status == "healthy" else health_status,
    )


def _collect_alerts(status: dict[str, object]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    runtime = status["runtime"]
    scheduler = status["scheduler"]
    metrics = status["metrics"]["summary"]
    policy = status["policy"]
    privacy_controls = status["privacy_controls"]
    queue_depth = status["metrics"].get("queue_depth", {})
    provider_latency = status["metrics"].get("provider_latency", {})

    if int(runtime.get("leased_jobs", 0) or 0) > 0:
        alerts.append(_alert("leased_jobs", "warning", "Ada leased job yang belum selesai.", "observe jobs"))
    if int(runtime.get("failed_jobs", 0) or 0) > 0:
        alerts.append(_alert("failed_jobs", "critical", "Ada failed job di runtime queue.", "monitor alerts"))
    if int(metrics.get("timeouts_total", 0) or 0) > 0:
        alerts.append(_alert("timeouts", "warning", "Terdeteksi timeout pada eksekusi skill.", "monitor alerts"))
    if int(metrics.get("errors_total", 0) or 0) > 0:
        alerts.append(_alert("errors", "critical", "Terdeteksi error pada command atau skill.", "monitor alerts"))
    if int(policy.get("policy_denied_count", 0) or 0) > 0:
        alerts.append(_alert("policy_denials", "warning", "Ada policy decision yang menolak command.", "policy show"))
    if bool(privacy_controls.get("quiet_hours_active")):
        alerts.append(_alert("quiet_hours", "info", "Quiet hours sedang aktif.", "schedule show"))
    if str(scheduler.get("last_status") or "").strip().lower() == "quiet_hours":
        alerts.append(_alert("scheduler_quiet_hours", "info", "Scheduler terakhir tertahan quiet hours.", "schedule show"))

    queue_alert = _build_queue_alert(queue_depth)
    if queue_alert:
        alerts.append(queue_alert)

    latency_alert = _build_latency_alert(provider_latency, int(metrics.get("provider_latency_samples", 0) or 0))
    if latency_alert:
        alerts.append(latency_alert)

    alerts.sort(key=_alert_sort_key)
    return alerts


def _alert(kind: str, severity: str, message: str, recommended_command: str) -> dict[str, str]:
    return {
        "kind": kind,
        "severity": severity,
        "message": message,
        "recommended_command": recommended_command,
    }


def _build_queue_alert(queue_depth: object) -> dict[str, str] | None:
    if not isinstance(queue_depth, dict):
        return None
    highest_depth = 0
    highest_watermark = 0
    for snapshot in queue_depth.values():
        if not isinstance(snapshot, dict):
            continue
        highest_depth = max(highest_depth, int(snapshot.get("current_depth", 0) or 0))
        highest_watermark = max(highest_watermark, int(snapshot.get("high_watermark", 0) or 0))
    if highest_depth >= QUEUE_WARNING_DEPTH or highest_watermark >= QUEUE_WARNING_DEPTH:
        return _alert(
            "queue_depth",
            "warning",
            f"Queue depth meningkat (current={highest_depth}, high_watermark={highest_watermark}).",
            "monitor queue",
        )
    return None


def _build_latency_alert(provider_latency: object, sample_count: int) -> dict[str, str] | None:
    if not isinstance(provider_latency, dict) or not provider_latency:
        return _alert("latency_samples_missing", "info", "Belum ada sample provider latency.", "monitor latency")
    max_avg_ms = 0.0
    for snapshot in provider_latency.values():
        if not isinstance(snapshot, dict):
            continue
        max_avg_ms = max(max_avg_ms, float(snapshot.get("avg_ms", 0) or 0.0))
    if max_avg_ms >= LATENCY_CRITICAL_MS:
        return _alert(
            "provider_latency",
            "critical",
            f"Provider latency tinggi (avg={round(max_avg_ms, 2)} ms).",
            "monitor latency",
        )
    if max_avg_ms >= LATENCY_WARNING_MS:
        return _alert(
            "provider_latency",
            "warning",
            f"Provider latency mulai tinggi (avg={round(max_avg_ms, 2)} ms).",
            "monitor latency",
        )
    if sample_count <= 0:
        return _alert("latency_samples_missing", "info", "Belum ada sample provider latency.", "monitor latency")
    return None


def _derive_health_status(status: dict[str, object], alerts: list[dict[str, str]]) -> str:
    if any(alert.get("severity") == "critical" for alert in alerts):
        return "critical"
    if status["issues"] or any(alert.get("severity") == "warning" for alert in alerts):
        return "warning"
    return "healthy"


def _alert_sort_key(alert: dict[str, str]) -> tuple[int, str]:
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    return (severity_order.get(str(alert.get("severity") or ""), 3), str(alert.get("kind") or ""))


def _summarize_queue(status: dict[str, object]) -> dict[str, int]:
    queue_depth = status["metrics"].get("queue_depth", {})
    if not isinstance(queue_depth, dict):
        return {"high_watermark": 0}
    high_watermark = 0
    for snapshot in queue_depth.values():
        if not isinstance(snapshot, dict):
            continue
        high_watermark = max(high_watermark, int(snapshot.get("high_watermark", 0) or 0))
    return {"high_watermark": high_watermark}


def _summarize_latency(status: dict[str, object]) -> dict[str, int | float]:
    provider_latency = status["metrics"].get("provider_latency", {})
    if not isinstance(provider_latency, dict):
        return {"provider_count": 0, "max_avg_ms": 0.0}
    max_avg_ms = 0.0
    for snapshot in provider_latency.values():
        if not isinstance(snapshot, dict):
            continue
        max_avg_ms = max(max_avg_ms, float(snapshot.get("avg_ms", 0) or 0.0))
    return {"provider_count": len(provider_latency), "max_avg_ms": round(max_avg_ms, 2)}
