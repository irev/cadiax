"""Model/provider routing that cooperates with budget enforcement."""

from __future__ import annotations

from typing import Any

from cadiax.ai.factory import AIProviderFactory
from cadiax.services.runtime.budget_manager import BudgetDecision, BudgetManager


class ModelRouter:
    """Select an AI provider with budget-aware fallback rules."""

    def __init__(self, budget_manager: BudgetManager | None = None) -> None:
        self.budget_manager = budget_manager or BudgetManager()
        self._last_decision: dict[str, Any] = {}

    def get_provider(self) -> Any | None:
        """Return a provider instance, respecting active budget constraints."""
        configured_name = AIProviderFactory.get_current_provider_name()
        decision = self.budget_manager.authorize_provider(configured_name)
        if decision.allowed:
            provider = AIProviderFactory.auto_detect()
            if provider is not None:
                routed_name = provider.__class__.__name__.removesuffix("Provider").lower()
                self._remember(configured_name, routed_name, decision, fallback=routed_name != configured_name)
                return provider

        if not decision.allowed:
            for candidate in self.budget_manager.get_local_providers():
                provider = self._try_create_provider(candidate)
                if provider is not None:
                    self._remember(configured_name, candidate, decision, fallback=True)
                    return provider

        self._remember(configured_name, "", decision, fallback=False)
        return None

    def get_last_decision(self) -> dict[str, Any]:
        """Return the last routing decision for diagnostics."""
        return dict(self._last_decision)

    def _try_create_provider(self, provider_name: str) -> Any | None:
        try:
            provider = AIProviderFactory.create(provider_name)
        except Exception:
            return None
        try:
            return provider if provider.is_available() else None
        except Exception:
            return None

    def _remember(
        self,
        configured: str,
        selected: str,
        decision: BudgetDecision,
        *,
        fallback: bool,
    ) -> None:
        self._last_decision = {
            "configured_provider": configured,
            "selected_provider": selected,
            "fallback_used": fallback,
            "budget_allowed": decision.allowed,
            "budget_reason": decision.reason,
            "budget_enforcement": decision.enforcement,
            "budget_warning": decision.warning,
        }
