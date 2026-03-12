"""Skill loader for loading skills from directory-based structure.

New format:
skills/
  - <skill_name>/
    - SKILL.md      (metadata and AI instructions)
    - script/       (optional Python/TypeScript handlers)
      - handler.py
"""

import importlib.util
import json
import re
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from otonomassist.core.external_assets import get_external_skills_dir, is_external_skill_approved
from otonomassist.models import Skill, SkillDefinition
from otonomassist.platform import run_process

if TYPE_CHECKING:
    from otonomassist.core.skill_registry import SkillRegistry


class SkillLoader:
    """Loads skills from directory-based skill files."""

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

    def load_all(self, registry: "SkillRegistry") -> int:
        """Load all skills from the skills directory."""
        if not self.skills_dir.exists():
            print(f"Skills directory not found: {self.skills_dir}")
            return 0

        count = 0

        # Check for directory-based skills first
        for entry in self.skills_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("__"):
                if self._is_unapproved_external_skill(entry):
                    print(f"Skipping unapproved external skill: {entry.name}", file=sys.stderr)
                    continue
                skill = self._load_skill_from_directory(entry)
                if skill:
                    registry.register(skill)
                    count += 1

        # Fallback: check for legacy flat .md files
        for file_path in self.skills_dir.glob("*.md"):
            skill = self._load_legacy_skill(file_path)
            if skill:
                registry.register(skill)
                count += 1

        return count

    def _is_unapproved_external_skill(self, skill_dir: Path) -> bool:
        """Return True when a skill dir is external and not approved for loading."""
        try:
            external_root = get_external_skills_dir().resolve()
            resolved = skill_dir.resolve()
        except OSError:
            return False
        if resolved == external_root or external_root not in resolved.parents:
            return False
        return not is_external_skill_approved(resolved)

    def _load_skill_from_directory(self, skill_dir: Path) -> Skill | None:
        """Load a skill from a directory structure."""
        skill_name = skill_dir.name
        skill_md = skill_dir / "SKILL.md"

        if not skill_md.exists():
            print(f"SKILL.md not found in {skill_dir}", file=sys.stderr)
            return None

        try:
            content = skill_md.read_text(encoding="utf-8")
            return self._parse_skill_directory(content, skill_name, skill_dir)
        except Exception as e:
            print(f"Error loading skill from {skill_dir}: {e}", file=sys.stderr)
            return None

    def _parse_skill_directory(
        self, content: str, skill_name: str, skill_dir: Path
    ) -> Skill:
        """Parse skill definition from SKILL.md content."""
        name = skill_name
        description = ""
        aliases: list[str] = []
        category = "general"
        autonomy_category = "general"
        risk_level = "medium"
        side_effects: list[str] = []
        requires: list[str] = []
        idempotency = "unknown"
        schema_version = "v1"
        timeout_behavior = "fail_fast"
        retry_policy = "none"
        triggers: list[str] = []
        ai_instructions = ""

        in_metadata = False
        in_ai_instructions = False
        in_triggers = False

        lines = content.split("\n")
        for line in lines:
            line_stripped = line.strip()

            if line_stripped == "## Metadata":
                in_metadata = True
                in_ai_instructions = False
                in_triggers = False
                continue
            elif line_stripped == "## AI Instructions":
                in_metadata = False
                in_ai_instructions = True
                in_triggers = False
                continue
            elif line_stripped == "## Triggers":
                in_metadata = False
                in_ai_instructions = False
                in_triggers = True
                continue
            elif line_stripped.startswith("##"):
                in_metadata = False
                in_ai_instructions = False
                in_triggers = False

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
                    elif key == "autonomy_category":
                        autonomy_category = value.strip()
                    elif key == "risk_level":
                        risk_level = value.strip()
                    elif key == "side_effects":
                        side_effects = self._parse_list(value)
                    elif key == "requires":
                        requires = self._parse_list(value)
                    elif key == "idempotency":
                        idempotency = value.strip()
                    elif key == "schema_version":
                        schema_version = value.strip()
                    elif key == "timeout_behavior":
                        timeout_behavior = value.strip()
                    elif key == "retry_policy":
                        retry_policy = value.strip()

            elif in_ai_instructions:
                ai_instructions += line + "\n"

            elif in_triggers:
                match = self.TRIGGER_PATTERN.match(line)
                if match:
                    trigger = match.group(1).strip().strip('"').strip("'")
                    triggers.append(trigger)

        if not description:
            description = self._extract_description(content)

        # Load handler from script/handler.py
        handler, is_async = self._load_handler_from_directory(skill_dir, name)

        definition = SkillDefinition(
            name=name,
            description=description,
            aliases=aliases,
            category=category,
            autonomy_category=autonomy_category,
            risk_level=risk_level,
            side_effects=side_effects,
            requires=requires,
            idempotency=idempotency,
            schema_version=schema_version,
            timeout_behavior=timeout_behavior,
            retry_policy=retry_policy,
            triggers=triggers,
            handler_code="",
            response_template="{result}",
            ai_instructions=ai_instructions.strip(),
        )

        return Skill(definition=definition, handler=handler, is_async=is_async)

    def _load_handler_from_directory(
        self, skill_dir: Path, skill_name: str
    ) -> tuple[Any, bool]:
        """Load handler from script/handler.py."""
        handler_path = skill_dir / "script" / "handler.py"

        if not handler_path.exists():
            return (
                lambda args: f"Skill '{skill_name}' has no handler",
                False,
            )

        if self._is_external_skill_directory(skill_dir):
            return self._build_external_handler(skill_dir, handler_path, skill_name), False

        try:
            # Load module from file path
            spec = importlib.util.spec_from_file_location(
                f"skill_{skill_name}", handler_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "handle") and callable(module.handle):
                    import inspect

                    is_async = inspect.iscoroutinefunction(module.handle)
                    return module.handle, is_async
        except Exception as e:
            print(f"Error loading handler for {skill_name}: {e}", file=sys.stderr)

        return (
            lambda args: f"Skill '{skill_name}' handler error",
            False,
        )

    def _is_external_skill_directory(self, skill_dir: Path) -> bool:
        """Return True when a skill directory lives under workspace external skills."""
        try:
            external_root = get_external_skills_dir().resolve()
            resolved = skill_dir.resolve()
        except OSError:
            return False
        return resolved == external_root or external_root in resolved.parents

    def _build_external_handler(self, skill_dir: Path, handler_path: Path, skill_name: str):
        """Wrap external skills in an isolated subprocess runner."""
        runner_path = Path(__file__).resolve().parents[1] / "platform" / "external_skill_runner.py"

        def _invoke(args: str) -> Any:
            command = [
                sys.executable,
                str(runner_path),
                "--handler",
                str(handler_path),
                "--skill-dir",
                str(skill_dir),
                "--args",
                args,
            ]
            env = os.environ.copy()
            src_root = str(Path(__file__).resolve().parents[2])
            existing_pythonpath = env.get("PYTHONPATH", "").strip()
            env["PYTHONPATH"] = src_root if not existing_pythonpath else f"{src_root}{os.pathsep}{existing_pythonpath}"
            result = run_process(
                command,
                cwd=skill_dir,
                timeout_seconds=120.0,
                env=env,
            )
            payload_text = str(result.get("stdout") or "").strip()
            payload: dict[str, Any] = {}
            if payload_text:
                try:
                    payload = json.loads(payload_text)
                except json.JSONDecodeError:
                    payload = {}
            if not result.get("ok") or not payload.get("ok"):
                detail = str(payload.get("error") or result.get("stderr") or payload_text or "unknown external skill error").strip()
                return f"Error executing skill: {detail}"
            return payload.get("result")

        return _invoke

    def _load_legacy_skill(self, file_path: Path) -> Skill | None:
        """Load a skill from legacy flat .md file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            return self._parse_legacy_skill(content, file_path.stem)
        except Exception as e:
            print(f"Error loading skill from {file_path}: {e}", file=sys.stderr)
            return None

    def _parse_legacy_skill(self, content: str, fallback_name: str) -> Skill:
        """Parse legacy skill format for backward compatibility."""
        lines = content.split("\n")

        name = fallback_name
        description = ""
        aliases: list[str] = []
        category = "general"
        autonomy_category = "general"
        risk_level = "medium"
        side_effects: list[str] = []
        requires: list[str] = []
        idempotency = "unknown"
        schema_version = "v1"
        timeout_behavior = "fail_fast"
        retry_policy = "none"
        triggers: list[str] = []
        handler_code = ""
        response_template = "{result}"

        in_metadata = False
        in_handlers = False

        for line in lines:
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
                    elif key == "autonomy_category":
                        autonomy_category = value.strip()
                    elif key == "risk_level":
                        risk_level = value.strip()
                    elif key == "side_effects":
                        side_effects = self._parse_list(value)
                    elif key == "requires":
                        requires = self._parse_list(value)
                    elif key == "idempotency":
                        idempotency = value.strip()
                    elif key == "schema_version":
                        schema_version = value.strip()
                    elif key == "timeout_behavior":
                        timeout_behavior = value.strip()
                    elif key == "retry_policy":
                        retry_policy = value.strip()

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
            autonomy_category=autonomy_category,
            risk_level=risk_level,
            side_effects=side_effects,
            requires=requires,
            idempotency=idempotency,
            schema_version=schema_version,
            timeout_behavior=timeout_behavior,
            retry_policy=retry_policy,
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
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith("#") and not line_stripped.startswith("-"):
                return line_stripped[:200]
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
