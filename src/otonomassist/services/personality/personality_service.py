"""Service boundary for persistent assistant personality."""

from __future__ import annotations

from pathlib import Path

from otonomassist.core import agent_context


class PersonalityService:
    """Manage personality/profile state separately from runtime orchestration."""

    def __init__(self, profile_path: Path | None = None) -> None:
        self.profile_path = profile_path or agent_context.PROFILE_FILE

    def show_profile(self, max_chars: int = 4000) -> str:
        """Return the persisted profile markdown."""
        agent_context.ensure_agent_storage()
        return agent_context.load_markdown(self.profile_path, max_chars=max_chars)

    def set_purpose(self, text: str) -> None:
        """Replace the profile purpose section."""
        agent_context.replace_section(self.profile_path, "Purpose", text.strip())

    def add_preference(self, text: str) -> None:
        """Append one preference item."""
        agent_context.append_markdown_bullet(self.profile_path, "Preferences", text.strip())

    def add_constraint(self, text: str) -> None:
        """Append one constraint item."""
        agent_context.append_markdown_bullet(self.profile_path, "Constraints", text.strip())

    def add_context(self, text: str) -> None:
        """Append one long-term context item."""
        agent_context.append_markdown_bullet(self.profile_path, "Long-term Context", text.strip())

    def build_prompt_block(self, max_chars: int = 1200) -> str:
        """Render the personality block for prompt assembly."""
        return "\n".join(
            [
                "Assistant personality context:",
                "",
                "## Profile",
                self.show_profile(max_chars=max_chars),
            ]
        )
