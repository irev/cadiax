"""Prompt context budgeting for orchestration and reasoning surfaces."""

from __future__ import annotations

import os

from otonomassist.core.agent_context import build_runtime_context_block
from otonomassist.services.personality import PersonalityService
from otonomassist.services.runtime.redaction_policy import RedactionPolicy, SECRET_PATTERNS


class ContextBudgeter:
    """Compose prompt context blocks under configurable character budgets."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        self.env = env or dict(os.environ)
        self.redaction_policy = RedactionPolicy(self.env)

    def build_orchestration_context(
        self,
        *,
        command: str,
        skills_context: str,
        personality_service: PersonalityService,
        session_mode: str = "main",
    ) -> str:
        """Build the assistant orchestration context under active budgets."""
        return self.compose(
            skills_context=skills_context,
            personality_context=personality_service.build_prompt_block(
                max_chars=self.get_profile_max_chars(),
                session_mode=session_mode,
            ),
            runtime_context=build_runtime_context_block(command, session_mode=session_mode),
        )

    def build_general_reasoning_context(
        self,
        *,
        query: str,
        personality_service: PersonalityService,
        session_mode: str = "main",
    ) -> str:
        """Build a general-purpose reasoning context for direct AI skills."""
        return self.compose(
            skills_context="",
            personality_context=personality_service.build_prompt_block(
                max_chars=self.get_profile_max_chars(),
                session_mode=session_mode,
            ),
            runtime_context=build_runtime_context_block(query, session_mode=session_mode),
        )

    def compose(
        self,
        *,
        skills_context: str,
        personality_context: str,
        runtime_context: str,
    ) -> str:
        """Compose prompt sections while enforcing a total context budget."""
        total_budget = self.get_total_budget_chars()
        sections = [
            _truncate(self.redaction_policy.redact_text(skills_context.strip()), self.get_skills_max_chars()),
            _truncate(self.redaction_policy.redact_text(personality_context.strip()), self.get_personality_max_chars()),
            _truncate(self.redaction_policy.redact_text(runtime_context.strip()), self.get_runtime_max_chars()),
        ]
        text = "\n\n".join(section for section in sections if section)
        return _truncate(text, total_budget)

    def get_diagnostics(self) -> dict[str, int]:
        """Return effective context budget settings."""
        return {
            "total_budget_chars": self.get_total_budget_chars(),
            "skills_max_chars": self.get_skills_max_chars(),
            "personality_max_chars": self.get_personality_max_chars(),
            "profile_max_chars": self.get_profile_max_chars(),
            "runtime_max_chars": self.get_runtime_max_chars(),
            "redaction_enabled": 1 if self.redaction_policy.is_enabled() else 0,
            "redaction_pattern_count": len(SECRET_PATTERNS),
        }

    def get_total_budget_chars(self) -> int:
        return _env_int(self.env.get("OTONOMASSIST_CONTEXT_BUDGET_CHARS", ""), 5200)

    def get_skills_max_chars(self) -> int:
        return _env_int(self.env.get("OTONOMASSIST_CONTEXT_SKILLS_MAX_CHARS", ""), 2200)

    def get_personality_max_chars(self) -> int:
        return _env_int(self.env.get("OTONOMASSIST_CONTEXT_PERSONALITY_MAX_CHARS", ""), 1600)

    def get_profile_max_chars(self) -> int:
        return _env_int(self.env.get("OTONOMASSIST_CONTEXT_PROFILE_MAX_CHARS", ""), 900)

    def get_runtime_max_chars(self) -> int:
        return _env_int(self.env.get("OTONOMASSIST_CONTEXT_RUNTIME_MAX_CHARS", ""), 2200)


def _truncate(text: str, limit: int) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n... (context budget truncated)"


def _env_int(raw: str, default: int) -> int:
    text = (raw or "").strip()
    if not text:
        return default
    try:
        return max(200, int(text))
    except ValueError:
        return default
