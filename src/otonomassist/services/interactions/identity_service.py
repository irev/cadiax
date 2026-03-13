"""Durable identity and session resolution for cross-channel continuity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import otonomassist.core.agent_context as agent_context
from otonomassist.services.interactions.models import InteractionRequest


@dataclass(slots=True)
class IdentityResolution:
    """Resolved identity and session for one interaction."""

    identity_id: str
    session_id: str
    identity_created: bool = False
    session_created: bool = False


class IdentitySessionService:
    """Resolve canonical identity and session ids across channels."""

    def resolve(self, request: InteractionRequest) -> IdentityResolution:
        """Resolve and persist identity/session continuity for one request."""
        identities_state = agent_context.load_identity_state()
        sessions_state = agent_context.load_session_state()
        identities = identities_state.setdefault("identities", [])
        sessions = sessions_state.setdefault("sessions", [])
        normalized_scope = str(request.agent_scope or "default").strip().lower() or "default"
        normalized_roles = tuple(
            item_text
            for item_text in (str(item).strip().lower() for item in request.roles)
            if item_text
        )

        principal_keys = self._build_principal_keys(request)
        identity_hint = str(request.metadata.get("identity_hint", "")).strip()
        identity = self._find_identity(identities, principal_keys, identity_hint, request.identity_id)
        identity_created = False
        if identity is None:
            identity_created = True
            identity = {
                "id": request.identity_id or f"identity_{len(identities) + 1}",
                "identity_hint": identity_hint,
                "sources": sorted({request.source}),
                "principals": sorted(principal_keys),
                "created_at": _utc_now_iso(),
                "last_seen_at": _utc_now_iso(),
                "interaction_count": 0,
                "agent_scopes": [normalized_scope],
                "last_agent_scope": normalized_scope,
                "roles": list(normalized_roles),
            }
            identities.append(identity)

        identity["sources"] = sorted(set(identity.get("sources", [])) | {request.source})
        identity["principals"] = sorted(set(identity.get("principals", [])) | principal_keys)
        identity["agent_scopes"] = sorted(
            {
                str(item).strip().lower()
                for item in list(identity.get("agent_scopes", []))
                if str(item).strip()
            }
            | {normalized_scope}
        )
        identity["last_agent_scope"] = normalized_scope
        identity["roles"] = sorted(
            {
                str(item).strip().lower()
                for item in list(identity.get("roles", []))
                if str(item).strip()
            }
            | set(normalized_roles)
        )
        if identity_hint and not str(identity.get("identity_hint", "")).strip():
            identity["identity_hint"] = identity_hint
        identity["last_seen_at"] = _utc_now_iso()
        identity["interaction_count"] = int(identity.get("interaction_count", 0) or 0) + 1

        session = self._find_session(
            sessions,
            source=request.source,
            raw_session_id=request.session_id or request.chat_id or request.user_id or "",
            identity_id=str(identity["id"]),
            agent_scope=normalized_scope,
        )
        session_created = False
        if session is None:
            session_created = True
            session = {
                "id": f"session_{len(sessions) + 1}",
                "identity_id": str(identity["id"]),
                "source": request.source,
                "raw_session_id": request.session_id or request.chat_id or request.user_id or request.source,
                "channel_user_id": request.user_id or "",
                "channel_chat_id": request.chat_id or "",
                "created_at": _utc_now_iso(),
                "last_seen_at": _utc_now_iso(),
                "interaction_count": 0,
                "agent_scope": normalized_scope,
                "roles": list(normalized_roles),
            }
            sessions.append(session)

        session["identity_id"] = str(identity["id"])
        session["channel_user_id"] = request.user_id or str(session.get("channel_user_id", ""))
        session["channel_chat_id"] = request.chat_id or str(session.get("channel_chat_id", ""))
        session["agent_scope"] = normalized_scope
        session["roles"] = sorted(
            {
                str(item).strip().lower()
                for item in list(session.get("roles", []))
                if str(item).strip()
            }
            | set(normalized_roles)
        )
        session["last_seen_at"] = _utc_now_iso()
        session["interaction_count"] = int(session.get("interaction_count", 0) or 0) + 1

        identities_state["updated_at"] = _utc_now_iso()
        sessions_state["updated_at"] = _utc_now_iso()
        agent_context.save_identity_state(identities_state)
        agent_context.save_session_state(sessions_state)

        return IdentityResolution(
            identity_id=str(identity["id"]),
            session_id=str(session["id"]),
            identity_created=identity_created,
            session_created=session_created,
        )

    def get_snapshot(
        self,
        *,
        agent_scope: str | None = None,
        roles: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Return machine-readable snapshot of identity/session continuity state."""
        identities = list(agent_context.load_identity_state().get("identities", []))
        sessions = list(agent_context.load_session_state().get("sessions", []))
        filtered_identities = (
            agent_context.filter_identity_entries_by_scope(
                identities,
                agent_scope=agent_scope or "default",
                roles=roles,
            )
            if agent_scope
            else identities
        )
        filtered_sessions = (
            agent_context.filter_session_entries_by_scope(
                sessions,
                agent_scope=agent_scope or "default",
                roles=roles,
            )
            if agent_scope
            else sessions
        )
        by_scope: dict[str, dict[str, int]] = {}
        for item in filtered_identities:
            scopes = list(item.get("agent_scopes", [])) or [str(item.get("last_agent_scope") or "default")]
            for scope_name in scopes:
                bucket = by_scope.setdefault(str(scope_name), {"identities": 0, "sessions": 0})
                bucket["identities"] += 1
        for item in filtered_sessions:
            scope_name = str(item.get("agent_scope") or "default")
            bucket = by_scope.setdefault(scope_name, {"identities": 0, "sessions": 0})
            bucket["sessions"] += 1
        return {
            "identity_count": len(filtered_identities),
            "session_count": len(filtered_sessions),
            "total_identity_count": len(identities),
            "total_session_count": len(sessions),
            "latest_identity_id": str(filtered_identities[-1].get("id", "")) if filtered_identities else "",
            "latest_session_id": str(filtered_sessions[-1].get("id", "")) if filtered_sessions else "",
            "identities": filtered_identities,
            "sessions": filtered_sessions,
            "by_scope": by_scope,
            "filter_agent_scope": str(agent_scope or ""),
            "filter_roles": list(roles),
        }

    def _find_identity(
        self,
        identities: list[dict[str, Any]],
        principal_keys: set[str],
        identity_hint: str,
        explicit_identity_id: str | None,
    ) -> dict[str, Any] | None:
        if explicit_identity_id:
            found = next((item for item in identities if str(item.get("id", "")) == explicit_identity_id), None)
            if found is not None:
                return found
        if identity_hint:
            found = next(
                (item for item in identities if str(item.get("identity_hint", "")).strip() == identity_hint),
                None,
            )
            if found is not None:
                return found
        for item in identities:
            if principal_keys & set(item.get("principals", [])):
                return item
        return None

    def _find_session(
        self,
        sessions: list[dict[str, Any]],
        *,
        source: str,
        raw_session_id: str,
        identity_id: str,
        agent_scope: str,
    ) -> dict[str, Any] | None:
        if raw_session_id:
            found = next(
                (
                    item for item in sessions
                    if str(item.get("source", "")) == source
                    and str(item.get("raw_session_id", "")) == raw_session_id
                    and str(item.get("agent_scope", "") or "default").strip().lower() == agent_scope
                ),
                None,
            )
            if found is not None:
                return found
        return next(
            (
                item for item in sessions
                if str(item.get("identity_id", "")) == identity_id
                and str(item.get("source", "")) == source
                and str(item.get("agent_scope", "") or "default").strip().lower() == agent_scope
            ),
            None,
        )

    def _build_principal_keys(self, request: InteractionRequest) -> set[str]:
        principals: set[str] = set()
        if request.user_id:
            principals.add(f"{request.source}:user:{request.user_id}")
        if request.chat_id:
            principals.add(f"{request.source}:chat:{request.chat_id}")
        if request.session_id:
            principals.add(f"{request.source}:session:{request.session_id}")
        return principals


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
