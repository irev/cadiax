"""Transport-agnostic message types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TransportContext:
    """Metadata about the source of an inbound message."""

    source: str = "cli"
    user_id: str | None = None
    chat_id: str | None = None
    roles: tuple[str, ...] = ()
