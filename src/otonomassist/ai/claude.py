"""Claude AI provider implementation."""

import os
from typing import Any

import httpx

from otonomassist.ai.base import AIProvider, AIResponse, ChatMessage


class ClaudeProvider(AIProvider):
    """Claude API (Anthropic) provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        base_url = config.get("base_url") or os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")
        model = config.get("model") or os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")

        if not api_key:
            raise ValueError("Anthropic API key is required")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AIResponse:
        """Send chat request to Claude."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Convert messages to Claude format
            claude_messages = []
            for msg in messages:
                if msg.role != "system":
                    claude_messages.append({
                        "role": msg.role,
                        "content": msg.content,
                    })

            # Get system prompt if exists
            system_prompt = None
            for msg in messages:
                if msg.role == "system":
                    system_prompt = msg.content
                    break

            headers = {
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            request_body: dict[str, Any] = {
                "model": self._model,
                "messages": claude_messages,
                "max_tokens": kwargs.get("max_tokens", 1024),
            }

            if system_prompt:
                request_body["system"] = system_prompt

            response = await client.post(
                f"{self._base_url}/v1/messages",
                headers=headers,
                json=request_body,
            )
            response.raise_for_status()
            data = response.json()

            return AIResponse(
                content=data.get("content", [{}])[0].get("text", ""),
                model=self._model,
                finish_reason=data.get("stop_reason"),
            )

    async def chat_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Simple chat completion."""
        messages = self._prepare_messages(prompt, system_prompt)
        response = await self.chat(messages, **kwargs)
        return response.content

    def get_model_name(self) -> str:
        """Get the model name."""
        return self._model

    def is_available(self) -> bool:
        """Check if Claude is available."""
        return bool(self._api_key or os.getenv("ANTHROPIC_API_KEY"))
