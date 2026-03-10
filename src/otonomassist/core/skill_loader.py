"""Skill loader for loading skills from markdown files."""

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from otonomassist.models import Skill, SkillDefinition

if TYPE_CHECKING:
    from otonomassist.core.skill_registry import SkillRegistry


class SkillLoader:
    """Loads skills from markdown files."""

    METADATA_PATTERN = re.compile(r"^- (\w+):\s*(.+)$", re.MULTILINE)
    TRIGGER_PATTERN = re.compile(r"^- (.+)$", re.MULTILINE)
    CODE_BLOCK_PATTERN = re.compile(
        r"```python\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE
    )

    def __init__(self, skills_dir: Path | None = None) -> None:
        if skills_dir is None:
            self.skills_dir = Path("skills")
        else:
            self.skills_dir = Path(skills_dir)

    def load_from_file(self, file_path: Path) -> Skill | None:
        """Load a single skill from a markdown file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            return self.parse_skill(content, file_path.stem)
        except Exception as e:
            print(f"Error loading skill from {file_path}: {e}", file=sys.stderr)
            return None

    def load_all(self, registry: "SkillRegistry") -> int:
        """Load all skills from the skills directory."""
        if not self.skills_dir.exists():
            print(f"Skills directory not found: {self.skills_dir}")
            return 0

        count = 0
        for file_path in self.skills_dir.glob("*.md"):
            skill = self.load_from_file(file_path)
            if skill:
                registry.register(skill)
                count += 1

        return count

    def parse_skill(self, content: str, fallback_name: str) -> Skill:
        """Parse skill definition from markdown content."""
        lines = content.split("\n")

        name = fallback_name
        description = ""
        aliases: list[str] = []
        category = "general"
        triggers: list[str] = []
        handler_code = ""
        response_template = "{result}"

        in_metadata = False
        in_handlers = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            if line_stripped == "## Metadata":
                in_metadata = True
                continue
            elif line_stripped == "## Triggers":
                in_metadata = False
                in_handlers = True
                continue
            elif line_stripped.startswith("##"):
                in_metadata = False
                in_handlers = False

            if in_metadata:
                match = self.METADATA_PATTERN.match(line)
                if match:
                    key, value = match.groups()
                    if key == "name":
                        name = value.strip()
                    elif key == "description":
                        description = value.strip()
                    elif key == "aliases":
                        aliases = self._parse_list(value)
                    elif key == "category":
                        category = value.strip()

            if in_handlers:
                match = self.TRIGGER_PATTERN.match(line)
                if match:
                    trigger = match.group(1).strip().strip('"').strip("'")
                    triggers.append(trigger)

        code_match = self.CODE_BLOCK_PATTERN.search(content)
        if code_match:
            handler_code = code_match.group(1).strip()

        if not description:
            description = self._extract_description(content)

        definition = SkillDefinition(
            name=name,
            description=description,
            aliases=aliases,
            category=category,
            triggers=triggers,
            handler_code=handler_code,
            response_template=response_template,
        )

        handler, is_async = self._compile_handler(handler_code, name)

        return Skill(definition=definition, handler=handler, is_async=is_async)

    def _parse_list(self, value: str) -> list[str]:
        """Parse a list from string format."""
        if value.startswith("[") and value.endswith("]"):
            items = value[1:-1].split(",")
            return [item.strip().strip("'\"") for item in items]
        return [value.strip()]

    def _extract_description(self, content: str) -> str:
        """Extract description from first paragraph."""
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                return line[:200]
        return "No description"

    def _compile_handler(self, code: str, skill_name: str):
        """Compile handler code to executable function."""
        if not code:
            return (lambda args: f"Skill '{skill_name}' has no handler", False)

        local_vars: dict[str, object] = {}
        try:
            exec(code, {"__builtins__": __builtins__}, local_vars)
            handler = local_vars.get("handle")
            if handler and callable(handler):
                import inspect
                is_async = inspect.iscoroutinefunction(handler)
                return (handler, is_async)
        except Exception as e:
            print(f"Error compiling handler for {skill_name}: {e}", file=sys.stderr)

        return (lambda args: f"Skill '{skill_name}' handler error", False)
