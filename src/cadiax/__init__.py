"""Cadiax - Autonomous Assistant.

Modular assistant system with skill-based architecture.
"""

from cadiax.core.path_layout import apply_env_aliases

__version__ = "1.1.6"
__author__ = "Cadiax Team"
apply_env_aliases()

from cadiax.core.assistant import Assistant
from cadiax.models.skill import Skill, SkillDefinition

__all__ = ["Assistant", "Skill", "SkillDefinition", "__version__"]
