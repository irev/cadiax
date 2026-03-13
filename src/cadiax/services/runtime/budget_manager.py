"""Cost-aware budget controls for AI provider routing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from cadiax.core.execution_metrics import get_execution_metrics_snapshot


DEFAULT_REMOTE_PROVIDERS = ("openai", "claude")
DEFAULT_LOCAL_PROVIDERS = ("ollama", "lmstudio")


@dataclass(slots=True)
class BudgetDecision:
    """Decision for one provider against the active budget policy."""

    allowed: bool
    enforcement: str
    reason: str = ""
    warning: str = ""
    limit_tokens: int = 0
    used_tokens: int = 0
    remaining_tokens: int = 0


class BudgetManager:
    """Evaluate whether AI usage is still allowed under token budgets."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        self.env = env or dict(os.environ)

    def authorize_provider(self, provider_name: str) -> BudgetDecision:
        """Authorize one provider using the active token budget policy."""
        provider = (provider_name or "").strip().lower()
        enforcement = self.get_enforcement_mode()
        usage = self.get_usage_snapshot()
        global_limit = self.get_daily_token_budget()
        remote_limit = self.get_remote_daily_token_budget()

        if global_limit > 0 and usage["ai_total_tokens"] >= global_limit:
            return self._decision(
                provider=provider,
                enforcement=enforcement,
                reason="daily_token_budget_exceeded",
                limit_tokens=global_limit,
                used_tokens=usage["ai_total_tokens"],
            )

        if provider in self.get_remote_providers() and remote_limit > 0 and usage["remote_ai_total_tokens"] >= remote_limit:
            return self._decision(
                provider=provider,
                enforcement=enforcement,
                reason="remote_daily_token_budget_exceeded",
                limit_tokens=remote_limit,
                used_tokens=usage["remote_ai_total_tokens"],
            )

        return BudgetDecision(
            allowed=True,
            enforcement=enforcement,
            remaining_tokens=max(0, global_limit - usage["ai_total_tokens"]) if global_limit > 0 else 0,
        )

    def get_diagnostics(self) -> dict[str, Any]:
        """Return machine-readable budget diagnostics."""
        usage = self.get_usage_snapshot()
        global_limit = self.get_daily_token_budget()
        remote_limit = self.get_remote_daily_token_budget()
        status = "healthy"
        if (global_limit > 0 and usage["ai_total_tokens"] >= global_limit) or (
            remote_limit > 0 and usage["remote_ai_total_tokens"] >= remote_limit
        ):
            status = "blocked" if self.get_enforcement_mode() == "hard" else "warning"

        return {
            "status": status,
            "enforcement": self.get_enforcement_mode(),
            "daily_token_budget": global_limit,
            "remote_daily_token_budget": remote_limit,
            "ai_total_tokens": usage["ai_total_tokens"],
            "remote_ai_total_tokens": usage["remote_ai_total_tokens"],
            "remote_providers": sorted(self.get_remote_providers()),
            "local_providers": list(self.get_local_providers()),
        }

    def get_usage_snapshot(self) -> dict[str, int]:
        """Summarize token usage relevant to budget checks."""
        snapshot = get_execution_metrics_snapshot()
        total_tokens = int(snapshot["summary"].get("ai_total_tokens", 0) or 0)
        remote_tokens = 0
        for summary in snapshot.get("token_usage", {}).values():
            provider = str(summary.get("provider") or "").strip().lower()
            if provider in self.get_remote_providers():
                remote_tokens += int(summary.get("total_tokens", 0) or 0)
        return {
            "ai_total_tokens": total_tokens,
            "remote_ai_total_tokens": remote_tokens,
        }

    def get_daily_token_budget(self) -> int:
        """Return the daily total token budget, or zero when unlimited."""
        return _env_int(self.env.get("OTONOMASSIST_DAILY_TOKEN_BUDGET", ""))

    def get_remote_daily_token_budget(self) -> int:
        """Return the daily token budget for remote providers, or zero when unlimited."""
        return _env_int(self.env.get("OTONOMASSIST_REMOTE_DAILY_TOKEN_BUDGET", ""))

    def get_enforcement_mode(self) -> str:
        """Return budget enforcement mode: warn or hard."""
        value = (self.env.get("OTONOMASSIST_BUDGET_ENFORCEMENT", "warn") or "warn").strip().lower()
        return value if value in {"warn", "hard"} else "warn"

    def get_remote_providers(self) -> set[str]:
        """Return provider names treated as remote/cost-bearing."""
        raw = (self.env.get("OTONOMASSIST_REMOTE_AI_PROVIDERS", "") or "").strip()
        if not raw:
            return set(DEFAULT_REMOTE_PROVIDERS)
        return {item.strip().lower() for item in raw.split(",") if item.strip()}

    def get_local_providers(self) -> tuple[str, ...]:
        """Return preferred local fallback providers."""
        raw = (self.env.get("OTONOMASSIST_LOCAL_AI_PROVIDERS", "") or "").strip()
        if not raw:
            return DEFAULT_LOCAL_PROVIDERS
        values = tuple(item.strip().lower() for item in raw.split(",") if item.strip())
        return values or DEFAULT_LOCAL_PROVIDERS

    def _decision(
        self,
        *,
        provider: str,
        enforcement: str,
        reason: str,
        limit_tokens: int,
        used_tokens: int,
    ) -> BudgetDecision:
        remaining = max(0, limit_tokens - used_tokens)
        warning = (
            f"Budget token untuk provider `{provider}` telah melewati batas "
            f"({used_tokens}/{limit_tokens})."
        )
        return BudgetDecision(
            allowed=enforcement != "hard",
            enforcement=enforcement,
            reason=reason,
            warning=warning,
            limit_tokens=limit_tokens,
            used_tokens=used_tokens,
            remaining_tokens=remaining,
        )


def _env_int(raw: str) -> int:
    text = (raw or "").strip()
    if not text:
        return 0
    try:
        return max(0, int(text))
    except ValueError:
        return 0
