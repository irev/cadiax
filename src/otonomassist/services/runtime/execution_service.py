"""Execution service for skills and AI-routed commands."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any, Callable

from otonomassist.ai.base import AIResponse
from otonomassist.core.execution_control import classify_result_status, get_skill_timeout_seconds, run_with_timeout
from otonomassist.core.execution_history import append_execution_event
from otonomassist.core.execution_metrics import (
    record_ai_usage_metric,
    record_execution_metric,
    record_provider_latency_metric,
)
from otonomassist.core.result_formatter import extract_presentation_request, format_result
from otonomassist.core.transport import TransportContext
from otonomassist.services.policy import PolicyService

if TYPE_CHECKING:
    from otonomassist.core.skill_registry import SkillRegistry
    from otonomassist.models import Skill


class ExecutionService:
    """Handle AI routing, response parsing, and skill execution."""

    SKILL_RESPONSE_PATTERN = re.compile(
        r"^SKILL:\s*(\w+)\s*\|\s*ARGS:\s*(.*)$",
        re.IGNORECASE | re.MULTILINE,
    )

    def __init__(
        self,
        registry: "SkillRegistry",
        policy_service: PolicyService,
        *,
        provider_getter: Callable[[], Any],
        system_prompt_builder: Callable[[str], str],
        error_formatter: Callable[[str, str], str],
        async_runner: Callable[[Any], Any],
        help_renderer: Callable[[], str],
    ) -> None:
        self.registry = registry
        self.policy_service = policy_service
        self.provider_getter = provider_getter
        self.system_prompt_builder = system_prompt_builder
        self.error_formatter = error_formatter
        self.async_runner = async_runner
        self.help_renderer = help_renderer

    def route_via_ai(self, command: str, context: TransportContext | None = None) -> str:
        """Route a command through the active AI provider."""
        provider = self.provider_getter()
        if not provider:
            return self.error_formatter(
                "no_provider",
                "Tidak ada AI provider tersedia. Cek konfigurasi di .env",
            )

        try:
            provider_name = provider.__class__.__name__.removesuffix("Provider").lower()
            route_started = time.perf_counter()
            ai_response = self._run_chat_completion(
                provider,
                command,
                self.system_prompt_builder(command),
            )
            route_duration_ms = int((time.perf_counter() - route_started) * 1000)
            self._record_ai_route_usage(
                provider_name=provider_name,
                response=ai_response,
                command=command,
                context=context,
                duration_ms=route_duration_ms,
            )
            return self.parse_and_execute(ai_response.content, command, context=context)
        except Exception as exc:
            provider_name = provider.__class__.__name__.removesuffix("Provider").lower()
            record_provider_latency_metric(
                provider=provider_name,
                model=getattr(provider, "get_model_name", lambda: "")() or "",
                duration_ms=0,
                status="error",
            )
            if context and context.trace_id:
                append_execution_event(
                    "ai_route_failed",
                    trace_id=context.trace_id,
                    status="error",
                    source=context.source,
                    command=command,
                    data={"error": str(exc)},
                )
            return self.error_formatter("api_error", str(exc))

    def parse_and_execute(
        self,
        ai_response: str,
        original_command: str,
        context: TransportContext | None = None,
    ) -> str:
        """Parse a structured AI route response and execute the selected skill."""
        match = self.SKILL_RESPONSE_PATTERN.match(ai_response.strip())
        if not match:
            return ai_response

        skill_name = match.group(1).strip().lower()
        skill_args = match.group(2).strip()
        skill = self.registry.get(skill_name)
        if not skill:
            return self.error_formatter(
                "skill_not_found",
                f"Skill '{skill_name}' tidak ditemukan. Available: {', '.join(s.name for s in self.registry)}",
            )

        decision = self.policy_service.authorize_command(skill.name.lower(), skill_args, context)
        if not decision.allowed:
            return decision.message or f"Command/skill `{skill.name.lower()}` ditolak oleh policy."

        try:
            return self.execute_skill(
                skill,
                skill_args,
                original_command=original_command,
                trace_id=context.trace_id if context else "",
            )
        except Exception as exc:
            return f"Error executing skill '{skill_name}': {str(exc)}"

    def _run_chat_completion(self, provider: Any, prompt: str, system_prompt: str) -> AIResponse:
        if hasattr(provider, "chat_completion_response"):
            result = self.async_runner(
                provider.chat_completion_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                )
            )
            if isinstance(result, AIResponse):
                return result
            if hasattr(result, "content"):
                return result

        content = self.async_runner(
            provider.chat_completion(
                prompt=prompt,
                system_prompt=system_prompt,
            )
        )
        return AIResponse(
            content=str(content),
            model=getattr(provider, "get_model_name", lambda: "")() or "",
            usage=None,
        )

    def _record_ai_route_usage(
        self,
        *,
        provider_name: str,
        response: AIResponse,
        command: str,
        context: TransportContext | None,
        duration_ms: int,
    ) -> None:
        record_ai_usage_metric(
            provider=provider_name,
            model=response.model,
            usage=response.usage,
        )
        record_provider_latency_metric(
            provider=provider_name,
            model=response.model,
            duration_ms=duration_ms,
            status="ok",
        )
        if context and context.trace_id:
            append_execution_event(
                "ai_route_completed",
                trace_id=context.trace_id,
                status="ok",
                source=context.source,
                command=command,
                duration_ms=duration_ms,
                data={
                    "model": response.model,
                    "usage": response.usage or {},
                    "finish_reason": response.finish_reason or "",
                },
            )

    def execute_skill(
        self,
        skill: "Skill",
        args: str,
        *,
        original_command: str | None = None,
        trace_id: str = "",
    ) -> str:
        """Execute one skill with timeout, formatting, trace, and metrics."""
        if skill.name.lower() == "help":
            return self.help_renderer()

        skill_started = time.perf_counter()
        if trace_id:
            append_execution_event(
                "skill_started",
                trace_id=trace_id,
                status="started",
                skill_name=skill.name,
                command=original_command or args,
                data={"args": args},
            )

        cleaned_args, presentation = extract_presentation_request(original_command or args, args)
        timeout_seconds = get_skill_timeout_seconds()
        raw_result, timed_out = run_with_timeout(
            lambda: skill.run(cleaned_args),
            timeout_seconds=timeout_seconds,
        )
        if timed_out:
            formatted = (
                f"[ERROR] TIMEOUT\n"
                f"Skill `{skill.name}` melebihi batas waktu {timeout_seconds:.2f} detik."
            )
        else:
            formatted = format_result(raw_result, presentation)

        if trace_id:
            duration_ms = int((time.perf_counter() - skill_started) * 1000)
            status = classify_result_status(formatted)
            append_execution_event(
                "skill_completed",
                trace_id=trace_id,
                status=status,
                skill_name=skill.name,
                command=original_command or args,
                duration_ms=duration_ms,
                data={
                    "result_preview": formatted[:240],
                    "view": presentation.view,
                    "timed_out": timed_out,
                    "timeout_seconds": timeout_seconds,
                },
            )
            record_execution_metric(
                "skill_completed",
                status=status,
                skill_name=skill.name,
                duration_ms=duration_ms,
            )
        return formatted
