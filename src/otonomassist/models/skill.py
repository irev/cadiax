"""Skill models and definitions."""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SkillDefinition:
    """Represents a skill definition loaded from markdown."""

    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    category: str = "general"
    triggers: list[str] = field(default_factory=list)
    handler_code: str = ""
    response_template: str = "{result}"
    ai_instructions: str = ""

    def match_command(self, command: str) -> tuple[bool, str]:
        """Check if command matches this skill."""
        cmd_lower = command.lower().strip()
        name_lower = self.name.lower()

        if cmd_lower == name_lower:
            return True, ""

        for alias in self.aliases:
            if cmd_lower == alias.lower():
                return True, ""

        for trigger in self.triggers:
            trigger_lower = trigger.lower()
            if cmd_lower.startswith(trigger_lower):
                args = cmd_lower[len(trigger_lower):].strip()
                return True, args

        return False, ""


@dataclass
class Skill:
    """Runtime skill with executable handler."""

    definition: SkillDefinition
    handler: Callable[..., Any]
    is_async: bool = False

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def description(self) -> str:
        return self.definition.description

    def execute(self, args: str) -> str:
        """Execute the skill handler."""
        try:
            if self.is_async:
                import asyncio

                result = asyncio.run(self.handler(args))
            else:
                result = self.handler(args)
            return self.definition.response_template.format(result=result)
        except Exception as e:
            return f"Error executing skill: {str(e)}"
