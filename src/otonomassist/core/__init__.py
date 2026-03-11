"""Core package."""

from otonomassist.core.agent_context import build_agent_context_block, ensure_agent_storage
from otonomassist.core.assistant import Assistant
from otonomassist.core.result_builder import build_result
from otonomassist.core.result_formatter import PresentationRequest, extract_presentation_request, format_result
from otonomassist.core.skill_loader import SkillLoader
from otonomassist.core.skill_registry import SkillRegistry
from otonomassist.core.transport import TransportContext

__all__ = [
    "Assistant",
    "PresentationRequest",
    "SkillLoader",
    "SkillRegistry",
    "TransportContext",
    "build_result",
    "build_agent_context_block",
    "ensure_agent_storage",
    "extract_presentation_request",
    "format_result",
]
