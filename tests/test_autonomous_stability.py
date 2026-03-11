from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from otonomassist.core import agent_context  # noqa: E402
from otonomassist.core import workspace_guard  # noqa: E402
from otonomassist.ai.factory import AIProviderFactory  # noqa: E402
from otonomassist.core.assistant import Assistant  # noqa: E402
from otonomassist.transports.telegram import TelegramPollingTransport  # noqa: E402
import otonomassist.transports.telegram as telegram_module  # noqa: E402


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _configure_temp_agent_state(tmp_path, monkeypatch):
    data_dir = tmp_path / ".otonomassist"
    monkeypatch.setattr(agent_context, "DATA_DIR", data_dir)
    monkeypatch.setattr(agent_context, "MEMORY_FILE", data_dir / "memory.jsonl")
    monkeypatch.setattr(agent_context, "PLANNER_FILE", data_dir / "planner.json")
    monkeypatch.setattr(agent_context, "LESSONS_FILE", data_dir / "lessons.md")
    monkeypatch.setattr(agent_context, "PROFILE_FILE", data_dir / "profile.md")
    monkeypatch.setattr(agent_context, "SECRETS_FILE", data_dir / "secrets.json")
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ACCESS", "rw")
    agent_context.ensure_agent_storage()


class _FakeProvider:
    async def chat_completion(self, prompt, system_prompt=None, **kwargs):
        return (
            "1. Observasi: state terpantau.\n"
            "2. Risiko utama: rendah.\n"
            "3. Langkah berikutnya: lanjutkan task planner.\n"
            "4. Mengapa langkah itu penting: menjaga progres tetap berjalan."
        )


class _ResolveProvider:
    async def chat_completion(self, prompt, system_prompt=None, **kwargs):
        return "research siapa presiden saat ini"


def test_append_lesson_deduplicates_recent_entry(tmp_path, monkeypatch):
    lessons_file = tmp_path / "lessons.md"
    lessons_file.write_text("# Learned Lessons\n", encoding="utf-8")

    monkeypatch.setattr(agent_context, "DATA_DIR", tmp_path)
    monkeypatch.setattr(agent_context, "LESSONS_FILE", lessons_file)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ACCESS", "rw")

    agent_context.append_lesson("lesson yang sama")
    agent_context.append_lesson("lesson yang sama")

    lines = lessons_file.read_text(encoding="utf-8").splitlines()
    lesson_lines = [line for line in lines if line.startswith("- ")]
    assert len(lesson_lines) == 1


def test_executor_blocks_mutating_autonomous_commands():
    module = _load_module(ROOT / "skills" / "executor" / "script" / "handler.py", "executor_handler_test")

    assert module._guard_autonomous_command("secrets set token abc", task_id=1) is not None
    assert module._guard_autonomous_command("profile add-context rahasia", task_id=1) is not None
    assert module._guard_autonomous_command("memory add catatan aman", task_id=1) is None
    assert module._guard_autonomous_command("secrets set token abc", task_id=None) is None


def test_self_review_skips_duplicate_follow_up_tasks(tmp_path, monkeypatch):
    module = _load_module(ROOT / "skills" / "self-review" / "script" / "handler.py", "self_review_handler_test")

    planner_file = tmp_path / "planner.json"
    planner_file.write_text(
        json.dumps(
            {
                "goal": "",
                "tasks": [
                    {
                        "id": 1,
                        "text": "agent-loop next",
                        "status": "todo",
                        "notes": [],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                    {
                        "id": 2,
                        "text": "memory add follow-up self-review diperlukan untuk text",
                        "status": "todo",
                        "notes": [],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(agent_context, "DATA_DIR", tmp_path)
    monkeypatch.setattr(agent_context, "PLANNER_FILE", planner_file)
    monkeypatch.setattr(agent_context, "MEMORY_FILE", tmp_path / "memory.jsonl")
    monkeypatch.setattr(agent_context, "LESSONS_FILE", tmp_path / "lessons.md")
    monkeypatch.setattr(agent_context, "PROFILE_FILE", tmp_path / "profile.md")
    monkeypatch.setattr(agent_context, "SECRETS_FILE", tmp_path / "secrets.json")
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ACCESS", "rw")

    (tmp_path / "memory.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "lessons.md").write_text("# Learned Lessons\n", encoding="utf-8")
    (tmp_path / "profile.md").write_text("# Agent Profile\n", encoding="utf-8")
    (tmp_path / "secrets.json").write_text(json.dumps({"secrets": {}}, indent=2), encoding="utf-8")

    result = module.handle("text TODO dan api_key")

    assert "agent-loop next" in result["data"]["persistence"]["duplicate_follow_up_skipped"]
    assert (
        "memory add follow-up self-review diperlukan untuk text"
        in result["data"]["persistence"]["duplicate_follow_up_skipped"]
    )


def test_runner_once_executes_planner_executor_and_reflection_end_to_end(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: _FakeProvider()))

    runner_module = _load_module(ROOT / "skills" / "runner" / "script" / "handler.py", "runner_handler_test")
    self_review_module = _load_module(
        ROOT / "skills" / "self-review" / "script" / "handler.py",
        "self_review_handler_e2e_test",
    )

    task = agent_context.add_planner_task("memory add catatan e2e", status="todo")
    output = runner_module.handle("once")

    planner_state = agent_context.load_planner_state()
    task_state = next(item for item in planner_state["tasks"] if item["id"] == task["id"])
    memories = agent_context.load_recent_memories(limit=50)
    memory_texts = [entry.get("text", "") for entry in memories]

    assert "Runner executing 1 step(s):" in output
    assert "reflection:" in output
    assert task_state["status"] == "done"
    assert any("Memory #1 tersimpan." in text or "catatan e2e" in text for text in memory_texts)
    assert any(text.startswith("agent-loop reflect:") for text in memory_texts)
    assert any(text.startswith("runner step completed") for text in memory_texts)

    review = self_review_module.handle("text TODO dan api_key")
    assert review["type"] == "self_review_result"
    assert review["data"]["finding_count"] >= 2
    assert review["data"]["persistence"]["lesson_written"] is True


def test_runner_until_idle_processes_multiple_tasks_with_reflection(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: _FakeProvider()))

    runner_module = _load_module(ROOT / "skills" / "runner" / "script" / "handler.py", "runner_handler_until_idle")

    agent_context.add_planner_task("memory add tugas satu", status="todo")
    agent_context.add_planner_task("memory add tugas dua", status="todo")

    output = runner_module.handle("until-idle")
    planner_state = agent_context.load_planner_state()
    memories = agent_context.load_recent_memories(limit=50)
    reflections = [entry for entry in memories if entry.get("source") == "agent-loop"]

    assert "Runner until-idle with max_steps=10:" in output
    assert output.count("reflection:") >= 2
    assert all(task["status"] == "done" for task in planner_state["tasks"])
    assert len(reflections) >= 2


def test_executor_resolves_natural_language_to_known_prefix(monkeypatch):
    module = _load_module(ROOT / "skills" / "executor" / "script" / "handler.py", "executor_handler_resolve_test")
    monkeypatch.setattr(module.AIProviderFactory, "auto_detect", staticmethod(lambda: _ResolveProvider()))

    resolved = module._resolve_command("cari presiden saat ini")
    assert resolved == "research siapa presiden saat ini"


def test_assistant_applies_formatter_from_user_intent(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "README.md").write_text("README contoh untuk formatter\n", encoding="utf-8")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("workspace cari README dalam bentuk tabel")

    assert "| Path | Line | Text |" in result
    assert "README.md" in result


def test_telegram_transport_handles_message_without_network(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(telegram_module, "TELEGRAM_AUTH_FILE", tmp_path / ".otonomassist" / "telegram_auth.json")
    monkeypatch.setattr(telegram_module, "TELEGRAM_STATE_FILE", tmp_path / ".otonomassist" / "telegram_state.json")

    sent_messages: list[tuple[str, str]] = []
    transport = TelegramPollingTransport(token="dummy-token", poll_timeout=1)
    monkeypatch.setattr(transport, "_send_message", lambda chat_id, text: sent_messages.append((chat_id, text)))
    monkeypatch.setattr(transport, "_is_authorized", lambda *args, **kwargs: True)
    monkeypatch.setattr(transport, "_resolve_roles", lambda *args, **kwargs: ("telegram", "owner"))

    captured: dict[str, object] = {}

    class FakeAssistant:
        def handle_message(self, message, context=None):
            captured["message"] = message
            captured["context"] = context
            return "handled-ok"

    update = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "text": "memory list",
            "chat": {"id": 12345, "type": "private"},
            "from": {"id": 999, "username": "tester"},
        },
    }

    transport._handle_update(FakeAssistant(), update)

    assert captured["message"] == "memory list"
    assert getattr(captured["context"], "source", None) == "telegram"
    assert sent_messages == [("12345", "handled-ok")]
