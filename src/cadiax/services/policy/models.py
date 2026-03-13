"""Policy decision contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PolicyDecision:
    """One policy authorization outcome."""

    allowed: bool
    message: str | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
