"""Policy skill handler."""

from __future__ import annotations

from otonomassist.core.result_builder import build_result
from otonomassist.core.transport import TransportContext
from otonomassist.services.policy import PolicyService


def handle(args: str) -> dict[str, object] | str:
    """Inspect or simulate policy decisions."""
    args = args.strip()
    if not args:
        args = "show"

    command, options = _parse_args(args)
    if command == "show":
        return _show_policy()
    if command == "prefixes":
        return _show_prefixes()
    if command == "check":
        return _check_policy(options)
    return _usage()


def _usage() -> str:
    return (
        "Usage: policy <show|prefixes|check> "
        "[prefix=<name>] [args=<text>] [source=<name>] [roles=<a,b>] [session_mode=<main|shared>]"
    )


def _parse_args(args: str) -> tuple[str, dict[str, object]]:
    tokens = [token for token in args.split() if token.strip()]
    command = "show"
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
        if key in {"prefix", "args", "source", "session_mode"} and value:
            options[key] = value
        elif key in {"roles", "role"}:
            options["roles"] = tuple(
                item.strip().lower()
                for item in value.split(",")
                if item.strip()
            )
    return command, options


def _show_policy() -> dict[str, object]:
    diagnostics = PolicyService().get_diagnostics()
    return build_result(
        "policy_show",
        {
            "summary": (
                f"Policy show: owner_only={len(diagnostics['telegram_owner_only_prefixes'])}, "
                f"approved={len(diagnostics['telegram_approved_prefixes'])}, "
                f"policy_events={diagnostics['policy_event_count']}."
            ),
            "policy": diagnostics,
        },
        source_skill="policy",
        default_view="summary",
    )


def _check_policy(options: dict[str, object]) -> dict[str, object] | str:
    prefix = str(options.get("prefix") or "").strip().lower()
    if not prefix:
        return "Policy check membutuhkan prefix=<name>."
    args_text = str(options.get("args") or "").strip()
    source = str(options.get("source") or "cli").strip().lower() or "cli"
    session_mode = str(options.get("session_mode") or "main").strip().lower()
    if session_mode not in {"main", "shared"}:
        session_mode = "main"
    roles = tuple(options.get("roles") or ())
    decision = PolicyService().authorize_command(
        prefix,
        args_text,
        TransportContext(
            source=source,
            roles=roles,
            session_mode=session_mode,
        ),
    )
    return build_result(
        "policy_check",
        {
            "summary": (
                f"Policy check: prefix={prefix}, "
                f"allowed={'yes' if decision.allowed else 'no'}, "
                f"reason={decision.reason or '-'}."
            ),
            "decision": {
                "allowed": decision.allowed,
                "reason": decision.reason,
                "message": decision.message or "",
                "metadata": decision.metadata,
            },
            "context": {
                "source": source,
                "roles": list(roles),
                "session_mode": session_mode,
                "args": args_text,
            },
        },
        source_skill="policy",
        default_view="summary",
        status="ok" if decision.allowed else "denied",
    )


def _show_prefixes() -> dict[str, object]:
    diagnostics = PolicyService().get_diagnostics()
    return build_result(
        "policy_prefixes",
        {
            "summary": (
                f"Policy prefixes: owner_only={len(diagnostics['telegram_owner_only_prefixes'])}, "
                f"approved={len(diagnostics['telegram_approved_prefixes'])}, "
                f"read_only={len(diagnostics['telegram_read_only_prefixes'])}."
            ),
            "owner_only_prefixes": diagnostics["telegram_owner_only_prefixes"],
            "approved_prefixes": diagnostics["telegram_approved_prefixes"],
            "read_only_prefixes": diagnostics["telegram_read_only_prefixes"],
            "mutating_prefixes": diagnostics["telegram_mutating_prefixes"],
        },
        source_skill="policy",
        default_view="summary",
    )
