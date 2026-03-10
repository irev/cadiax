"""Base AI Provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    """Represents a chat message."""

    role: str
    content: str
    name: str | None = None


@dataclass
class AIResponse:
    """Represents an AI response."""

    content: str
    model: str
    finish_reason: str | None = None
    usage: dict[str, int] | None = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._client: Any = None

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AIResponse:
        """Send a chat request to the AI provider."""
        pass

    @abstractmethod
    async def chat_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Simple chat completion with a single prompt."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        pass

    def _prepare_messages(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> list[ChatMessage]:
        """Prepare messages for chat request."""
        messages: list[ChatMessage] = []

        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))

        messages.append(ChatMessage(role="user", content=prompt))

        return messages
