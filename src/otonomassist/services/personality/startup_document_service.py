"""Workspace startup document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from otonomassist.core import agent_context
from otonomassist.core.workspace_guard import get_workspace_root


class StartupDocumentService:
    """Load workspace startup documents in one canonical order."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root or get_workspace_root()

    def get_snapshot(self, *, session_mode: str = "main", max_chars: int = 700) -> dict[str, Any]:
        """Return startup document snapshot for one session mode."""
        agent_context.ensure_agent_storage()
        normalized_mode = str(session_mode or "main").strip().lower() or "main"
        documents = [
            self._document_payload("agents", self.workspace_root / "AGENTS.md", max_chars=max_chars),
            self._document_payload("soul", self.workspace_root / "SOUL.md", max_chars=max_chars),
            self._document_payload("user", self.workspace_root / "USER.md", max_chars=max_chars),
            self._document_payload("identity", self.workspace_root / "IDENTITY.md", max_chars=max_chars),
            self._document_payload("tools", self.workspace_root / "TOOLS.md", max_chars=max_chars),
        ]
        daily_notes = agent_context.load_recent_workspace_daily_notes(days=2, max_chars=max_chars)
        curated_memory = (
            agent_context.load_workspace_curated_memory(max_chars=max_chars)
            if normalized_mode == "main"
            else ""
        )
        return {
            "session_mode": normalized_mode,
            "documents": documents,
            "daily_notes": daily_notes,
            "curated_memory": curated_memory,
        }

    def build_prompt_block(self, *, session_mode: str = "main", max_chars: int = 700) -> str:
        """Render startup docs as a prompt-ready block."""
        snapshot = self.get_snapshot(session_mode=session_mode, max_chars=max_chars)
        lines = [
            "## Session Startup Docs",
            f"- session_mode: {snapshot['session_mode']}",
        ]
        for item in snapshot["documents"]:
            lines.append(
                f"- {item['name']}: "
                + (item["preview"] if item["preview"] else "belum ada")
            )
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

    def _document_payload(self, name: str, path: Path, *, max_chars: int) -> dict[str, str]:
        if not path.exists():
            return {"name": name, "path": str(path), "preview": ""}
        preview = agent_context.load_markdown(path, max_chars=max_chars)
        return {"name": name, "path": str(path), "preview": preview}
