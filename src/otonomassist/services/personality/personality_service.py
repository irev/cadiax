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
        state = agent_context.load_preference_state()
        state["preferences"] = preferences
        agent_context.save_preference_state(state)

    def remove_preference(self, text: str) -> bool:
        """Remove one preference item if present."""
        normalized = text.strip()
        if not normalized:
            return False
        state = agent_context.load_preference_state()
        filtered = [
            item for item in self.list_preferences()
            if item.casefold() != normalized.casefold()
        ]
        if len(filtered) == len(self.list_preferences()):
            return False
        state["preferences"] = filtered
        agent_context.save_preference_state(state)
        return True

    def reset_preferences(self) -> None:
        """Clear structured preference items while keeping profile markdown intact."""
        state = agent_context.load_preference_state()
        state["preferences"] = []
        agent_context.save_preference_state(state)

    def update_structured_profile(self, **fields: str | list[str]) -> dict[str, object]:
        """Update structured preference profile fields."""
        state = agent_context.load_preference_state()
        profile = dict(state.get("profile", {}))
        for key, value in fields.items():
            if key == "preferred_channels":
                profile[key] = [
                    str(item).strip()
                    for item in (value if isinstance(value, list) else [])
                    if str(item).strip()
                ]
                continue
            profile[key] = str(value or "").strip()
        state["profile"] = profile
        agent_context.save_preference_state(state)
        return profile

    def get_structured_profile(self) -> dict[str, object]:
        """Return structured personality preference profile."""
        return agent_context.get_preference_profile()

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
        structured = self.get_structured_profile()
        parts.extend(["", "## Preference Profile"])
        if any(structured.values()):
            if structured.get("preferred_channels"):
                parts.append(f"- preferred_channels: {', '.join(structured['preferred_channels'])}")
            if structured.get("preferred_brevity"):
                parts.append(f"- preferred_brevity: {structured['preferred_brevity']}")
            if structured.get("formality"):
                parts.append(f"- formality: {structured['formality']}")
            if structured.get("proactive_mode"):
                parts.append(f"- proactive_mode: {structured['proactive_mode']}")
            if structured.get("summary_style"):
                parts.append(f"- summary_style: {structured['summary_style']}")
        else:
            parts.append("- belum ada profil preferensi terstruktur")
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
