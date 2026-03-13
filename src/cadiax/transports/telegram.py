"""Compatibility shim for the Telegram polling transport."""

from __future__ import annotations

from cadiax.core.agent_context import DATA_DIR
from cadiax.core.transport import TransportContext
from cadiax.interfaces.telegram.polling import TelegramPollingTransport as _TelegramPollingTransport


TELEGRAM_STATE_FILE = DATA_DIR / "telegram_state.json"
TELEGRAM_AUTH_FILE = DATA_DIR / "telegram_auth.json"


class TelegramPollingTransport(_TelegramPollingTransport):
    """Backwards-compatible export that binds legacy patchable state paths."""

    def __init__(self, token: str | None = None, poll_timeout: int = 30) -> None:
        super().__init__(
            token=token,
            poll_timeout=poll_timeout,
            state_file=TELEGRAM_STATE_FILE,
            auth_file=TELEGRAM_AUTH_FILE,
        )


__all__ = [
    "TELEGRAM_AUTH_FILE",
    "TELEGRAM_STATE_FILE",
    "TelegramPollingTransport",
    "TransportContext",
]
