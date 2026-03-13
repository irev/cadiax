"""AI Provider Factory."""

import os
from typing import Any

from cadiax.ai.base import AIProvider
from cadiax.ai.lmstudio import LMStudioProvider
from cadiax.ai.ollama import OllamaProvider
from cadiax.ai.openai import OpenAIProvider
from cadiax.ai.claude import ClaudeProvider
from cadiax.core.agent_context import get_env_or_secret


def _mask_value(value: str) -> str:
    if not value:
        return "(kosong)"
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * 8}...{value[-4:]}"


class AIProviderFactory:
    """Factory for creating AI providers."""

    PROVIDERS = {
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
        "claude": ClaudeProvider,
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
    def get_current_provider_name(cls) -> str:
        """Get the current configured provider name."""
        return os.getenv("AI_PROVIDER", "openai").lower()

    @classmethod
    def get_provider_config_info(cls) -> dict[str, Any]:
        """Get configuration info for the current provider."""
        provider = cls.get_current_provider_name()
        info = {
            "provider": provider,
            "available_providers": list(cls.PROVIDERS.keys()),
            "config": {},
            "issues": [],
        }

        if provider == "openai":
            api_key = get_env_or_secret("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            fallback_model = os.getenv("OPENAI_FALLBACK_MODEL")
            info["config"] = {"base_url": base_url, "model": model}
            if api_key:
                info["config"]["api_key"] = _mask_value(api_key)
            if fallback_model:
                info["config"]["fallback_model"] = fallback_model
            if not api_key:
                info["issues"].append("OPENAI_API_KEY tidak ditemukan di .env atau secrets")
            elif len(api_key) < 20:
                info["issues"].append("OPENAI_API_KEY tampak tidak valid (terlalu pendek)")

        elif provider == "claude":
            api_key = get_env_or_secret("ANTHROPIC_API_KEY")
            base_url = os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")
            model = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")
            info["config"] = {"base_url": base_url, "model": model}
            if api_key:
                info["config"]["api_key"] = _mask_value(api_key)
            if not api_key:
                info["issues"].append("ANTHROPIC_API_KEY tidak ditemukan di .env atau secrets")

        elif provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model = os.getenv("OLLAMA_MODEL", "llama3.2")
            info["config"] = {"base_url": base_url, "model": model}
            info["issues"].append(f"Pastikan Ollama running di {base_url}")

        elif provider == "lmstudio":
            base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
            model = os.getenv("LMSTUDIO_MODEL", "local-model")
            info["config"] = {"base_url": base_url, "model": model}
            info["issues"].append(f"Pastikan LM Studio running di {base_url}")

        return info

    @classmethod
    def get_config_diagnostic(cls) -> str:
        """Get diagnostic information about current provider configuration."""
        info = cls.get_provider_config_info()
        lines = [
            f"Current AI_PROVIDER: {info['provider']}",
            f"Available providers: {', '.join(info['available_providers'])}",
            "",
            "Configuration:"
        ]

        if info["config"]:
            for key, value in info["config"].items():
                if "url" in key.lower():
                    lines.append(f"  - {key}: {value}")
                elif "key" in key.lower():
                    lines.append(f"  - {key}: {'*' * 8}...{value[-4:] if len(value) > 4 else ''}" if value else "  - {key}: (not set)")
                else:
                    lines.append(f"  - {key}: {value}")

        if info["issues"]:
            lines.append("")
            lines.append("Issues detected:")
            for issue in info["issues"]:
                lines.append(f"  - {issue}")

        lines.append("")
        lines.append("Tip: Cek file .env atau secrets lokal untuk konfigurasi lengkap.")

        return "\n".join(lines)

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls.PROVIDERS.keys())

    @classmethod
    def auto_detect(cls) -> AIProvider | None:
        """Auto-detect and create the first available provider."""
        # Try in order of preference
        for provider_name in ["openai", "claude", "ollama", "lmstudio"]:
            try:
                provider = cls.create(provider_name)
                if provider.is_available():
                    return provider
            except Exception:
                continue

        return None

    @classmethod
    def get_model_listing(cls) -> str:
        """Get visible models for the current provider if supported."""
        provider_name = cls.get_current_provider_name()
        provider = cls.create(provider_name)

        if provider_name != "openai" or not hasattr(provider, "list_models"):
            return (
                f"Listing models is not supported for provider '{provider_name}' "
                "in this CLI."
            )

        import asyncio

        models = asyncio.run(provider.list_models())
        if not models:
            return "No models returned by the API."

        lines = [f"Models visible to provider '{provider_name}':"]
        for model in models:
            lines.append(f"- {model}")
        return "\n".join(lines)
