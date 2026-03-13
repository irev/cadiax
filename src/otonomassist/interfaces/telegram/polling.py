"""Telegram long-polling interface adapter."""

from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from otonomassist.core.agent_context import DATA_DIR, ensure_agent_storage, get_secret_value
from otonomassist.core.transport import TransportContext
from otonomassist.interfaces.telegram.auth import TelegramAuthService

if TYPE_CHECKING:
    from otonomassist.core.assistant import Assistant


DEFAULT_TELEGRAM_STATE_FILE = DATA_DIR / "telegram_state.json"
DEFAULT_TELEGRAM_AUTH_FILE = DATA_DIR / "telegram_auth.json"


class TelegramPollingTransport:
    """Telegram long-polling adapter with fail-closed authorization."""

    CHAT_ACTION_INTERVAL_SECONDS = 4.0

    def __init__(
        self,
        token: str | None = None,
        poll_timeout: int = 30,
        *,
        state_file: Path | None = None,
        auth_file: Path | None = None,
    ) -> None:
        ensure_agent_storage()
        self.state_file = state_file or DEFAULT_TELEGRAM_STATE_FILE
        self.auth_file = auth_file or DEFAULT_TELEGRAM_AUTH_FILE
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN") or get_secret_value("telegram_bot_token")
        self.poll_timeout = poll_timeout
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self._client = httpx.Client(timeout=max(poll_timeout + 10, 40))
        self.auth = TelegramAuthService.from_config(auth_file=self.auth_file)
        self.owner_ids = self.auth.owner_ids
        self.allow_from = self.auth.allow_from
        self.dm_policy = self.auth.dm_policy
        self.group_policy = self.auth.group_policy
        self.group_allow_from = self.auth.group_allow_from
        self.allowed_groups = self.auth.allowed_groups
        self.require_mention = self.auth.require_mention
        self.bot_username: str | None = None
        self.bot_id: str | None = None

    def is_configured(self) -> bool:
        """Check whether Telegram transport can run."""
        return bool(self.token)

    def run(self, assistant: Assistant) -> None:
        """Start long polling."""
        if not self.is_configured():
            raise RuntimeError(
                "Telegram bot token tidak ditemukan. "
                "Set TELEGRAM_BOT_TOKEN atau simpan via `secrets set telegram_bot_token <token>`."
            )

        self._load_bot_identity()
        offset = self._load_offset()
        while True:
            updates = self._get_updates(offset)
            for update in updates:
                offset = max(offset, update["update_id"] + 1)
                self._save_offset(offset)
                self._handle_update(assistant, update)
            time.sleep(1)

    def _get_updates(self, offset: int) -> list[dict[str, Any]]:
        response = self._client.get(
            f"{self.base_url}/getUpdates",
            params={
                "timeout": self.poll_timeout,
                "offset": offset,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API error: {payload}")
        return payload.get("result", [])

    def _handle_update(self, assistant: Assistant, update: dict[str, Any]) -> None:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return

        text = message.get("text")
        chat = message.get("chat", {})
        chat_id = str(chat.get("id"))
        chat_type = str(chat.get("type", "private"))
        user = message.get("from", {})
        user_id = str(user.get("id")) if user.get("id") is not None else None

        if not text:
            self._send_message(chat_id, "Hanya pesan teks yang didukung saat ini.")
            return

        normalized = text.strip()
        if normalized in {"/myid", "/whoami"}:
            self._send_message(
                chat_id,
                f"user_id: {user_id or '-'}\nchat_id: {chat_id}\nchat_type: {chat_type}",
            )
            return
        if self._handle_control_command(message, chat_id, chat_type, user_id, normalized):
            return

        if not self._is_authorized(message, chat_id, chat_type, user_id, normalized):
            return

        roles = self._resolve_roles(chat_id, user_id)
        with self._chat_action_session(chat_id, action="typing"):
            result = assistant.handle_message(
                normalized,
                TransportContext(source="telegram", user_id=user_id, chat_id=chat_id, roles=roles),
            )
        self._send_message(chat_id, result)

    def _handle_control_command(
        self,
        message: dict[str, Any],
        chat_id: str,
        chat_type: str,
        user_id: str | None,
        text: str,
    ) -> bool:
        if text == "/start":
            if self._is_dm_allowed(chat_id, user_id, silent=True) or self._is_group_allowed(
                message, chat_id, user_id, text, silent=True
            ):
                self._send_message(chat_id, "Autonomiq Telegram siap. Kirim pesan untuk mulai.")
            else:
                self._send_message(chat_id, self.auth.get_start_denied_text())
            return True

        if text == "/help":
            self._send_message(chat_id, self.auth.get_help_text())
            return True

        if text == "/pair":
            self._send_pairing_response(chat_id, chat_type, user_id, message)
            return True

        if text.startswith("/auth"):
            self._handle_auth_command(chat_id, user_id, text)
            return True

        return False

    def _is_authorized(
        self,
        message: dict[str, Any],
        chat_id: str,
        chat_type: str,
        user_id: str | None,
        text: str,
    ) -> bool:
        if chat_type == "private":
            return self._is_dm_allowed(chat_id, user_id)
        return self._is_group_allowed(message, chat_id, user_id, text)

    def _is_dm_allowed(self, chat_id: str, user_id: str | None, silent: bool = False) -> bool:
        allowed, reply = self.auth.is_dm_allowed(chat_id, user_id, silent=silent)
        if not allowed and reply and not silent:
            self._send_message(chat_id, reply)
        return allowed

    def _is_group_allowed(
        self,
        message: dict[str, Any],
        chat_id: str,
        user_id: str | None,
        text: str,
        silent: bool = False,
    ) -> bool:
        allowed, _ = self.auth.is_group_allowed(
            chat_id,
            user_id,
            mentions_bot=self._message_mentions_bot(message, text),
            silent=silent,
        )
        return allowed

    def _group_is_listed(self, chat_id: str) -> bool:
        return self.auth.group_is_listed(chat_id)

    def _sender_is_allowed(self, user_id: str | None) -> bool:
        return self.auth.sender_is_allowed(user_id)

    def _message_mentions_bot(self, message: dict[str, Any], text: str) -> bool:
        if self.bot_username:
            username_mention = f"@{self.bot_username.lower()}"
            for entity in message.get("entities", []) or []:
                if entity.get("type") != "mention":
                    continue
                offset = int(entity.get("offset", 0))
                length = int(entity.get("length", 0))
                fragment = text[offset : offset + length].lower()
                if fragment == username_mention:
                    return True
            if username_mention in text.lower():
                return True

        reply = message.get("reply_to_message") or {}
        reply_from = reply.get("from") or {}
        if self.bot_id and str(reply_from.get("id")) == self.bot_id:
            return True
        return False

    def _effective_dm_allowlist(self) -> set[str]:
        return self.auth.effective_dm_allowlist()

    def _effective_group_allowlist(self) -> set[str]:
        return self.auth.effective_group_allowlist()

    def _resolve_roles(self, chat_id: str, user_id: str | None) -> tuple[str, ...]:
        return self.auth.resolve_roles(chat_id, user_id)

    def _send_pairing_response(
        self,
        chat_id: str,
        chat_type: str,
        user_id: str | None,
        message: dict[str, Any],
    ) -> None:
        self._send_message(
            chat_id,
            self.auth.handle_pairing_command(
                chat_id=chat_id,
                chat_type=chat_type,
                user_id=user_id,
                message=message,
            ),
        )

    def _handle_auth_command(self, chat_id: str, user_id: str | None, text: str) -> None:
        self._send_message(
            chat_id,
            self.auth.handle_auth_command(chat_id=chat_id, user_id=user_id, text=text),
        )

    def _load_bot_identity(self) -> None:
        response = self._client.get(f"{self.base_url}/getMe")
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API error: {payload}")
        result = payload.get("result", {})
        username = result.get("username")
        self.bot_username = username.lower() if username else None
        bot_id = result.get("id")
        self.bot_id = str(bot_id) if bot_id is not None else None

    def _send_message(self, chat_id: str, text: str) -> None:
        chunks = _chunk_text(text, limit=3500)
        for chunk in chunks:
            response = self._client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                },
            )
            response.raise_for_status()

    def _send_chat_action(self, chat_id: str, action: str = "typing") -> None:
        """Send a Telegram chat action like typing for better UX."""
        response = self._client.post(
            f"{self.base_url}/sendChatAction",
            json={
                "chat_id": chat_id,
                "action": action,
            },
        )
        response.raise_for_status()

    @contextmanager
    def _chat_action_session(self, chat_id: str, action: str = "typing"):
        """Keep Telegram chat action alive while a long task is running."""
        stop_event = threading.Event()
        worker = threading.Thread(
            target=self._chat_action_pulse_loop,
            args=(chat_id, action, stop_event),
            daemon=True,
        )
        worker.start()
        try:
            yield
        finally:
            stop_event.set()
            worker.join(timeout=self.CHAT_ACTION_INTERVAL_SECONDS + 1.0)

    def _chat_action_pulse_loop(self, chat_id: str, action: str, stop_event: threading.Event) -> None:
        """Send chat action immediately, then refresh it until stopped."""
        while not stop_event.is_set():
            try:
                self._send_chat_action(chat_id, action=action)
            except Exception:
                return
            if stop_event.wait(self.CHAT_ACTION_INTERVAL_SECONDS):
                return

    def _load_offset(self) -> int:
        if not self.state_file.exists():
            return 0
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
            return int(payload.get("offset", 0))
        except (ValueError, json.JSONDecodeError):
            return 0

    def _save_offset(self, offset: int) -> None:
        self.state_file.write_text(
            json.dumps({"offset": offset}, indent=2),
            encoding="utf-8",
        )


def _chunk_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks
