"""Core package."""

from otonomassist.core.agent_context import build_agent_context_block, ensure_agent_storage
from otonomassist.core.assistant import Assistant
from otonomassist.core.config_doctor import get_config_status_data, get_config_status_report
from otonomassist.core.execution_control import classify_result_status, get_skill_timeout_seconds
from otonomassist.core.event_bus import render_event_bus
from otonomassist.core.execution_history import render_execution_history
from otonomassist.core.execution_metrics import get_execution_metrics_snapshot, render_execution_metrics
from otonomassist.core.result_builder import build_result
from otonomassist.core.result_formatter import PresentationRequest, extract_presentation_request, format_result
from otonomassist.core.setup_wizard import run_setup_wizard, should_recommend_setup
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
    "classify_result_status",
    "ensure_agent_storage",
    "extract_presentation_request",
    "format_result",
    "get_config_status_data",
    "get_config_status_report",
    "get_execution_metrics_snapshot",
    "get_skill_timeout_seconds",
    "render_event_bus",
    "render_execution_metrics",
    "render_execution_history",
    "run_setup_wizard",
    "should_recommend_setup",
]
