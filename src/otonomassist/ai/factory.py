"""AI Provider Factory."""

import os
from typing import Any

from otonomassist.ai.base import AIProvider
from otonomassist.ai.lmstudio import LMStudioProvider
from otonomassist.ai.ollama import OllamaProvider
from otonomassist.ai.openai import OpenAIProvider


class AIProviderFactory:
    """Factory for creating AI providers."""

    PROVIDERS = {
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
    }

    @classmethod
    def create(cls, provider_name: str | None = None, config: dict[str, Any] | None = None) -> AIProvider:
        """Create an AI provider based on configuration."""
        config = config or {}

        if provider_name is None:
            provider_name = config.get("provider") or os.getenv("AI_PROVIDER", "openai")

        provider_class = cls.PROVIDERS.get(provider_name.lower())

        if not provider_class:
            available = ", ".join(cls.PROVIDERS.keys())
            raise ValueError(f"Unknown provider: {provider_name}. Available: {available}")

        return provider_class(config)

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls.PROVIDERS.keys())

    @classmethod
    def auto_detect(cls) -> AIProvider | None:
        """Auto-detect and create the first available provider."""
        # Try in order of preference
        for provider_name in ["openai", "ollama", "lmstudio"]:
            try:
                provider = cls.create(provider_name)
                if provider.is_available():
                    return provider
            except Exception:
                continue

        return None
