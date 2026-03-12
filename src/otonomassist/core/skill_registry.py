"""Skill registry for managing available skills."""

from collections.abc import Iterator
from typing import TYPE_CHECKING

from otonomassist.models import Skill

if TYPE_CHECKING:
    from otonomassist.models import SkillDefinition


class SkillRegistry:
    """Registry for managing skills."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill."""
        self._skills[skill.name.lower()] = skill

    def unregister(self, name: str) -> bool:
        """Unregister a skill by name."""
        key = name.lower()
        if key in self._skills:
            del self._skills[key]
            return True
        return False

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name.lower())

    def find_by_command(self, command: str) -> tuple[Skill | None, str]:
        """Find a skill that matches the command."""
        for skill in self._skills.values():
            matched, args = skill.definition.match_command(command)
            if matched:
                return skill, args

        return None, ""

    def list_skills(self) -> list["Skill"]:
        """List all registered skills."""
        return list(self._skills.values())

    def get_skill_layer_summary(self) -> dict[str, object]:
        """Summarize loaded skills by autonomous skill-layer taxonomy."""
        categories: dict[str, list[dict[str, object]]] = {}
        for skill in self._skills.values():
            entry = {
                "name": skill.name,
                "category": skill.definition.category,
                "risk_level": skill.definition.risk_level,
                "side_effects": list(skill.definition.side_effects),
                "requires": list(skill.definition.requires),
                "idempotency": skill.definition.idempotency,
                "schema_version": skill.definition.schema_version,
                "timeout_behavior": skill.definition.timeout_behavior,
                "retry_policy": skill.definition.retry_policy,
            }
            categories.setdefault(skill.definition.autonomy_category or "general", []).append(entry)

        for skills in categories.values():
            skills.sort(key=lambda item: str(item["name"]))

        return {
            "category_count": len(categories),
            "skills": categories,
        }

    def __iter__(self) -> Iterator[Skill]:
        return iter(self._skills.values())

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._skills
