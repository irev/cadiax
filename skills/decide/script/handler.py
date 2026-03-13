"""Decide skill handler."""

from __future__ import annotations

from otonomassist.core.agent_context import get_next_planner_task, list_ready_planner_tasks
from otonomassist.core.config_doctor import get_config_status_data
from otonomassist.core.result_builder import build_result
from otonomassist.core.runtime_interaction import get_current_interaction_context


KNOWN_PREFIXES = {
    "ai",
    "agent-loop",
    "decide",
    "executor",
    "help",
    "identity",
    "memory",
    "monitor",
    "notify",
    "observe",
    "planner",
    "policy",
    "profile",
    "research",
    "schedule",
    "secrets",
    "self-review",
    "workspace",
}

CAPABILITY_PREFIX_ALIASES = {
    "chat": "ai",
    "plan": "planner",
    "act": "executor",
    "reflect": "agent-loop",
    "inspect": "workspace",
    "persona": "profile",
    "review": "self-review",
}

ALERT_PRIORITY = {
    "failed_jobs": 90,
    "errors_total": 80,
    "timeouts_total": 70,
    "policy_denied_count": 60,
    "leased_jobs": 50,
    "quiet_hours_active": 40,
}


def handle(args: str) -> dict[str, object] | str:
    """Choose a next action or the best option from multiple candidates."""
    args = args.strip()
    if not args:
        args = "next"

    inferred = _infer_natural_language(args)
    if inferred:
        args = inferred

    command, content, options = _parse_args(args)
    if command == "next":
        return _decide_next(options)
    if command == "between":
        return _decide_between(content, options)
    return _usage()


def _usage() -> str:
    return "Usage: decide <next|between <option-a> | <option-b>> [scope=<name>] [roles=<a,b>]"


def _infer_natural_language(args: str) -> str | None:
    lowered = args.lower().strip()
    if not lowered:
        return None
    if lowered.startswith(("next", "between")):
        return None
    if "|" in lowered or " atau " in lowered:
        return "between " + args.replace(" atau ", " | ")
    if any(token in lowered for token in ("langkah terbaik", "next action", "tindakan terbaik", "aksi terbaik")):
        return "next"
    return None


def _parse_args(args: str) -> tuple[str, str, dict[str, object]]:
    tokens = [token for token in args.split() if token.strip()]
    command = "next"
    if tokens and "=" not in tokens[0]:
        command = tokens[0].strip().lower()
        tokens = tokens[1:]

    content_tokens: list[str] = []
    options: dict[str, object] = {}
    for token in tokens:
        key, separator, value = token.partition("=")
        if separator and key.strip().lower() == "scope" and value.strip():
            options["agent_scope"] = value.strip().lower()
            continue
        if separator and key.strip().lower() in {"roles", "role"}:
            options["roles"] = tuple(
                item.strip().lower()
                for item in value.split(",")
                if item.strip()
            )
            continue
        content_tokens.append(token)

    context = get_current_interaction_context()
    if "agent_scope" not in options:
        options["agent_scope"] = str(context.get("agent_scope") or "").strip().lower()
    if "roles" not in options:
        options["roles"] = tuple(context.get("roles") or ())
    return command, " ".join(content_tokens).strip(), options


def _decide_next(options: dict[str, object]) -> dict[str, object]:
    status = _load_status(options)
    next_task = get_next_planner_task()
    ready_tasks = list_ready_planner_tasks()
    health = _extract_health_signals(status)
    dominant_signal = _select_dominant_signal(health)
    recommendation = _recommend_next_action(next_task, health)
    summary = (
        f"Decide next: pilih `{recommendation['command']}` "
        f"karena {recommendation['reason']}."
    )
    return build_result(
        "decide_next",
        {
            "summary": summary,
            "decision": recommendation,
            "next_task": next_task,
            "ready_task_count": len(ready_tasks),
            "health": health,
            "dominant_signal": dominant_signal,
            "scope_filter": status["scope_filter"],
        },
        source_skill="decide",
        default_view="summary",
    )


def _decide_between(content: str, options: dict[str, object]) -> dict[str, object] | str:
    raw_options = [item.strip() for item in content.split("|") if item.strip()]
    if len(raw_options) < 2:
        return "Decide between membutuhkan minimal dua opsi yang dipisahkan dengan '|'."

    status = _load_status(options)
    next_task = get_next_planner_task()
    health = _extract_health_signals(status)
    scored = [
        _score_option(option, next_task=next_task, health=health, index=index)
        for index, option in enumerate(raw_options)
    ]
    scored.sort(key=lambda item: (-item["score"], int(item["index"])))
    selected = scored[0]
    summary = (
        f"Decide between: pilih `{selected['option']}` "
        f"karena {selected['reason']}."
    )
    return build_result(
        "decide_between",
        {
            "summary": summary,
            "selected": {
                "option": selected["option"],
                "score": selected["score"],
                "reason": selected["reason"],
            },
            "candidates": [
                {
                    "option": item["option"],
                    "score": item["score"],
                    "reason": item["reason"],
                }
                for item in scored
            ],
            "health": health,
            "scope_filter": status["scope_filter"],
        },
        source_skill="decide",
        default_view="summary",
    )


def _load_status(options: dict[str, object]) -> dict[str, object]:
    agent_scope = str(options.get("agent_scope") or "").strip().lower()
    roles = tuple(options.get("roles") or ())
    return get_config_status_data(agent_scope=agent_scope or None, roles=roles)


def _extract_health_signals(status: dict[str, object]) -> dict[str, int | bool | str]:
    runtime = status["runtime"]
    scheduler = status["scheduler"]
    metrics = status["metrics"]["summary"]
    policy = status["policy"]
    quiet_hours_active = bool(status["privacy_controls"].get("quiet_hours_active"))
    return {
        "issue_count": len(status["issues"]),
        "queued_jobs": int(runtime.get("queued_jobs", 0) or 0),
        "leased_jobs": int(runtime.get("leased_jobs", 0) or 0),
        "failed_jobs": int(runtime.get("failed_jobs", 0) or 0),
        "timeouts_total": int(metrics.get("timeouts_total", 0) or 0),
        "errors_total": int(metrics.get("errors_total", 0) or 0),
        "policy_denied_count": int(policy.get("policy_denied_count", 0) or 0),
        "scheduler_last_status": str(scheduler.get("last_status") or "").strip().lower(),
        "quiet_hours_active": quiet_hours_active,
    }


def _recommend_next_action(next_task: dict[str, object] | None, health: dict[str, object]) -> dict[str, str]:
    dominant_signal = _select_dominant_signal(health)
    if dominant_signal in {"failed_jobs", "errors_total", "timeouts_total", "policy_denied_count"}:
        return {
            "command": "monitor alerts",
            "reason": _reason_for_signal(dominant_signal),
        }
    if dominant_signal == "leased_jobs":
        return {
            "command": "observe jobs",
            "reason": _reason_for_signal(dominant_signal),
        }
    if dominant_signal == "quiet_hours_active":
        return {
            "command": "schedule show",
            "reason": _reason_for_signal(dominant_signal),
        }
    if next_task:
        return {
            "command": "executor next",
            "reason": f"task planner siap tersedia sebagai #{next_task['id']}",
        }
    if int(health["queued_jobs"] or 0) > 0 or int(health["leased_jobs"] or 0) > 0:
        return {
            "command": "observe jobs",
            "reason": "runtime queue masih memiliki aktivitas yang perlu diamati",
        }
    if bool(health["quiet_hours_active"]) or health["scheduler_last_status"] == "quiet_hours":
        return {
            "command": "schedule show",
            "reason": "scheduler sedang dipengaruhi quiet hours",
        }
    return {
        "command": "agent-loop next",
        "reason": "tidak ada alert atau task siap sehingga refleksi ringan paling relevan",
    }


def _score_option(
    option: str,
    *,
    next_task: dict[str, object] | None,
    health: dict[str, object],
    index: int,
) -> dict[str, object]:
    normalized = option.strip()
    prefix = normalized.split(" ", 1)[0].strip().lower() if normalized else ""
    resolved_prefix = CAPABILITY_PREFIX_ALIASES.get(prefix, prefix)
    score = 0
    reasons: list[str] = []
    dominant_signal = _select_dominant_signal(health)

    if resolved_prefix in KNOWN_PREFIXES:
        score += 1
        reasons.append("opsi sudah berupa command internal yang executable")

    if resolved_prefix == "monitor" and dominant_signal in {"failed_jobs", "errors_total", "timeouts_total", "policy_denied_count"}:
        score += 8
        reasons.append(_reason_for_signal(dominant_signal))
    if resolved_prefix == "observe" and dominant_signal == "leased_jobs":
        score += 8
        reasons.append(_reason_for_signal(dominant_signal))
    if resolved_prefix == "schedule" and dominant_signal == "quiet_hours_active":
        score += 7
        reasons.append(_reason_for_signal(dominant_signal))
    if resolved_prefix == "executor" and next_task:
        score += 6
        reasons.append(f"ada next planner task #{next_task['id']} yang siap")
    if resolved_prefix == "observe" and (int(health["queued_jobs"] or 0) > 0 or int(health["leased_jobs"] or 0) > 0):
        score += 4
        reasons.append("queue masih aktif dan layak diobservasi")
    if resolved_prefix == "agent-loop" and not next_task and not _has_attention_alerts(health):
        score += 3
        reasons.append("refleksi ringan cocok saat state relatif tenang")
    if resolved_prefix == "planner" and not next_task:
        score += 2
        reasons.append("planner bisa dipakai saat belum ada next task siap")
    if resolved_prefix == "workspace" and int(health["issue_count"] or 0) == 0 and not next_task:
        score += 1
        reasons.append("inspeksi lokal aman dilakukan saat state relatif tenang")
    if resolved_prefix == "secrets":
        score -= 2
        reasons.append("aksi secrets bukan prioritas default untuk keputusan umum")

    if not reasons:
        reasons.append("opsi ini masih valid tetapi punya sinyal prioritas yang lebih lemah")

    return {
        "index": index,
        "option": normalized,
        "score": score,
        "reason": reasons[0],
    }


def _has_attention_alerts(health: dict[str, object]) -> bool:
    return any(
        int(health[key] or 0) > 0
        for key in ("failed_jobs", "leased_jobs", "timeouts_total", "errors_total", "policy_denied_count")
    )


def _select_dominant_signal(health: dict[str, object]) -> str:
    ranked: list[tuple[int, str]] = []
    for key, priority in ALERT_PRIORITY.items():
        value = health.get(key)
        is_active = bool(value) if isinstance(value, bool) else int(value or 0) > 0
        if is_active:
            ranked.append((priority, key))
    if not ranked:
        return "steady"
    ranked.sort(reverse=True)
    return ranked[0][1]


def _reason_for_signal(signal: str) -> str:
    if signal == "failed_jobs":
        return "ada failed job yang perlu dianalisis lebih dulu"
    if signal == "errors_total":
        return "ada error command atau skill yang perlu ditinjau"
    if signal == "timeouts_total":
        return "ada timeout eksekusi yang perlu ditelusuri"
    if signal == "policy_denied_count":
        return "ada policy denial yang perlu diklarifikasi"
    if signal == "leased_jobs":
        return "ada leased job aktif yang perlu diobservasi"
    if signal == "quiet_hours_active":
        return "quiet hours aktif sehingga status scheduler perlu dicek"
    return "state saat ini relatif stabil"
