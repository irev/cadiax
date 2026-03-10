"""AI Chat skill handler."""

import asyncio
from typing import Any

from otonomassist.ai.factory import AIProviderFactory


async def handle(args: str) -> str:
    """Handle AI chat requests."""
    if not args:
        return "Usage: ai <pertanyaan>\nContoh: ai Apa itu Python?"

    try:
        provider = AIProviderFactory.auto_detect()
        if not provider:
            return "Error: Tidak ada AI provider yang tersedia. Pastikan .env dikonfigurasi dengan benar."

        response = await provider.chat_completion(
            prompt=args,
            system_prompt="Anda adalah asisten yang membantu. Jawab dalam bahasa Indonesia kecuali diminta sebaliknya."
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"


def handle_sync(args: str) -> str:
    """Synchronous wrapper for the async handler."""
    return asyncio.run(handle(args))
