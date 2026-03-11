"""Transport-aware command policy service."""

from __future__ import annotations

import os

from otonomassist.core.execution_history import append_execution_event, new_trace_id
from otonomassist.core.transport import TransportContext
from otonomassist.services.policy.models import PolicyDecision


class PolicyService:
    """Evaluate whether one command may execute for the given transport context."""

    def authorize_command(
        self,
        prefix: str,
        args: str,
        context: TransportContext | None,
    ) -> PolicyDecision:
        """Authorize a command/skill prefix and subcommand for a transport context."""
        prefix = prefix.strip().lower()
        subcommand = _extract_subcommand(args)
        roles = tuple(context.roles) if context else ()

        if context is None or context.source != "telegram":
            return self._record_decision(
                context,
                prefix,
                args,
                subcommand,
                PolicyDecision(
                    allowed=True,
                    reason="policy_not_applicable",
                    metadata={"roles": list(roles)},
                ),
            )

        role_set = set(roles)
        if "owner" in role_set:
            return self._record_decision(
                context,
                prefix,
                args,
                subcommand,
                PolicyDecision(
                    allowed=True,
                    reason="telegram_owner",
                    metadata={"roles": list(roles)},
                ),
            )
        if "approved" not in role_set:
            return self._record_decision(
                context,
                prefix,
                args,
                subcommand,
                PolicyDecision(
                    allowed=False,
                    message="Akses Telegram belum diotorisasi untuk operasi ini.",
                    reason="telegram_unapproved",
                    metadata={"roles": list(roles)},
                ),
            )

        owner_only = _parse_prefix_set(
            "TELEGRAM_OWNER_ONLY_PREFIXES",
            {"admin", "debug-config", "doctor", "external", "list-models", "secrets", "executor", "runner"},
        )
        approved = _parse_prefix_set(
            "TELEGRAM_APPROVED_PREFIXES",
            {
                "help",
                "history",
                "list",
                "metrics",
                "jobs",
                "skills",
                "ai",
                "research",
                "memory",
                "planner",
                "profile",
                "agent-loop",
                "workspace",
                "self-review",
            },
        )

        if prefix in owner_only:
            return self._record_decision(
                context,
                prefix,
                args,
                subcommand,
                PolicyDecision(
                    allowed=False,
                    message=(
                        f"Command/skill `{prefix}` dibatasi untuk owner Telegram. "
                        "Gunakan akun owner atau minta owner menjalankannya."
                    ),
                    reason="telegram_owner_only_prefix",
                    metadata={"roles": list(roles)},
                ),
            )

        if prefix in approved:
            action_denied = self._authorize_approved_action(prefix, subcommand)
            if action_denied:
                return self._record_decision(
                    context,
                    prefix,
                    args,
                    subcommand,
                    PolicyDecision(
                        allowed=False,
                        message=action_denied,
                        reason="telegram_approved_action_denied",
                        metadata={"roles": list(roles)},
                    ),
                )
            return self._record_decision(
                context,
                prefix,
                args,
                subcommand,
                PolicyDecision(
                    allowed=True,
                    reason="telegram_approved_prefix",
                    metadata={"roles": list(roles)},
                ),
            )

        return self._record_decision(
            context,
            prefix,
            args,
            subcommand,
            PolicyDecision(
                allowed=False,
                message=f"Command/skill `{prefix}` tidak diizinkan untuk user Telegram non-owner.",
                reason="telegram_prefix_denied",
                metadata={"roles": list(roles)},
            ),
        )

    def _authorize_approved_action(self, prefix: str, subcommand: str) -> str | None:
        """Apply finer-grained action checks for approved Telegram users."""
        read_only_actions: dict[str, set[str]] = {
            "help": {""},
            "history": {"", "recent"},
            "list": {""},
            "metrics": {"", "summary"},
            "jobs": {"", "list", "queue"},
            "skills": {"audit"},
            "ai": {"*"},
            "research": {"*"},
            "workspace": {"tree", "read", "find", "files", "summary"},
            "memory": {"list", "search", "get", "summarize", "summary", "context"},
            "planner": {"list", "next", "summary"},
            "profile": {"show"},
        }
        mutate_denial: dict[str, str] = {
            "jobs": "Operasi runtime job Telegram dibatasi untuk owner.",
            "memory": "Operasi ubah memory Telegram dibatasi untuk owner.",
            "planner": "Operasi ubah planner Telegram dibatasi untuk owner.",
            "profile": "Operasi ubah profile Telegram dibatasi untuk owner.",
            "self-review": "Self-review Telegram dibatasi untuk owner karena menulis memory, lessons, dan planner.",
            "agent-loop": "Agent-loop Telegram dibatasi untuk owner karena menulis memory pembelajaran.",
        }

        allowed = read_only_actions.get(prefix)
        if allowed is None:
            if prefix in mutate_denial:
                return mutate_denial[prefix]
            return f"Operasi `{prefix}` tidak diizinkan untuk user Telegram approved."

        if "*" in allowed:
            return None
        if subcommand in allowed:
            return None
        if prefix in mutate_denial:
            return mutate_denial[prefix]
        return f"Subcommand `{prefix} {subcommand or '(default)'}` dibatasi untuk owner Telegram."

    def _record_decision(
        self,
        context: TransportContext | None,
        prefix: str,
        args: str,
        subcommand: str,
        decision: PolicyDecision,
    ) -> PolicyDecision:
        """Persist one policy decision into the shared execution trace."""
        if context and context.source == "telegram":
            append_execution_event(
                "policy_decision",
                trace_id=context.trace_id or new_trace_id(),
                status="allowed" if decision.allowed else "denied",
                source=context.source,
                command=f"{prefix} {args}".strip(),
                data={
                    "prefix": prefix,
                    "subcommand": subcommand,
                    "reason": decision.reason,
                    "roles": list(context.roles),
                    "message": decision.message or "",
                },
            )
        return decision


def _parse_prefix_set(name: str, default: set[str]) -> set[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return set(default)
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _extract_subcommand(args: str) -> str:
    args = args.strip().lower()
    if not args:
        return ""
    return args.split()[0]
