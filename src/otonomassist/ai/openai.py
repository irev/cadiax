"""OpenAI provider implementation."""

import os
from typing import Any

from openai import AsyncOpenAI

from otonomassist.ai.base import AIProvider, AIResponse, ChatMessage


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        base_url = config.get("base_url") or os.getenv("OPENAI_BASE_URL")
        model = config.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if not api_key:
            raise ValueError("OpenAI API key is required")

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self._model = model

    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AIResponse:
        """Send chat request to OpenAI."""
        openai_messages = []
        for msg in messages:
            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name
            openai_messages.append(msg_dict)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            **kwargs,
        )

        choice = response.choices[0]
        return AIResponse(
            content=choice.message.content or "",
            model=response.model,
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            if response.usage
            else None,
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
        """Check if OpenAI is available."""
        return bool(self.config.get("api_key") or os.getenv("OPENAI_API_KEY"))
