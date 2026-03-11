"""Canonical interaction request/response models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(slots=True)
class InteractionRequest:
    """Normalized inbound interaction payload."""

    message: str
    source: str = "api"
    user_id: str | None = None
    session_id: str | None = None
    chat_id: str | None = None
    identity_id: str | None = None
    roles: tuple[str, ...] = ()
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "InteractionRequest":
        """Build a normalized request from a JSON payload."""
        message = str(payload.get("message") or payload.get("text") or "").strip()
        if not message:
            raise ValueError("field `message` is required")

        roles = _normalize_roles(payload.get("roles"))
        metadata = payload.get("metadata")
        return cls(
            message=message,
            source=_coerce_optional_text(payload.get("source")) or "api",
            user_id=_coerce_optional_text(payload.get("user_id")),
            session_id=_coerce_optional_text(payload.get("session_id")),
            chat_id=_coerce_optional_text(payload.get("chat_id")),
            identity_id=_coerce_optional_text(payload.get("identity_id")),
            roles=roles,
            trace_id=_coerce_optional_text(payload.get("trace_id")),
            metadata=metadata if isinstance(metadata, dict) else {},
        )


@dataclass(slots=True)
class InteractionResponse:
    """Structured interaction response returned by the conversation service."""

    response: str
    source: str
    trace_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    chat_id: str | None = None
    identity_id: str | None = None
    status: str = "ok"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the response for API output."""
        return {
            "status": self.status,
            "response": self.response,
            "source": self.source,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "chat_id": self.chat_id,
            "identity_id": self.identity_id,
            "metadata": self.metadata,
        }


def _coerce_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_roles(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(
            item_text
            for item_text in (str(item).strip() for item in value)
            if item_text
        )
    return ()
