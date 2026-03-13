"""Telegram interface auth, pairing, and allowlist service."""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import cadiax.core.agent_context as agent_context


class TelegramAuthService:
    """Resolve Telegram auth, pairing, allowlist, and role decisions."""

    def __init__(
        self,
        *,
        auth_file: Path,
        owner_ids: set[str],
        allow_from: set[str],
        dm_policy: str,
        group_policy: str,
        group_allow_from: set[str],
        allowed_groups: set[str],
        require_mention: bool,
    ) -> None:
        self.auth_file = auth_file
        self.owner_ids = set(owner_ids)
        self.allow_from = set(allow_from)
        self.dm_policy = dm_policy.strip().lower() or "pairing"
        self.group_policy = group_policy.strip().lower() or "allowlist"
        self.group_allow_from = set(group_allow_from)
        self.allowed_groups = set(allowed_groups)
        self.require_mention = bool(require_mention)
        self.ensure_auth_state()

    @classmethod
    def from_config(
        cls,
        env_values: Mapping[str, str] | None = None,
        *,
        auth_file: Path | None = None,
    ) -> "TelegramAuthService":
        """Build one Telegram auth service from env-like config values."""
        values = {key: value or "" for key, value in (env_values or os.environ).items()}
        return cls(
            auth_file=auth_file or (agent_context.DATA_DIR / "telegram_auth.json"),
            owner_ids=_parse_allowed_chat_ids(values.get("TELEGRAM_OWNER_IDS", "")),
            allow_from=_parse_allowed_chat_ids(values.get("TELEGRAM_ALLOW_FROM", "")),
            dm_policy=(values.get("TELEGRAM_DM_POLICY") or "pairing").strip().lower() or "pairing",
            group_policy=(values.get("TELEGRAM_GROUP_POLICY") or "allowlist").strip().lower() or "allowlist",
            group_allow_from=_parse_allowed_chat_ids(values.get("TELEGRAM_GROUP_ALLOW_FROM", "")),
            allowed_groups=_parse_allowed_chat_ids(values.get("TELEGRAM_GROUPS", "")),
            require_mention=_parse_bool(values.get("TELEGRAM_REQUIRE_MENTION", "true")),
        )

    def get_diagnostics(self) -> dict[str, object]:
        """Return machine-readable Telegram interface auth diagnostics."""
        state = self.load_auth_state()
        return {
            "auth_file": str(self.auth_file),
            "owner_ids": sorted(self.owner_ids),
            "allow_from": sorted(self.allow_from),
            "group_allow_from": sorted(self.group_allow_from),
            "allowed_groups": sorted(self.allowed_groups),
            "dm_policy": self.dm_policy,
            "group_policy": self.group_policy,
            "require_mention": self.require_mention,
            "approved_users": len(state.get("approved_users", [])),
            "approved_groups": len(state.get("approved_groups", [])),
            "pending_requests": len(state.get("pending_requests", [])),
        }

    def get_help_text(self) -> str:
        """Return Telegram control command help text."""
        return (
            "Gunakan pesan biasa untuk berinteraksi.\n"
            "- `/myid`: tampilkan user_id dan chat_id\n"
            "- `/pair`: minta akses DM bila policy pairing aktif\n"
            "- `/auth ...`: owner-only untuk approve/revoke akses Telegram"
        )

    def get_start_denied_text(self) -> str:
        """Return the default denied text for /start when access is not yet active."""
        return (
            "Akses Telegram dibatasi. Gunakan `/myid` lalu `/pair` di DM, "
            "atau minta owner menambahkan user/chat Anda."
        )

    def is_authorized(
        self,
        *,
        chat_id: str,
        chat_type: str,
        user_id: str | None,
        mentions_bot: bool,
        silent: bool = False,
    ) -> tuple[bool, str | None]:
        """Check whether the inbound Telegram message is authorized."""
        if chat_type == "private":
            return self.is_dm_allowed(chat_id, user_id, silent=silent)
        return self.is_group_allowed(chat_id, user_id, mentions_bot=mentions_bot, silent=silent)

    def is_dm_allowed(
        self,
        chat_id: str,
        user_id: str | None,
        *,
        silent: bool = False,
    ) -> tuple[bool, str | None]:
        """Check DM access under current Telegram auth policy."""
        if self.dm_policy == "open":
            return True, None
        if self.dm_policy == "disabled":
            return False, None if silent else "DM ke bot ini dinonaktifkan."

        principals = {value for value in {chat_id, user_id} if value}
        if self.dm_policy == "owner":
            allowed = bool(principals & self.owner_ids)
            if allowed:
                return True, None
            return False, None if silent else "Anda tidak diizinkan menggunakan bot ini."

        allowlist = self.effective_dm_allowlist()
        allowed = bool(principals & allowlist)
        if allowed:
            return True, None
        if silent:
            return False, None
        if self.dm_policy == "pairing":
            return (
                False,
                "Anda belum diizinkan menggunakan bot ini. "
                "Kirim `/pair` dari DM untuk membuat request akses.",
            )
        return False, "Anda tidak ada di allowlist bot ini."

    def is_group_allowed(
        self,
        chat_id: str,
        user_id: str | None,
        *,
        mentions_bot: bool,
        silent: bool = False,
    ) -> tuple[bool, str | None]:
        """Check group/chat access under current Telegram auth policy."""
        if self.group_policy == "disabled":
            return False, None

        group_is_listed = self.group_is_listed(chat_id)
        sender_allowed = self.sender_is_allowed(user_id)

        if not group_is_listed:
            if not silent and chat_id not in self.effective_group_allowlist():
                return False, None
            return False, None
        if self.group_policy == "allowlist" and not sender_allowed:
            return False, None
        if self.require_mention and not mentions_bot:
            return False, None
        return True, None

    def effective_dm_allowlist(self) -> set[str]:
        """Return effective DM allowlist including owners and approved users."""
        state = self.load_auth_state()
        approved = set(state.get("approved_users", []))
        return self.owner_ids | self.allow_from | approved

    def effective_group_allowlist(self) -> set[str]:
        """Return effective group allowlist including approved groups."""
        state = self.load_auth_state()
        approved = set(state.get("approved_groups", []))
        return self.allowed_groups | approved

    def group_is_listed(self, chat_id: str) -> bool:
        """Return whether one Telegram group/chat is on the allowlist."""
        groups = self.effective_group_allowlist()
        if not groups:
            return False
        return "*" in groups or chat_id in groups

    def sender_is_allowed(self, user_id: str | None) -> bool:
        """Return whether the Telegram sender is individually allowed."""
        if user_id is None:
            return False
        if user_id in self.owner_ids:
            return True
        allowed = self.effective_dm_allowlist() | self.group_allow_from
        return user_id in allowed

    def resolve_roles(self, chat_id: str, user_id: str | None) -> tuple[str, ...]:
        """Resolve runtime transport roles for one Telegram principal."""
        roles: list[str] = ["telegram"]
        principals = {value for value in {chat_id, user_id} if value}
        if principals & self.owner_ids:
            roles.append("owner")
        allowed_dm, _ = self.is_dm_allowed(chat_id, user_id, silent=True)
        if allowed_dm or user_id in self.group_allow_from:
            roles.append("approved")
        return tuple(dict.fromkeys(roles))

    def handle_pairing_command(
        self,
        *,
        chat_id: str,
        chat_type: str,
        user_id: str | None,
        message: dict[str, Any],
    ) -> str:
        """Handle `/pair` and return the user-facing response text."""
        if chat_type != "private":
            return "Gunakan `/pair` melalui DM ke bot, bukan dari grup."
        if user_id is None:
            return "Telegram user_id tidak ditemukan."
        if self.dm_policy != "pairing":
            return "Policy pairing tidak aktif untuk bot ini."
        if self.is_dm_allowed(chat_id, user_id, silent=True)[0]:
            return "Akses Anda sudah aktif. Anda bisa langsung mengirim pesan."

        state = self.load_auth_state()
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
            self.save_auth_state(state)

        return (
            "Request akses dicatat.\n"
            f"- request_id: {request_id}\n"
            f"- user_id: {user_id}\n"
            "Minta owner menjalankan `/auth approve "
            f"{request_id}` dari Telegram owner yang terdaftar."
        )

    def handle_auth_command(self, *, chat_id: str, user_id: str | None, text: str) -> str:
        """Handle `/auth ...` and return the response text."""
        if user_id not in self.owner_ids:
            return "Command `/auth` hanya untuk owner bot."

        parts = text.split()
        if len(parts) == 1:
            return (
                "Gunakan `/auth status`, `/auth pending`, `/auth approve <request_id>`, "
                "`/auth reject <request_id>`, `/auth allow-user <user_id>`, "
                "`/auth revoke-user <user_id>`, `/auth allow-group <chat_id>`, "
                "atau `/auth revoke-group <chat_id>`."
            )

        action = parts[1].lower()
        arg = parts[2] if len(parts) > 2 else None
        state = self.load_auth_state()

        if action == "status":
            return "\n".join(
                [
                    "Telegram authorization status:",
                    f"- dm_policy: {self.dm_policy}",
                    f"- group_policy: {self.group_policy}",
                    f"- owners: {', '.join(sorted(self.owner_ids)) or '-'}",
                    f"- approved_users: {', '.join(state.get('approved_users', [])) or '-'}",
                    f"- approved_groups: {', '.join(state.get('approved_groups', [])) or '-'}",
                    f"- pending_requests: {len(state.get('pending_requests', []))}",
                ]
            )

        if action == "pending":
            pending = state.get("pending_requests", [])
            if not pending:
                return "Tidak ada request pairing yang pending."
            lines = ["Pending pairing requests:"]
            for item in pending[:20]:
                identity = item.get("username") or item.get("full_name") or item.get("user_id")
                lines.append(
                    f"- {item.get('request_id')}: user_id={item.get('user_id')} identitas={identity}"
                )
            return "\n".join(lines)

        if action == "approve" and arg:
            request = self._pop_pending_request(state, arg)
            if not request:
                return f"Request `{arg}` tidak ditemukan."
            approved = state.setdefault("approved_users", [])
            if request["user_id"] not in approved:
                approved.append(request["user_id"])
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.save_auth_state(state)
            return f"User {request['user_id']} disetujui untuk akses DM Telegram."

        if action == "reject" and arg:
            request = self._pop_pending_request(state, arg)
            if not request:
                return f"Request `{arg}` tidak ditemukan."
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.save_auth_state(state)
            return f"Request `{arg}` ditolak."

        if action == "allow-user" and arg:
            approved = state.setdefault("approved_users", [])
            if arg not in approved:
                approved.append(arg)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.save_auth_state(state)
            return f"User {arg} ditambahkan ke allowlist Telegram."

        if action == "revoke-user" and arg:
            state["approved_users"] = [item for item in state.get("approved_users", []) if item != arg]
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.save_auth_state(state)
            return f"User {arg} dihapus dari allowlist Telegram."

        if action == "allow-group" and arg:
            groups = state.setdefault("approved_groups", [])
            if arg not in groups:
                groups.append(arg)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.save_auth_state(state)
            return f"Group/chat {arg} ditambahkan ke allowlist Telegram."

        if action == "revoke-group" and arg:
            state["approved_groups"] = [item for item in state.get("approved_groups", []) if item != arg]
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.save_auth_state(state)
            return f"Group/chat {arg} dihapus dari allowlist Telegram."

        return "Command auth tidak dikenali atau argumen kurang lengkap."

    def ensure_auth_state(self) -> None:
        """Create the Telegram auth state file if missing."""
        self.auth_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.auth_file.exists():
            self.auth_file.write_text(
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

    def load_auth_state(self) -> dict[str, Any]:
        """Load the Telegram auth state from disk."""
        self.ensure_auth_state()
        try:
            return json.loads(self.auth_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "approved_users": [],
                "approved_groups": [],
                "pending_requests": [],
            }

    def save_auth_state(self, state: dict[str, Any]) -> None:
        """Persist the Telegram auth state."""
        self.ensure_auth_state()
        self.auth_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _pop_pending_request(self, state: dict[str, Any], request_id: str) -> dict[str, Any] | None:
        pending = state.setdefault("pending_requests", [])
        for index, item in enumerate(pending):
            if item.get("request_id") == request_id:
                return pending.pop(index)
        return None


def _parse_allowed_chat_ids(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}
