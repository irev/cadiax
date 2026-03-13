"""Runtime interaction context shared across nested command execution."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Iterator


_CURRENT_INTERACTION: ContextVar[dict[str, Any] | None] = ContextVar(
    "cadiax_current_interaction",
    default=None,
)


def get_current_interaction_context() -> dict[str, Any]:
    """Return the current interaction context, if any."""
    return dict(_CURRENT_INTERACTION.get() or {})


@contextmanager
def bind_interaction_context(
    *,
    source: str = "cli",
    user_id: str | None = None,
    chat_id: str | None = None,
    session_id: str | None = None,
    identity_id: str | None = None,
    roles: tuple[str, ...] = (),
    trace_id: str | None = None,
    session_mode: str = "main",
    agent_scope: str = "default",
) -> Iterator[None]:
    """Bind one interaction context for nested runtime calls."""
    payload = {
        "source": str(source or "cli").strip() or "cli",
        "user_id": user_id,
        "chat_id": chat_id,
        "session_id": session_id,
        "identity_id": identity_id,
        "roles": tuple(roles or ()),
        "trace_id": trace_id,
        "session_mode": str(session_mode or "main").strip().lower() or "main",
        "agent_scope": str(agent_scope or "default").strip().lower() or "default",
    }
    token: Token = _CURRENT_INTERACTION.set(payload)
    try:
        yield
    finally:
        _CURRENT_INTERACTION.reset(token)
