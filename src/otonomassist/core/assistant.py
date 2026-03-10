"""Core assistant implementation."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from otonomassist.core.skill_loader import SkillLoader
from otonomassist.core.skill_registry import SkillRegistry

if TYPE_CHECKING:
    from otonomassist.models import Skill


class Assistant:
    """Core assistant that manages skills and command execution."""

    def __init__(self, skills_dir: Path | None = None) -> None:
        self.registry = SkillRegistry()
        self.loader = SkillLoader(skills_dir)
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the assistant and load all skills."""
        if self._initialized:
            return

        count = self.loader.load_all(self.registry)
        print(f"Loaded {count} skills", file=sys.stderr)
        self._initialized = True

    def execute(self, command: str) -> str:
        """Execute a command and return the result."""
        if not self._initialized:
            self.initialize()

        if not command.strip():
            return "Please enter a command. Type 'help' for available commands."

        # Built-in commands
        if command.strip().lower() == "help":
            return self.get_help()

        skill, args = self.registry.find_by_command(command)

        if skill:
            return skill.execute(args)

        return self._handle_unknown_command(command)

    def _handle_unknown_command(self, command: str) -> str:
        """Handle unknown commands."""
        return f"Unknown command: '{command}'. Type 'help' to see available commands."

    def list_skills(self) -> list["Skill"]:
        """Get list of available skills."""
        return self.registry.list_skills()

    def get_help(self) -> str:
        """Get help text showing all available commands."""
        skills = self.list_skills()

        if not skills:
            return "No skills available."

        lines = ["Available skills:", ""]
        for skill in skills:
            aliases = ""
            if skill.definition.aliases:
                aliases = f" (alias: {', '.join(skill.definition.aliases)})"
            lines.append(f"- {skill.name}{aliases}: {skill.description}")

        return "\n".join(lines)
