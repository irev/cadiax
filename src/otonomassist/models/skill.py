"""Skill models and definitions."""

from dataclasses import dataclass, field
from typing import Any, Callable
import asyncio
import concurrent.futures


@dataclass
class SkillDefinition:
    """Represents a skill definition loaded from markdown."""

    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    category: str = "general"
    autonomy_category: str = "general"
    risk_level: str = "medium"
    side_effects: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    idempotency: str = "unknown"
    triggers: list[str] = field(default_factory=list)
    handler_code: str = ""
    response_template: str = "{result}"
    ai_instructions: str = ""

    def match_command(self, command: str) -> tuple[bool, str]:
        """Check if command matches this skill."""
        command_stripped = command.strip()
        cmd_lower = command_stripped.lower()
        name_lower = self.name.lower()

        if cmd_lower == name_lower:
            return True, ""

        for alias in self.aliases:
            if cmd_lower == alias.lower():
                return True, ""

        for trigger in self.triggers:
            trigger_text = trigger.strip()
            trigger_lower = trigger_text.lower()
            if cmd_lower.startswith(trigger_lower):
                args = command_stripped[len(trigger_text):].strip()
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

    @property
    def autonomy_category(self) -> str:
        return self.definition.autonomy_category

    @property
    def risk_level(self) -> str:
        return self.definition.risk_level

    def run(self, args: str) -> Any:
        """Execute the skill handler and return the raw result."""
        try:
            if self.is_async:
                return self._run_async(self.handler(args))
            return self.handler(args)
        except Exception as e:
            return f"Error executing skill: {str(e)}"

    def execute(self, args: str) -> str:
        """Execute the skill handler and coerce the result to string."""
        result = self.run(args)
        return self.definition.response_template.format(result=result)

    def _run_async(self, coro: Any) -> Any:
        """Run coroutine safely, handling existing event loops."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            def run_in_new_loop() -> Any:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    pending = [
                        task for task in asyncio.all_tasks(new_loop)
                        if not task.done()
                    ]
                    for task in pending:
                        task.cancel()
                    if pending:
                        new_loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                    new_loop.run_until_complete(new_loop.shutdown_default_executor())
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()

        return asyncio.run(coro)
