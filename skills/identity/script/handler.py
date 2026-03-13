"""Identity skill handler."""

from __future__ import annotations

from cadiax.core.result_builder import build_result
from cadiax.core.runtime_interaction import get_current_interaction_context
from cadiax.services.interactions.identity_service import IdentitySessionService
from cadiax.services.interactions.models import InteractionRequest


def handle(args: str) -> dict[str, object] | str:
    """Inspect or resolve identity/session continuity."""
    args = args.strip()
    if not args:
        args = "show"

    command, options = _parse_args(args)
    if command == "show":
        return _show_identity(options)
    if command == "sessions":
        return _show_sessions(options)
    if command == "resolve":
        return _resolve_identity(options)
    return _usage()


def _usage() -> str:
    return (
        "Usage: identity <show|sessions|resolve> "
        "[source=<name>] [user_id=<id>] [session_id=<id>] [chat_id=<id>] "
        "[identity_hint=<value>] [scope=<name>] [roles=<a,b>]"
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
        if key in {"source", "user_id", "session_id", "chat_id", "identity_hint"} and value:
            options[key] = value
        elif key == "scope" and value:
            options["agent_scope"] = value.lower()
        elif key in {"roles", "role"}:
            options["roles"] = tuple(
                item.strip().lower()
                for item in value.split(",")
                if item.strip()
            )
    context = get_current_interaction_context()
    options.setdefault("agent_scope", str(context.get("agent_scope") or "").strip().lower())
    options.setdefault("roles", tuple(context.get("roles") or ()))
    options.setdefault("source", str(context.get("source") or "cli").strip() or "cli")
    return command, options


def _show_identity(options: dict[str, object]) -> dict[str, object]:
    agent_scope = str(options.get("agent_scope") or "").strip().lower()
    roles = tuple(options.get("roles") or ())
    snapshot = IdentitySessionService().get_snapshot(agent_scope=agent_scope or None, roles=roles)
    summary = (
        f"Identity snapshot: identities={snapshot['identity_count']}, "
        f"sessions={snapshot['session_count']}, "
        f"latest_identity={snapshot['latest_identity_id'] or '-'}."
    )
    return build_result(
        "identity_show",
        {
            "summary": summary,
            "snapshot": snapshot,
        },
        source_skill="identity",
        default_view="summary",
    )


def _resolve_identity(options: dict[str, object]) -> dict[str, object] | str:
    source = str(options.get("source") or "cli").strip() or "cli"
    user_id = str(options.get("user_id") or "").strip()
    session_id = str(options.get("session_id") or "").strip()
    chat_id = str(options.get("chat_id") or "").strip()
    identity_hint = str(options.get("identity_hint") or "").strip()
    agent_scope = str(options.get("agent_scope") or "").strip().lower() or "default"
    roles = tuple(options.get("roles") or ())
    if not any((user_id, session_id, chat_id, identity_hint)):
        return "Identity resolve membutuhkan minimal salah satu dari user_id, session_id, chat_id, atau identity_hint."

    request = InteractionRequest(
        message="identity resolve",
        source=source,
        user_id=user_id or None,
        session_id=session_id or None,
        chat_id=chat_id or None,
        roles=roles,
        agent_scope=agent_scope,
        metadata={"identity_hint": identity_hint} if identity_hint else {},
    )
    resolution = IdentitySessionService().resolve(request)
    return build_result(
        "identity_resolve",
        {
            "summary": (
                f"Identity resolved: identity_id={resolution.identity_id}, "
                f"session_id={resolution.session_id}."
            ),
            "identity_id": resolution.identity_id,
            "session_id": resolution.session_id,
            "identity_created": resolution.identity_created,
            "session_created": resolution.session_created,
            "agent_scope": agent_scope,
            "roles": list(roles),
        },
        source_skill="identity",
        default_view="summary",
    )


def _show_sessions(options: dict[str, object]) -> dict[str, object]:
    agent_scope = str(options.get("agent_scope") or "").strip().lower()
    roles = tuple(options.get("roles") or ())
    snapshot = IdentitySessionService().get_snapshot(agent_scope=agent_scope or None, roles=roles)
    return build_result(
        "identity_sessions",
        {
            "summary": (
                f"Identity sessions: sessions={snapshot['session_count']}, "
                f"latest_session={snapshot['latest_session_id'] or '-'}."
            ),
            "session_count": snapshot["session_count"],
            "latest_session_id": snapshot["latest_session_id"],
            "sessions": snapshot["sessions"],
            "scope_filter": {
                "agent_scope": agent_scope,
                "roles": list(roles),
            },
        },
        source_skill="identity",
        default_view="summary",
    )
