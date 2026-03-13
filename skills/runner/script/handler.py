"""Runner skill handler."""

from __future__ import annotations

from pathlib import Path

from cadiax.core.agent_context import (
    append_lesson,
    append_memory_entry,
    get_next_planner_task,
)
from cadiax.core.assistant import Assistant


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = PROJECT_ROOT / "skills"


def handle(args: str) -> str:
    """Run an autonomous loop for a bounded number of steps."""
    args = args.strip().lower()
    if not args or args == "once":
        return _run_steps(1)
    if args == "until-idle":
        return _run_until_idle(max_steps=10)
    if args.startswith("steps "):
        _, _, count_text = args.partition(" ")
        try:
            count = max(1, min(20, int(count_text)))
        except ValueError:
            return "Format: runner steps <angka>"
        return _run_steps(count)

    return "Usage: runner <once|steps N|until-idle>"


def _assistant() -> Assistant:
    assistant = Assistant(skills_dir=SKILLS_DIR)
    assistant.initialize()
    return assistant


def _run_steps(count: int) -> str:
    assistant = _assistant()
    lines = [f"Runner executing {count} step(s):"]
    executed = 0
    for _ in range(count):
        task = get_next_planner_task()
        if not task:
            lines.append("- idle: tidak ada task todo")
            break

        result, reflection = _execute_runner_step(assistant, task["id"])
        executed += 1
        lines.append(f"- step {executed}: task #{task['id']} -> {task['text']}")
        lines.append(f"  result: {result.splitlines()[0] if result else '-'}")
        lines.append(f"  reflection: {reflection.splitlines()[0] if reflection else '-'}")

    append_lesson(f"runner executed {executed} step(s)")
    return "\n".join(lines)


def _run_until_idle(max_steps: int) -> str:
    assistant = _assistant()
    lines = [f"Runner until-idle with max_steps={max_steps}:"]
    executed = 0
    while executed < max_steps:
        task = get_next_planner_task()
        if not task:
            lines.append("- idle: tidak ada task todo")
            break

        result, reflection = _execute_runner_step(assistant, task["id"])
        executed += 1
        lines.append(f"- step {executed}: task #{task['id']} -> {task['text']}")
        lines.append(f"  result: {result.splitlines()[0] if result else '-'}")
        lines.append(f"  reflection: {reflection.splitlines()[0] if reflection else '-'}")

    append_lesson(f"runner until-idle executed {executed} step(s)")
    return "\n".join(lines)


def _execute_runner_step(assistant: Assistant, task_id: int) -> tuple[str, str]:
    """Execute one autonomous step and capture reflection consistently."""
    result = assistant.execute("executor next")
    reflection = assistant.execute("agent-loop reflect")
    append_memory_entry(
        f"runner step completed for task #{task_id}",
        source="runner",
    )
    return result, reflection
