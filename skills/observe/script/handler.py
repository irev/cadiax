"""Observe skill handler."""

from __future__ import annotations

from otonomassist.core.config_doctor import get_config_status_data
from otonomassist.core.event_bus import get_event_bus_snapshot
from otonomassist.core.execution_history import export_execution_events
from otonomassist.core.execution_metrics import get_execution_metrics_snapshot
from otonomassist.core.job_runtime import get_job_queue_snapshot, get_job_queue_summary
from otonomassist.core.result_builder import build_result
from otonomassist.core.runtime_interaction import get_current_interaction_context
from otonomassist.core.scheduler_runtime import get_scheduler_summary


def handle(args: str) -> dict[str, object] | str:
    """Observe runtime state through a read-only skill surface."""
    args = args.strip()
    if not args:
        args = "summary"

    inferred = _infer_natural_language(args)
    if inferred:
        args = inferred

    command, options = _parse_command(args)
    command = command or "summary"

    if command == "summary":
        return _observe_summary(options)
    if command == "status":
        return _observe_status(options)
    if command == "metrics":
        return _observe_metrics(options)
    if command == "events":
        return _observe_events(options)
    if command == "history":
        return _observe_history(options)
    if command == "jobs":
        return _observe_jobs(options)
    if command == "scheduler":
        return _observe_scheduler(options)
    if command == "identity":
        return _observe_identity(options)
    if command == "notifications":
        return _observe_notifications(options)
    return _usage()


def _usage() -> str:
    return (
        "Usage: observe <summary|status|metrics|events|history|jobs|scheduler|identity|notifications> "
        "[scope=<name>] [roles=<a,b>] [limit=<n>]"
    )


def _parse_command(args: str) -> tuple[str, dict[str, object]]:
    tokens = [token for token in args.split() if token.strip()]
    command = ""
    options: dict[str, object] = {}
    if tokens and "=" not in tokens[0]:
        command = tokens[0].strip().lower()
        tokens = tokens[1:]
    for token in tokens:
        key, separator, value = token.partition("=")
        if not separator:
            continue
        key = key.strip().lower()
        value = value.strip()
        if key == "scope" and value:
            options["agent_scope"] = value.lower()
        elif key in {"roles", "role"}:
            options["roles"] = tuple(
                item.strip().lower()
                for item in value.split(",")
                if item.strip()
            )
        elif key == "limit":
            try:
                options["limit"] = max(1, min(200, int(value)))
            except ValueError:
                continue
    context = get_current_interaction_context()
    if "agent_scope" not in options:
        options["agent_scope"] = str(context.get("agent_scope") or "").strip().lower()
    if "roles" not in options:
        options["roles"] = tuple(context.get("roles") or ())
    if "limit" not in options:
        options["limit"] = 20
    return command, options


def _infer_natural_language(args: str) -> str | None:
    lowered = args.lower().strip()
    if not lowered:
        return None
    if lowered.startswith(("summary", "status", "metrics", "events", "history", "jobs", "scheduler", "identity", "notifications")):
        return None
    if any(token in lowered for token in ("identity", "session continuity", "session id", "identitas")):
        return "identity"
    if any(token in lowered for token in ("notification", "notify history", "dispatch history", "notifikasi")):
        return "notifications"
    if any(token in lowered for token in ("metric", "latency", "token", "queue depth")):
        return "metrics"
    if any(token in lowered for token in ("event", "topic", "bus")):
        return "events"
    if any(token in lowered for token in ("history", "audit trail", "trace")):
        return "history"
    if any(token in lowered for token in ("job", "queue", "worker")):
        return "jobs"
    if any(token in lowered for token in ("scheduler", "heartbeat")):
        return "scheduler"
    if any(token in lowered for token in ("status", "health", "runtime", "sistem", "kondisi")):
        return "status"
    return "summary"


def _observe_summary(options: dict[str, object]) -> dict[str, object]:
    agent_scope, roles, limit = _normalized_options(options)
    status = get_config_status_data(agent_scope=agent_scope or None, roles=roles)
    metrics = get_execution_metrics_snapshot()
    events = get_event_bus_snapshot(limit=limit, agent_scope=agent_scope or None, roles=roles)
    jobs = (
        get_job_queue_snapshot(agent_scope=agent_scope or None, roles=roles)
        if agent_scope
        else {"summary": get_job_queue_summary(), "scope_filter": {"agent_scope": "", "roles": []}}
    )
    scheduler = get_scheduler_summary()
    summary = (
        f"Observe summary: overall={status['overall']['status']}, "
        f"runtime={status['runtime']['status']}, "
        f"scheduler={status['scheduler']['last_status'] or 'idle'}, "
        f"jobs={jobs['summary']['total_jobs']}, "
        f"events={events['total_events']}, "
        f"issues={len(status['issues'])}."
    )
    return build_result(
        "observe_summary",
        {
            "summary": summary,
            "overall_status": status["overall"]["status"],
            "runtime_status": status["runtime"]["status"],
            "scheduler_status": status["scheduler"]["last_status"] or "idle",
            "job_count": jobs["summary"]["total_jobs"],
            "event_count": events["total_events"],
            "issues": status["issues"],
            "scope_filter": status["scope_filter"],
            "metrics_summary": metrics["summary"],
            "snapshot": {
                "status": status,
                "metrics": metrics["summary"],
                "events": {
                    "total_events": events["total_events"],
                    "last_event_topic": events["last_event_topic"],
                    "last_event_type": events["last_event_type"],
                },
                "jobs": jobs["summary"],
                "scheduler": scheduler,
            },
        },
        source_skill="observe",
        default_view="summary",
    )


def _observe_status(options: dict[str, object]) -> dict[str, object]:
    agent_scope, roles, _ = _normalized_options(options)
    snapshot = get_config_status_data(agent_scope=agent_scope or None, roles=roles)
    summary = (
        f"Observe status: overall={snapshot['overall']['status']}, "
        f"ai={snapshot['ai']['status']}, workspace={snapshot['workspace']['status']}, "
        f"runtime={snapshot['runtime']['status']}, scheduler={snapshot['scheduler']['status']}."
    )
    return build_result(
        "observe_status",
        {
            "summary": summary,
            "overall_status": snapshot["overall"]["status"],
            "issue_count": len(snapshot["issues"]),
            "scope_filter": snapshot["scope_filter"],
            "snapshot": snapshot,
        },
        source_skill="observe",
        default_view="summary",
    )


def _observe_metrics(options: dict[str, object]) -> dict[str, object]:
    snapshot = get_execution_metrics_snapshot()
    summary = (
        f"Observe metrics: events={snapshot['summary']['events_total']}, "
        f"commands={snapshot['summary']['commands_total']}, "
        f"skills={snapshot['summary']['skills_total']}, "
        f"ai_requests={snapshot['summary']['ai_requests_total']}."
    )
    return build_result(
        "observe_metrics",
        {
            "summary": summary,
            "updated_at": snapshot["updated_at"],
            "metrics_summary": snapshot["summary"],
            "queue_depth": snapshot.get("queue_depth", {}),
            "provider_latency": snapshot.get("provider_latency", {}),
            "snapshot": snapshot,
        },
        source_skill="observe",
        default_view="summary",
    )


def _observe_events(options: dict[str, object]) -> dict[str, object]:
    agent_scope, roles, limit = _normalized_options(options)
    snapshot = get_event_bus_snapshot(limit=limit, agent_scope=agent_scope or None, roles=roles)
    summary = (
        f"Observe events: returned={snapshot['returned_events']}, "
        f"total={snapshot['total_events']}, "
        f"last_topic={snapshot['last_event_topic'] or '-'}."
    )
    return build_result(
        "observe_events",
        {
            "summary": summary,
            "returned_events": snapshot["returned_events"],
            "total_events": snapshot["total_events"],
            "topics": snapshot["topics"],
            "events": snapshot.get("events", []),
            "scope_filter": {"agent_scope": agent_scope, "roles": list(roles), "limit": limit},
            "snapshot": snapshot,
        },
        source_skill="observe",
        default_view="summary",
    )


def _observe_history(options: dict[str, object]) -> dict[str, object]:
    agent_scope, roles, limit = _normalized_options(options)
    events = export_execution_events(limit=limit, agent_scope=agent_scope or None, roles=roles)
    latest = events[-1] if events else {}
    summary = (
        f"Observe history: returned={len(events)}, "
        f"latest_event={latest.get('event_type', '-')}, "
        f"latest_status={latest.get('status', '-') or '-'}."
    )
    return build_result(
        "observe_history",
        {
            "summary": summary,
            "returned_events": len(events),
            "latest_event_type": str(latest.get("event_type", "")),
            "latest_status": str(latest.get("status", "")),
            "events": events,
            "scope_filter": {"agent_scope": agent_scope, "roles": list(roles), "limit": limit},
        },
        source_skill="observe",
        default_view="summary",
    )


def _observe_jobs(options: dict[str, object]) -> dict[str, object]:
    agent_scope, roles, _ = _normalized_options(options)
    snapshot = (
        get_job_queue_snapshot(agent_scope=agent_scope or None, roles=roles)
        if agent_scope
        else {"summary": get_job_queue_summary(), "queue": {}, "scope_filter": {"agent_scope": "", "roles": []}}
    )
    summary = (
        f"Observe jobs: total={snapshot['summary']['total_jobs']}, "
        f"queued={snapshot['summary']['queued_jobs']}, "
        f"leased={snapshot['summary']['leased_jobs']}, "
        f"failed={snapshot['summary']['failed_jobs']}."
    )
    return build_result(
        "observe_jobs",
        {
            "summary": summary,
            "job_summary": snapshot["summary"],
            "scope_filter": snapshot.get("scope_filter", {}),
            "snapshot": snapshot,
        },
        source_skill="observe",
        default_view="summary",
    )


def _observe_scheduler(options: dict[str, object]) -> dict[str, object]:
    snapshot = get_scheduler_summary()
    summary = (
        f"Observe scheduler: last_status={snapshot['last_status'] or 'idle'}, "
        f"last_cycles={snapshot['last_cycles']}, "
        f"last_processed={snapshot['last_processed']}."
    )
    return build_result(
        "observe_scheduler",
        {
            "summary": summary,
            "scheduler": snapshot,
        },
        source_skill="observe",
        default_view="summary",
    )


def _observe_identity(options: dict[str, object]) -> dict[str, object]:
    agent_scope, roles, _ = _normalized_options(options)
    snapshot = get_config_status_data(agent_scope=agent_scope or None, roles=roles)["identity"]
    summary = (
        f"Observe identity: identities={snapshot['identity_count']}, "
        f"sessions={snapshot['session_count']}, "
        f"latest_identity={snapshot['latest_identity_id'] or '-'}."
    )
    return build_result(
        "observe_identity",
        {
            "summary": summary,
            "snapshot": snapshot,
            "scope_filter": {
                "agent_scope": agent_scope,
                "roles": list(roles),
            },
        },
        source_skill="observe",
        default_view="summary",
    )


def _observe_notifications(options: dict[str, object]) -> dict[str, object]:
    agent_scope, roles, _ = _normalized_options(options)
    snapshot = get_config_status_data(agent_scope=agent_scope or None, roles=roles)["notifications"]
    summary = (
        f"Observe notifications: count={snapshot['notification_count']}, "
        f"channels={len(snapshot['by_channel'])}, "
        f"latest_channel={str((snapshot.get('latest_notification') or {}).get('channel', '') or '-') }."
    )
    return build_result(
        "observe_notifications",
        {
            "summary": summary,
            "snapshot": snapshot,
            "scope_filter": {
                "agent_scope": agent_scope,
                "roles": list(roles),
            },
        },
        source_skill="observe",
        default_view="summary",
    )


def _normalized_options(options: dict[str, object]) -> tuple[str, tuple[str, ...], int]:
    agent_scope = str(options.get("agent_scope") or "").strip().lower()
    roles = tuple(str(role).strip().lower() for role in options.get("roles", ()) if str(role).strip())
    limit = int(options.get("limit", 20) or 20)
    return agent_scope, roles, limit
