"""OpenAI provider implementation."""

import asyncio
import os
from typing import Any

from openai import OpenAI

from cadiax.ai.base import AIProvider, AIResponse, ChatMessage
from cadiax.core.agent_context import get_env_or_secret


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        api_key = config.get("api_key") or get_env_or_secret("OPENAI_API_KEY")
        base_url = config.get("base_url") or os.getenv("OPENAI_BASE_URL")
        model = config.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        fallback_model = (
            config.get("fallback_model")
            or os.getenv("OPENAI_FALLBACK_MODEL")
            or None
        )

        if not api_key:
            raise ValueError("OpenAI API key is required")

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self._model = model
        self._fallback_model = fallback_model

    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AIResponse:
        """Send chat request to OpenAI."""
        return await asyncio.to_thread(self._chat_sync, messages, kwargs)

    def _chat_sync(
        self,
        messages: list[ChatMessage],
        kwargs: dict[str, Any],
    ) -> AIResponse:
        """Run a chat request through the synchronous OpenAI client."""
        if self._uses_responses_api(self._model):
            return self._chat_via_responses_api(messages, self._model, kwargs)

        openai_messages = []
        for msg in messages:
            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name
            openai_messages.append(msg_dict)

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                **kwargs,
            )
        except Exception as e:
            if not self._should_retry_with_fallback(e):
                raise

            if self._uses_responses_api(self._fallback_model):
                return self._chat_via_responses_api(
                    messages,
                    self._fallback_model,
                    kwargs,
                )

            response = self._client.chat.completions.create(
                model=self._fallback_model,
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
        """Check if OpenAI is available."""
        return bool(self.config.get("api_key") or get_env_or_secret("OPENAI_API_KEY"))

    async def list_models(self) -> list[str]:
        """List models visible to the active OpenAI API key."""
        return await asyncio.to_thread(self._list_models_sync)

    async def web_search_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Run a grounded web search response through OpenAI Responses API."""
        return await asyncio.to_thread(
            self._web_search_completion_sync,
            prompt,
            system_prompt,
            kwargs,
        )

    def _list_models_sync(self) -> list[str]:
        """List models visible to the active OpenAI API key."""
        response = self._client.models.list()
        return sorted(model.id for model in response.data)

    def _web_search_completion_sync(
        self,
        prompt: str,
        system_prompt: str | None,
        kwargs: dict[str, Any],
    ) -> str:
        """Run a web-grounded response using OpenAI web search."""
        web_model = (
            kwargs.pop("model", None)
            or os.getenv("OPENAI_WEB_MODEL")
            or self._fallback_model
            or self._model
        )
        response = self._client.responses.create(
            model=web_model,
            tools=[{"type": "web_search_preview"}],
            instructions=system_prompt,
            input=prompt,
            **kwargs,
        )
        return getattr(response, "output_text", "")

    def _should_retry_with_fallback(self, error: Exception) -> bool:
        """Retry with fallback model on model access/name failures."""
        if not self._fallback_model or self._fallback_model == self._model:
            return False

        error_text = str(error).lower()
        return (
            "model_not_found" in error_text
            or "does not have access to model" in error_text
            or "unknown model" in error_text
        )

    def _uses_responses_api(self, model: str | None) -> bool:
        """Use Responses API for Codex-family models."""
        if not model:
            return False

        return "codex" in model.lower()

    def _chat_via_responses_api(
        self,
        messages: list[ChatMessage],
        model: str,
        kwargs: dict[str, Any],
    ) -> AIResponse:
        """Send a request through the Responses API."""
        input_items = []
        for msg in messages:
            input_items.append(
                {
                    "role": msg.role,
                    "content": [
                        {
                            "type": "input_text",
                            "text": msg.content,
                        }
                    ],
                }
            )

        response = self._client.responses.create(
            model=model,
            input=input_items,
            **kwargs,
        )

        usage = None
        if getattr(response, "usage", None):
            usage = {
                "prompt_tokens": getattr(response.usage, "input_tokens", 0),
                "completion_tokens": getattr(response.usage, "output_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

        return AIResponse(
            content=getattr(response, "output_text", ""),
            model=getattr(response, "model", model),
            finish_reason=None,
            usage=usage,
        )
