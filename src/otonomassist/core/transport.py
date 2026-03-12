"""Transport-agnostic message types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TransportContext:
    """Metadata about the source of an inbound message."""

    source: str = "cli"
    user_id: str | None = None
    chat_id: str | None = None
    session_id: str | None = None
    identity_id: str | None = None
    roles: tuple[str, ...] = ()
    trace_id: str | None = None
    session_mode: str = "main"
