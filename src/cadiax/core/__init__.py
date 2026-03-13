"""Core package."""

from cadiax.core.agent_context import build_agent_context_block, ensure_agent_storage
from cadiax.core.assistant import Assistant
from cadiax.core.config_doctor import get_config_status_data, get_config_status_report
from cadiax.core.execution_control import classify_result_status, get_skill_timeout_seconds
from cadiax.core.event_bus import render_event_bus
from cadiax.core.execution_history import render_execution_history
from cadiax.core.execution_metrics import get_execution_metrics_snapshot, render_execution_metrics
from cadiax.core.result_builder import build_result
from cadiax.core.result_formatter import PresentationRequest, extract_presentation_request, format_result
from cadiax.core.setup_wizard import run_setup_wizard, should_recommend_setup
from cadiax.core.skill_loader import SkillLoader
from cadiax.core.skill_registry import SkillRegistry
from cadiax.core.transport import TransportContext

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
