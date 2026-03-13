"""LM Studio provider implementation."""

import os
from typing import Any

import httpx

from cadiax.ai.base import AIProvider, AIResponse, ChatMessage


class LMStudioProvider(AIProvider):
    """LM Studio local LLM provider (OpenAI compatible API)."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        base_url = config.get("base_url") or os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        model = config.get("model") or os.getenv("LMSTUDIO_MODEL", "local-model")

        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=120.0)

    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AIResponse:
        """Send chat request to LM Studio."""
        openai_messages = []
        for msg in messages:
            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name
            openai_messages.append(msg_dict)

        response = await self._client.post(
            "/chat/completions",
            json={
                "model": self._model,
                "messages": openai_messages,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        return AIResponse(
            content=choice["message"].get("content", ""),
            model=data.get("model", self._model),
            finish_reason=choice.get("finish_reason"),
            usage=data.get("usage"),
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

    async def chat_completion_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AIResponse:
        """Simple chat completion that preserves usage metadata."""
        messages = self._prepare_messages(prompt, system_prompt)
        return await self.chat(messages, **kwargs)

    def get_model_name(self) -> str:
        """Get the model name."""
        return self._model

    def is_available(self) -> bool:
        """Check if LM Studio is available."""
        try:
            import httpx
            client = httpx.Client(timeout=5.0)
            response = client.get(f"{self._base_url}/models")
            return response.status_code == 200
        except Exception:
            return False
