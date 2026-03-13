"""Soul document service."""

from __future__ import annotations

from pathlib import Path

from otonomassist.core.agent_context import ensure_agent_storage, load_markdown
from otonomassist.core.workspace_guard import get_workspace_root


class SoulService:
    """Read the assistant soul document from the workspace."""

    def __init__(self, document_path: Path | None = None) -> None:
        self.document_path = document_path or (get_workspace_root() / "SOUL.md")

    def show_soul(self, max_chars: int = 1400) -> str:
        """Return the current soul document."""
        ensure_agent_storage()
        if not self.document_path.exists():
            return "- belum ada soul layer yang ditetapkan"
        return load_markdown(self.document_path, max_chars=max_chars)

    def build_prompt_block(self, max_chars: int = 900) -> str:
        """Render soul context for prompt assembly."""
        content = self.show_soul(max_chars=max_chars).strip()
        if not content:
            content = "- belum ada soul layer yang ditetapkan"
        return "\n".join(
            [
                "## Soul",
                content,
            ]
        )
