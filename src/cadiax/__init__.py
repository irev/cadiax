"""Cadiax - Autonomous Assistant.

Modular assistant system with skill-based architecture.
"""

import os

__version__ = "1.1.1"
__author__ = "Cadiax Team"


def _apply_env_aliases() -> None:
    """Mirror public CADIAX_* env vars into legacy OTONOMASSIST_* keys and back."""
    items = list(os.environ.items())
    for key, value in items:
        if key.startswith("CADIAX_"):
            legacy_key = "OTONOMASSIST_" + key[len("CADIAX_") :]
            os.environ.setdefault(legacy_key, value)
        elif key.startswith("OTONOMASSIST_"):
            public_key = "CADIAX_" + key[len("OTONOMASSIST_") :]
            os.environ.setdefault(public_key, value)


_apply_env_aliases()

from cadiax.core.assistant import Assistant
from cadiax.models.skill import Skill, SkillDefinition

__all__ = ["Assistant", "Skill", "SkillDefinition", "__version__"]
