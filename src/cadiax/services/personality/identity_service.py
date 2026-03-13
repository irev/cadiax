"""Identity document service."""

from __future__ import annotations

from pathlib import Path

from cadiax.core.agent_context import ensure_agent_storage, load_markdown
from cadiax.core.workspace_guard import get_workspace_root


class IdentityService:
    """Read the assistant identity document from the workspace."""

    def __init__(self, document_path: Path | None = None) -> None:
        self.document_path = document_path or (get_workspace_root() / "IDENTITY.md")

    def show_identity(self, max_chars: int = 1400) -> str:
        """Return the current identity document."""
        ensure_agent_storage()
        if not self.document_path.exists():
            return "- belum ada identitas yang ditetapkan"
        return load_markdown(self.document_path, max_chars=max_chars)

    def build_prompt_block(self, max_chars: int = 900) -> str:
        """Render identity context for prompt assembly."""
        content = self.show_identity(max_chars=max_chars).strip()
        if not content:
            content = "- belum ada identitas yang ditetapkan"
        return "\n".join(
            [
                "## Identity",
                content,
            ]
        )
