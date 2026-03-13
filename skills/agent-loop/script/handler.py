"""Agent loop skill handler."""

from __future__ import annotations

from otonomassist.ai.factory import AIProviderFactory
from otonomassist.core.agent_context import (
    append_memory_entry,
    get_next_planner_task,
)
from otonomassist.services.personality import PersonalityService
from otonomassist.services.runtime import ContextBudgeter


async def handle(args: str) -> str:
    """Run a semi-autonomous reflection/next-step loop."""
    args = args.strip().lower()
    if not args:
        args = "next"

    if args not in {"next", "reflect"}:
        return "Usage: agent-loop <next|reflect>"

    provider = AIProviderFactory.auto_detect()
    if not provider:
        return "Error: Tidak ada AI provider yang tersedia."

    next_task = get_next_planner_task()
    next_task_text = (
        f"Next planner task: #{next_task['id']} {next_task['text']}"
        if next_task
        else "Next planner task: tidak ada"
    )
    prompt = (
        f"{ContextBudgeter().build_general_reasoning_context(query=args, personality_service=PersonalityService())}\n\n"
        f"{next_task_text}\n\n"
        "Buat respons ringkas dengan format:\n"
        "1. Observasi\n"
        "2. Risiko utama\n"
        "3. Langkah berikutnya\n"
        "4. Mengapa langkah itu penting\n"
    )

    if args == "reflect":
        prompt += "\nFokus pada refleksi kualitas state agent saat ini."
    else:
        prompt += "\nFokus pada aksi paling bernilai berikutnya."

    response = await provider.chat_completion(
        prompt=prompt,
        system_prompt=(
            "Anda adalah loop refleksi internal untuk private AI. "
            "Gunakan konteks persisten agent dan jawab singkat, operasional, dan dapat ditindaklanjuti."
        ),
    )
    append_memory_entry(f"agent-loop {args}: {response}", source="agent-loop")
    return response
