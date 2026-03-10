"""Ollama provider implementation."""

import os
from typing import Any

import httpx

from otonomassist.ai.base import AIProvider, AIResponse, ChatMessage


class OllamaProvider(AIProvider):
    """Ollama local LLM provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        base_url = config.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = config.get("model") or os.getenv("OLLAMA_MODEL", "llama3.2")

        self._base_url = base_url.rstrip("/")
        self._model = model

    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AIResponse:
        """Send chat request to Ollama."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            ollama_messages = []
            for msg in messages:
                ollama_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": ollama_messages,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()

            return AIResponse(
                content=data.get("message", {}).get("content", ""),
                model=self._model,
                finish_reason=data.get("done_reason"),
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
        """Check if Ollama is available."""
        try:
            import httpx
            client = httpx.Client(timeout=5.0)
            response = client.get(f"{self._base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
