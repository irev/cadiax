"""Telegram long-polling transport."""

from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any
from datetime import datetime, timezone
import secrets

import httpx

from otonomassist.core import Assistant, TransportContext, ensure_agent_storage
from otonomassist.core.agent_context import DATA_DIR, get_secret_value


TELEGRAM_STATE_FILE = DATA_DIR / "telegram_state.json"
TELEGRAM_AUTH_FILE = DATA_DIR / "telegram_auth.json"


class TelegramPollingTransport:
    """Telegram long-polling adapter with fail-closed authorization."""

    def __init__(
        self,
        token: str | None = None,
        poll_timeout: int = 30,
    ) -> None:
        ensure_agent_storage()
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN") or get_secret_value("telegram_bot_token")
        self.poll_timeout = poll_timeout
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self._client = httpx.Client(timeout=max(poll_timeout + 10, 40))
        self.owner_ids = _parse_allowed_chat_ids(os.getenv("TELEGRAM_OWNER_IDS", ""))
        self.allow_from = _parse_allowed_chat_ids(os.getenv("TELEGRAM_ALLOW_FROM", ""))
        self.dm_policy = os.getenv("TELEGRAM_DM_POLICY", "pairing").strip().lower() or "pairing"
        self.group_policy = os.getenv("TELEGRAM_GROUP_POLICY", "allowlist").strip().lower() or "allowlist"
        self.group_allow_from = _parse_allowed_chat_ids(os.getenv("TELEGRAM_GROUP_ALLOW_FROM", ""))
        self.allowed_groups = _parse_allowed_chat_ids(os.getenv("TELEGRAM_GROUPS", ""))
        self.require_mention = _parse_bool(os.getenv("TELEGRAM_REQUIRE_MENTION", "true"))
        self.bot_username: str | None = None
        self.bot_id: str | None = None
        _ensure_auth_state()

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
                self._send_message(chat_id, "OtonomAssist Telegram siap. Kirim pesan untuk mulai.")
            else:
                self._send_message(
                    chat_id,
                    "Akses Telegram dibatasi. Gunakan `/myid` lalu `/pair` di DM, "
                    "atau minta owner menambahkan user/chat Anda.",
                )
            return True

        if text == "/help":
            self._send_message(
                chat_id,
                "Gunakan pesan biasa untuk berinteraksi.\n"
                "- `/myid`: tampilkan user_id dan chat_id\n"
                "- `/pair`: minta akses DM bila policy pairing aktif\n"
                "- `/auth ...`: owner-only untuk approve/revoke akses Telegram",
            )
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
        if self.dm_policy == "open":
            return True
        if self.dm_policy == "disabled":
            if not silent:
                self._send_message(chat_id, "DM ke bot ini dinonaktifkan.")
            return False

        principals = {value for value in {chat_id, user_id} if value}
        if self.dm_policy == "owner":
            allowed = bool(principals & self.owner_ids)
            if not allowed and not silent:
                self._send_message(chat_id, "Anda tidak diizinkan menggunakan bot ini.")
            return allowed

        allowlist = self._effective_dm_allowlist()
        allowed = bool(principals & allowlist)
        if not allowed:
            if not silent:
                if self.dm_policy == "pairing":
                    self._send_message(
                        chat_id,
                        "Anda belum diizinkan menggunakan bot ini. "
                        "Kirim `/pair` dari DM untuk membuat request akses.",
                    )
                else:
                    self._send_message(chat_id, "Anda tidak ada di allowlist bot ini.")
        return allowed

    def _is_group_allowed(
        self,
        message: dict[str, Any],
        chat_id: str,
        user_id: str | None,
        text: str,
        silent: bool = False,
    ) -> bool:
        if self.group_policy == "disabled":
            return False

        group_is_listed = self._group_is_listed(chat_id)
        sender_allowed = self._sender_is_allowed(user_id)

        if not group_is_listed:
            if not silent and chat_id not in self._effective_group_allowlist():
                return False
            return False

        if self.group_policy == "allowlist" and not sender_allowed:
            return False

        if self.require_mention and not self._message_mentions_bot(message, text):
            return False
        return True

    def _group_is_listed(self, chat_id: str) -> bool:
        groups = self._effective_group_allowlist()
        if not groups:
            return False
        return "*" in groups or chat_id in groups

    def _sender_is_allowed(self, user_id: str | None) -> bool:
        if user_id is None:
            return False
        if user_id in self.owner_ids:
            return True
        allowed = self._effective_dm_allowlist() | self.group_allow_from
        return user_id in allowed

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
        state = _load_auth_state()
        approved = set(state.get("approved_users", []))
        return self.owner_ids | self.allow_from | approved

    def _effective_group_allowlist(self) -> set[str]:
        state = _load_auth_state()
        approved = set(state.get("approved_groups", []))
        return self.allowed_groups | approved

    def _resolve_roles(self, chat_id: str, user_id: str | None) -> tuple[str, ...]:
        roles: list[str] = ["telegram"]
        principals = {value for value in {chat_id, user_id} if value}
        if principals & self.owner_ids:
            roles.append("owner")
        if self._is_dm_allowed(chat_id, user_id, silent=True) or user_id in self.group_allow_from:
            roles.append("approved")
        return tuple(dict.fromkeys(roles))

    def _send_pairing_response(
        self,
        chat_id: str,
        chat_type: str,
        user_id: str | None,
        message: dict[str, Any],
    ) -> None:
        if chat_type != "private":
            self._send_message(chat_id, "Gunakan `/pair` melalui DM ke bot, bukan dari grup.")
            return
        if user_id is None:
            self._send_message(chat_id, "Telegram user_id tidak ditemukan.")
            return
        if self.dm_policy != "pairing":
            self._send_message(chat_id, "Policy pairing tidak aktif untuk bot ini.")
            return
        if self._is_dm_allowed(chat_id, user_id, silent=True):
            self._send_message(chat_id, "Akses Anda sudah aktif. Anda bisa langsung mengirim pesan.")
            return

        state = _load_auth_state()
        pending = state.setdefault("pending_requests", [])
        existing = next((item for item in pending if item.get("user_id") == user_id), None)
        if existing:
            request_id = existing["request_id"]
        else:
            user = message.get("from", {})
            request_id = secrets.token_hex(4)
            pending.append(
                {
                    "request_id": request_id,
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "username": user.get("username") or "",
                    "full_name": " ".join(
                        part for part in [user.get("first_name"), user.get("last_name")] if part
                    ).strip(),
                    "requested_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_auth_state(state)

        self._send_message(
            chat_id,
            "Request akses dicatat.\n"
            f"- request_id: {request_id}\n"
            f"- user_id: {user_id}\n"
            "Minta owner menjalankan `/auth approve "
            f"{request_id}` dari Telegram owner yang terdaftar.",
        )

    def _handle_auth_command(self, chat_id: str, user_id: str | None, text: str) -> None:
        if user_id not in self.owner_ids:
            self._send_message(chat_id, "Command `/auth` hanya untuk owner bot.")
            return

        parts = text.split()
        if len(parts) == 1:
            self._send_message(
                chat_id,
                "Gunakan `/auth status`, `/auth pending`, `/auth approve <request_id>`, "
                "`/auth reject <request_id>`, `/auth allow-user <user_id>`, "
                "`/auth revoke-user <user_id>`, `/auth allow-group <chat_id>`, "
                "atau `/auth revoke-group <chat_id>`.",
            )
            return

        action = parts[1].lower()
        arg = parts[2] if len(parts) > 2 else None
        state = _load_auth_state()

        if action == "status":
            self._send_message(
                chat_id,
                "\n".join(
                    [
                        "Telegram authorization status:",
                        f"- dm_policy: {self.dm_policy}",
                        f"- group_policy: {self.group_policy}",
                        f"- owners: {', '.join(sorted(self.owner_ids)) or '-'}",
                        f"- approved_users: {', '.join(state.get('approved_users', [])) or '-'}",
                        f"- approved_groups: {', '.join(state.get('approved_groups', [])) or '-'}",
                        f"- pending_requests: {len(state.get('pending_requests', []))}",
                    ]
                ),
            )
            return

        if action == "pending":
            pending = state.get("pending_requests", [])
            if not pending:
                self._send_message(chat_id, "Tidak ada request pairing yang pending.")
                return
            lines = ["Pending pairing requests:"]
            for item in pending[:20]:
                identity = item.get("username") or item.get("full_name") or item.get("user_id")
                lines.append(
                    f"- {item.get('request_id')}: user_id={item.get('user_id')} identitas={identity}"
                )
            self._send_message(chat_id, "\n".join(lines))
            return

        if action == "approve" and arg:
            request = self._pop_pending_request(state, arg)
            if not request:
                self._send_message(chat_id, f"Request `{arg}` tidak ditemukan.")
                return
            approved = state.setdefault("approved_users", [])
            if request["user_id"] not in approved:
                approved.append(request["user_id"])
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_auth_state(state)
            self._send_message(
                chat_id,
                f"User {request['user_id']} disetujui untuk akses DM Telegram.",
            )
            return

        if action == "reject" and arg:
            request = self._pop_pending_request(state, arg)
            if not request:
                self._send_message(chat_id, f"Request `{arg}` tidak ditemukan.")
                return
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_auth_state(state)
            self._send_message(chat_id, f"Request `{arg}` ditolak.")
            return

        if action == "allow-user" and arg:
            approved = state.setdefault("approved_users", [])
            if arg not in approved:
                approved.append(arg)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_auth_state(state)
            self._send_message(chat_id, f"User {arg} ditambahkan ke allowlist Telegram.")
            return

        if action == "revoke-user" and arg:
            approved = [item for item in state.get("approved_users", []) if item != arg]
            state["approved_users"] = approved
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_auth_state(state)
            self._send_message(chat_id, f"User {arg} dihapus dari allowlist Telegram.")
            return

        if action == "allow-group" and arg:
            groups = state.setdefault("approved_groups", [])
            if arg not in groups:
                groups.append(arg)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_auth_state(state)
            self._send_message(chat_id, f"Group/chat {arg} ditambahkan ke allowlist Telegram.")
            return

        if action == "revoke-group" and arg:
            groups = [item for item in state.get("approved_groups", []) if item != arg]
            state["approved_groups"] = groups
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_auth_state(state)
            self._send_message(chat_id, f"Group/chat {arg} dihapus dari allowlist Telegram.")
            return

        self._send_message(chat_id, "Command auth tidak dikenali atau argumen kurang lengkap.")

    def _pop_pending_request(self, state: dict[str, Any], request_id: str) -> dict[str, Any] | None:
        pending = state.setdefault("pending_requests", [])
        for index, item in enumerate(pending):
            if item.get("request_id") == request_id:
                return pending.pop(index)
        return None

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

    def _load_offset(self) -> int:
        if not TELEGRAM_STATE_FILE.exists():
            return 0
        try:
            payload = json.loads(TELEGRAM_STATE_FILE.read_text(encoding="utf-8"))
            return int(payload.get("offset", 0))
        except (ValueError, json.JSONDecodeError):
            return 0

    def _save_offset(self, offset: int) -> None:
        TELEGRAM_STATE_FILE.write_text(
            json.dumps({"offset": offset}, indent=2),
            encoding="utf-8",
        )


def _parse_allowed_chat_ids(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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


def _ensure_auth_state() -> None:
    if not TELEGRAM_AUTH_FILE.exists():
        TELEGRAM_AUTH_FILE.write_text(
            json.dumps(
                {
                    "approved_users": [],
                    "approved_groups": [],
                    "pending_requests": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def _load_auth_state() -> dict[str, Any]:
    _ensure_auth_state()
    try:
        return json.loads(TELEGRAM_AUTH_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "approved_users": [],
            "approved_groups": [],
            "pending_requests": [],
        }


def _save_auth_state(state: dict[str, Any]) -> None:
    _ensure_auth_state()
    TELEGRAM_AUTH_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
