"""Privacy-aware prompt redaction rules."""

from __future__ import annotations

import os
import re
from typing import Any


DEFAULT_REDACTION_LABEL = "[REDACTED]"
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{10,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._=-]{8,}\b", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|token|password|secret)\b\s*[:=]\s*([^\s,;]+)"),
)


class RedactionPolicy:
    """Redact sensitive tokens before prompt context is sent to an AI provider."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        self.env = env or dict(os.environ)

    def redact_text(self, text: str) -> str:
        """Redact common secret-looking patterns from one text block."""
        if not self.is_enabled():
            return text

        redacted = text or ""
        for pattern in SECRET_PATTERNS:
            if pattern.groups < 2:
                redacted = pattern.sub(self.get_replacement_label(), redacted)
                continue
            redacted = pattern.sub(lambda match: f"{match.group(1)}={self.get_replacement_label()}", redacted)
        return redacted

    def get_diagnostics(self) -> dict[str, Any]:
        """Return machine-readable privacy/redaction diagnostics."""
        return {
            "status": "healthy" if self.is_enabled() else "warning",
            "redaction_enabled": self.is_enabled(),
            "replacement_label": self.get_replacement_label(),
            "pattern_count": len(SECRET_PATTERNS),
        }

    def is_enabled(self) -> bool:
        raw = (self.env.get("OTONOMASSIST_PROMPT_REDACTION", "1") or "1").strip().lower()
        return raw not in {"0", "false", "off", "no"}

    def get_replacement_label(self) -> str:
        return (self.env.get("OTONOMASSIST_PROMPT_REDACTION_LABEL", DEFAULT_REDACTION_LABEL) or DEFAULT_REDACTION_LABEL).strip() or DEFAULT_REDACTION_LABEL
