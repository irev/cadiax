"""AI Chat skill handler."""

import asyncio
from typing import Any

from cadiax.ai.factory import AIProviderFactory
from cadiax.core.agent_context import ensure_agent_storage
from cadiax.services.personality import PersonalityService
from cadiax.services.runtime import ContextBudgeter


async def handle(args: str) -> str:
    """Handle AI chat requests."""
    if not args:
        return "Usage: ai <pertanyaan>\nContoh: ai Apa itu Python?"

    try:
        ensure_agent_storage()
        provider = AIProviderFactory.auto_detect()
        if not provider:
            return "Error: Tidak ada AI provider yang tersedia. Pastikan .env dikonfigurasi dengan benar."

        response = await provider.chat_completion(
            prompt=args,
            system_prompt=(
                "Anda adalah private AI assistant yang membantu. "
                "Jawab dalam bahasa Indonesia kecuali diminta sebaliknya.\n\n"
                + ContextBudgeter().build_general_reasoning_context(
                    query=args,
                    personality_service=PersonalityService(),
                )
            ),
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"


def handle_sync(args: str) -> str:
    """Synchronous wrapper for the async handler."""
    return asyncio.run(handle(args))
