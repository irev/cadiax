"""Service boundary for persistent assistant personality."""

from __future__ import annotations

from pathlib import Path

from otonomassist.core import agent_context
from otonomassist.services.personality.habit_model_service import HabitModelService


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
        normalized = text.strip()
        if not normalized:
            return
        preferences = self.list_preferences()
        if normalized.casefold() in {item.casefold() for item in preferences}:
            return
        agent_context.append_markdown_bullet(self.profile_path, "Preferences", normalized)
        preferences.append(normalized)
        agent_context.save_preference_state({"preferences": preferences})

    def add_constraint(self, text: str) -> None:
        """Append one constraint item."""
        agent_context.append_markdown_bullet(self.profile_path, "Constraints", text.strip())

    def add_context(self, text: str) -> None:
        """Append one long-term context item."""
        agent_context.append_markdown_bullet(self.profile_path, "Long-term Context", text.strip())

    def build_prompt_block(self, max_chars: int = 1200) -> str:
        """Render the personality block for prompt assembly."""
        parts = [
            "Assistant personality context:",
            "",
            "## Structured Preferences",
        ]
        preferences = self.list_preferences()
        if preferences:
            parts.extend(f"- {item}" for item in preferences[:8])
        else:
            parts.append("- belum ada preference terstruktur")
        habits = HabitModelService().list_habits(limit=3)
        parts.extend(["", "## Habit Signals"])
        if habits:
            parts.extend(f"- {item.get('summary')}" for item in habits)
        else:
            parts.append("- belum ada sinyal kebiasaan yang cukup")
        parts.extend(
            [
                "",
                "## Profile",
                self.show_profile(max_chars=max_chars),
            ]
        )
        return "\n".join(parts)

    def list_preferences(self) -> list[str]:
        """Return structured preferences for prompt assembly."""
        return agent_context.list_preferences()
