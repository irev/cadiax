"""Autonomiq - Autonomous Assistant.

Modular assistant system with skill-based architecture.
"""

__version__ = "1.1.0"
__author__ = "Autonomiq Team"

from otonomassist.core.assistant import Assistant
from otonomassist.models.skill import Skill, SkillDefinition

__all__ = ["Assistant", "Skill", "SkillDefinition", "__version__"]
