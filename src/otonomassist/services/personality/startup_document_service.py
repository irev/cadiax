"""Workspace startup document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from otonomassist.core import agent_context
from otonomassist.core.workspace_guard import get_workspace_root
from otonomassist.services.personality.agent_scope_service import AgentScopeService


class StartupDocumentService:
    """Load workspace startup documents in one canonical order."""

    SENSITIVE_DOCUMENTS = frozenset({"soul", "user", "identity"})

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root or get_workspace_root()

    def get_snapshot(
        self,
        *,
        session_mode: str = "main",
        agent_scope: str = "default",
        roles: tuple[str, ...] = (),
        max_chars: int = 700,
    ) -> dict[str, Any]:
        """Return startup document snapshot for one session mode."""
        agent_context.ensure_agent_storage()
        normalized_mode = str(session_mode or "main").strip().lower() or "main"
        scope_entry = AgentScopeService().get_scope(agent_scope)
        scope_name = str(scope_entry.get("scope") or "default")
        request_roles = {
            item_text
            for item_text in (str(item).strip().lower() for item in roles)
            if item_text
        }
        documents = [
            self._document_payload(
                "agents",
                self.workspace_root / "AGENTS.md",
                max_chars=max_chars,
                scope_entry=scope_entry,
                request_roles=request_roles,
            ),
            self._document_payload(
                "soul",
                self.workspace_root / "SOUL.md",
                max_chars=max_chars,
                scope_entry=scope_entry,
                request_roles=request_roles,
            ),
            self._document_payload(
                "user",
                self.workspace_root / "USER.md",
                max_chars=max_chars,
                scope_entry=scope_entry,
                request_roles=request_roles,
            ),
            self._document_payload(
                "identity",
                self.workspace_root / "IDENTITY.md",
                max_chars=max_chars,
                scope_entry=scope_entry,
                request_roles=request_roles,
            ),
            self._document_payload(
                "tools",
                self.workspace_root / "TOOLS.md",
                max_chars=max_chars,
                scope_entry=scope_entry,
                request_roles=request_roles,
            ),
        ]
        daily_notes = agent_context.load_recent_workspace_daily_notes(days=2, max_chars=max_chars)
        curated_memory = (
            agent_context.load_workspace_curated_memory(max_chars=max_chars)
            if normalized_mode == "main"
            else ""
        )
        return {
            "session_mode": normalized_mode,
            "agent_scope": scope_name,
            "scope_declared": bool(scope_entry.get("declared", True)),
            "request_roles": sorted(request_roles),
            "documents": documents,
            "daily_notes": daily_notes,
            "curated_memory": curated_memory,
        }

    def build_prompt_block(
        self,
        *,
        session_mode: str = "main",
        agent_scope: str = "default",
        roles: tuple[str, ...] = (),
        max_chars: int = 700,
    ) -> str:
        """Render startup docs as a prompt-ready block."""
        snapshot = self.get_snapshot(
            session_mode=session_mode,
            agent_scope=agent_scope,
            roles=roles,
            max_chars=max_chars,
        )
        lines = [
            "## Session Startup Docs",
            f"- session_mode: {snapshot['session_mode']}",
            f"- agent_scope: {snapshot['agent_scope']}",
        ]
        for item in snapshot["documents"]:
            preview = item["preview"] if item["preview"] else "belum ada"
            if item.get("availability") == "restricted":
                preview = "- dibatasi oleh scope policy"
            lines.append(f"- {item['name']}: {preview}")
        lines.append("")
        lines.append("## Recent Daily Notes")
        lines.append(snapshot["daily_notes"] or "- belum ada daily notes")
        lines.append("")
        lines.append("## Curated Memory Availability")
        if snapshot["session_mode"] == "main":
            lines.append(snapshot["curated_memory"] or "- belum ada curated memory")
        else:
            lines.append("- curated memory tidak dimuat pada shared session")
        return "\n".join(lines)

    def _document_payload(
        self,
        name: str,
        path: Path,
        *,
        max_chars: int,
        scope_entry: dict[str, Any],
        request_roles: set[str],
    ) -> dict[str, str]:
        if self._is_restricted(name, scope_entry, request_roles):
            return {
                "name": name,
                "path": str(path),
                "preview": "",
                "availability": "restricted",
            }
        if not path.exists():
            return {"name": name, "path": str(path), "preview": "", "availability": "missing"}
        preview = agent_context.load_markdown(path, max_chars=max_chars)
        return {"name": name, "path": str(path), "preview": preview, "availability": "available"}

    def _is_restricted(self, name: str, scope_entry: dict[str, Any], request_roles: set[str]) -> bool:
        if name not in self.SENSITIVE_DOCUMENTS:
            return False
        if not bool(scope_entry.get("declared", True)) and str(scope_entry.get("scope") or "default") != "default":
            return True
        allowed_roles = {
            item_text
            for item_text in (str(item).strip().lower() for item in scope_entry.get("allowed_roles", []))
            if item_text
        }
        if not allowed_roles:
            return False
        if request_roles.intersection(allowed_roles):
            return False
        return True
