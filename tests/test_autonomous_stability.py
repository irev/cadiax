from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import time
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from otonomassist.core import agent_context  # noqa: E402
from otonomassist.core.execution_history import load_execution_events  # noqa: E402
from otonomassist.core.execution_metrics import get_execution_metrics_snapshot  # noqa: E402
from otonomassist.core import workspace_guard  # noqa: E402
from otonomassist.core.admin_api import build_admin_snapshot  # noqa: E402
from otonomassist.ai.base import AIResponse  # noqa: E402
from otonomassist.ai.factory import AIProviderFactory  # noqa: E402
from otonomassist.core.assistant import Assistant  # noqa: E402
from otonomassist.core.job_runtime import process_job_queue  # noqa: E402
from otonomassist.core.scheduler_runtime import run_scheduler  # noqa: E402
from otonomassist.interfaces.telegram import TelegramPollingTransport as InterfaceTelegramPollingTransport  # noqa: E402
from otonomassist.platform import run_worker_service  # noqa: E402
from otonomassist.services import BudgetManager, ContextBudgeter, HabitModelService, ModelRouter, PersonalityService, PolicyService, RedactionPolicy  # noqa: E402
from otonomassist.services.interactions import (  # noqa: E402
    ConversationService,
    InteractionRequest,
    build_conversation_response,
)
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
    for name in (
        "TELEGRAM_OWNER_IDS",
        "TELEGRAM_ALLOW_FROM",
        "TELEGRAM_GROUPS",
        "TELEGRAM_GROUP_ALLOW_FROM",
        "TELEGRAM_DM_POLICY",
        "TELEGRAM_GROUP_POLICY",
        "TELEGRAM_REQUIRE_MENTION",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(agent_context, "DATA_DIR", data_dir)
    monkeypatch.setattr(agent_context, "MEMORY_FILE", data_dir / "memory.jsonl")
    monkeypatch.setattr(agent_context, "PLANNER_FILE", data_dir / "planner.json")
    monkeypatch.setattr(agent_context, "LESSONS_FILE", data_dir / "lessons.md")
    monkeypatch.setattr(agent_context, "PROFILE_FILE", data_dir / "profile.md")
    monkeypatch.setattr(agent_context, "PREFERENCES_FILE", data_dir / "preferences.json")
    monkeypatch.setattr(agent_context, "HABITS_FILE", data_dir / "habits.json")
    monkeypatch.setattr(agent_context, "MEMORY_SUMMARIES_FILE", data_dir / "memory_summaries.json")
    monkeypatch.setattr(agent_context, "IDENTITIES_FILE", data_dir / "identities.json")
    monkeypatch.setattr(agent_context, "SESSIONS_FILE", data_dir / "sessions.json")
    monkeypatch.setattr(agent_context, "SECRETS_FILE", data_dir / "secrets.json")
    monkeypatch.setattr(agent_context, "EXECUTION_HISTORY_FILE", data_dir / "execution_history.jsonl")
    monkeypatch.setattr(agent_context, "METRICS_FILE", data_dir / "execution_metrics.json")
    monkeypatch.setattr(agent_context, "JOB_QUEUE_FILE", data_dir / "job_queue.json")
    monkeypatch.setattr(agent_context, "SCHEDULER_STATE_FILE", data_dir / "scheduler_state.json")
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


class _BrokenProvider:
    async def chat_completion(self, prompt, system_prompt=None, **kwargs):
        raise RuntimeError("provider boom")


class _StructuredRouteProvider:
    def __init__(self, response: str) -> None:
        self.response = response

    async def chat_completion(self, prompt, system_prompt=None, **kwargs):
        return self.response


class _PromptCaptureProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[tuple[str, str | None]] = []

    async def chat_completion(self, prompt, system_prompt=None, **kwargs):
        self.prompts.append((prompt, system_prompt))
        return self.response


class _UsageRouteProvider:
    async def chat_completion_response(self, prompt, system_prompt=None, **kwargs):
        return AIResponse(
            content="SKILL: profile | ARGS: show",
            model="test-model-1",
            finish_reason="stop",
            usage={
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
            },
        )

    async def chat_completion(self, prompt, system_prompt=None, **kwargs):
        return "SKILL: profile | ARGS: show"


class _NamedProvider:
    def __init__(self, name: str, available: bool = True) -> None:
        self._name = name
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def get_model_name(self) -> str:
        return f"{self._name}-model"


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


def test_personality_service_updates_profile_sections(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    service = PersonalityService()
    service.set_purpose("Menjadi asisten riset internal.")
    service.add_preference("jawaban singkat")
    service.add_constraint("jangan kirim data sensitif")
    service.add_context("user lebih suka ringkasan mingguan")

    profile = service.show_profile(max_chars=4000)

    assert "Menjadi asisten riset internal." in profile
    assert "- jawaban singkat" in profile
    assert "- jangan kirim data sensitif" in profile
    assert "- user lebih suka ringkasan mingguan" in profile
    assert service.list_preferences() == [
        "Utamakan bahasa Indonesia kecuali diminta sebaliknya.",
        "Utamakan solusi pragmatis dan berbasis data lokal.",
        "jawaban singkat",
    ]


def test_personality_service_bootstraps_structured_preferences_from_profile(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    agent_context.PROFILE_FILE.write_text(
        "# Agent Profile\n\n## Preferences\n- ringkas\n- fokus outcome\n",
        encoding="utf-8",
    )
    agent_context.PREFERENCES_FILE.write_text(json.dumps({"preferences": []}, indent=2), encoding="utf-8")
    agent_context._get_state_store().upsert_json_state(agent_context.PREFERENCE_STATE_KEY, {"preferences": []})

    service = PersonalityService()

    assert service.list_preferences() == ["ringkas", "fokus outcome"]
    assert "- ringkas" in service.build_prompt_block()


def test_context_budgeter_truncates_large_prompt_sections(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    service = PersonalityService()
    service.add_context("x" * 1200)
    monkeypatch.setenv("OTONOMASSIST_CONTEXT_BUDGET_CHARS", "600")
    monkeypatch.setenv("OTONOMASSIST_CONTEXT_PERSONALITY_MAX_CHARS", "300")
    monkeypatch.setenv("OTONOMASSIST_CONTEXT_RUNTIME_MAX_CHARS", "300")
    monkeypatch.setenv("OTONOMASSIST_CONTEXT_SKILLS_MAX_CHARS", "260")
    monkeypatch.setenv("OTONOMASSIST_CONTEXT_PROFILE_MAX_CHARS", "220")

    prompt = ContextBudgeter().build_orchestration_context(
        command="dependency runtime planner",
        skills_context="Available skills:\n" + ("- skill panjang sekali\n" * 40),
        personality_service=service,
    )

    assert "... (context budget truncated)" in prompt
    assert len(prompt) <= 640


def test_context_budgeter_redacts_secret_like_values_from_prompt_context(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    PersonalityService().add_context("api_key=sk-live-1234567890abcdefgh")
    agent_context.append_memory_entry("Bearer secret-token-abcdef123456 harus dirahasiakan", source="manual")

    prompt = ContextBudgeter().build_general_reasoning_context(
        query="rahasia runtime",
        personality_service=PersonalityService(),
    )

    assert "sk-live-1234567890abcdefgh" not in prompt
    assert "secret-token-abcdef123456" not in prompt
    assert "[REDACTED]" in prompt


def test_redaction_policy_can_be_disabled_for_local_debugging(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("OTONOMASSIST_PROMPT_REDACTION", "0")

    text = RedactionPolicy().redact_text("token=abc123456789")

    assert text == "token=abc123456789"


def test_habit_model_derives_frequent_source_and_command_prefix(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    assistant.handle_message("list", context=telegram_module.TransportContext(source="telegram", user_id="1", chat_id="1", roles=("telegram", "owner")))
    assistant.handle_message("list", context=telegram_module.TransportContext(source="telegram", user_id="1", chat_id="1", roles=("telegram", "owner")))
    assistant.handle_message("metrics", context=telegram_module.TransportContext(source="telegram", user_id="1", chat_id="1", roles=("telegram", "owner")))
    assistant.execute("list")

    habits = HabitModelService().refresh(limit=50)
    summaries = [item["summary"] for item in habits["habits"]]

    assert any("telegram" in summary for summary in summaries)
    assert any("`list`" in summary for summary in summaries)
    assert habits["signals_analyzed"] >= 4
    assert "## Habit Signals" in PersonalityService().build_prompt_block()


def test_get_secret_value_supports_uppercase_env_style_alias(tmp_path, monkeypatch):
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text(
        json.dumps(
            {
                "secrets": {
                    "OPENAI_API_KEY": {
                        "value": "sk-upper-alias-1234567890",
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(agent_context, "DATA_DIR", tmp_path)
    monkeypatch.setattr(agent_context, "SECRETS_FILE", secrets_file)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ACCESS", "rw")

    assert agent_context.get_secret_value("openai_api_key") == "sk-upper-alias-1234567890"


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
    monkeypatch.setattr(agent_context, "HABITS_FILE", tmp_path / "habits.json")
    monkeypatch.setattr(agent_context, "MEMORY_SUMMARIES_FILE", tmp_path / "memory_summaries.json")
    monkeypatch.setattr(agent_context, "IDENTITIES_FILE", tmp_path / "identities.json")
    monkeypatch.setattr(agent_context, "SESSIONS_FILE", tmp_path / "sessions.json")
    monkeypatch.setattr(agent_context, "SECRETS_FILE", tmp_path / "secrets.json")
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(workspace_guard, "WORKSPACE_ACCESS", "rw")

    (tmp_path / "memory.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "lessons.md").write_text("# Learned Lessons\n", encoding="utf-8")
    (tmp_path / "profile.md").write_text("# Agent Profile\n", encoding="utf-8")
    (tmp_path / "habits.json").write_text(json.dumps({"habits": [], "updated_at": "", "signals_analyzed": 0}, indent=2), encoding="utf-8")
    (tmp_path / "memory_summaries.json").write_text(json.dumps({"summaries": [], "updated_at": "", "prune_candidates": 0}, indent=2), encoding="utf-8")
    (tmp_path / "identities.json").write_text(json.dumps({"identities": [], "updated_at": ""}, indent=2), encoding="utf-8")
    (tmp_path / "sessions.json").write_text(json.dumps({"sessions": [], "updated_at": ""}, indent=2), encoding="utf-8")
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


def test_planner_next_respects_priority_and_dependencies(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    planner_module = _load_module(ROOT / "skills" / "planner" / "script" / "handler.py", "planner_handler_priority_test")

    planner_module.handle("add --priority 1 task rendah")
    planner_module.handle("add --priority 5 task tinggi")
    planner_module.handle("add --priority 9 --depends-on 2 task tergantung")

    before = planner_module.handle("next")
    agent_context.update_planner_task_status(2, "done")
    after = planner_module.handle("next")

    assert before["data"]["next_task"]["text"] == "task tinggi"
    assert after["data"]["next_task"]["text"] == "task tergantung"


def test_worker_processes_job_queue_from_ready_planner_task(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: _FakeProvider()))

    planner_module = _load_module(ROOT / "skills" / "planner" / "script" / "handler.py", "planner_handler_worker_test")
    worker_module = _load_module(ROOT / "skills" / "worker" / "script" / "handler.py", "worker_handler_test")

    planner_module.handle("add --priority 4 memory add dari worker")
    output = worker_module.handle("once --enqueue")
    planner_state = agent_context.load_planner_state()
    job_state = agent_context.load_job_queue_state()

    assert "Worker processing 1 job(s):" in output
    assert "processed: 1" in output
    assert planner_state["tasks"][0]["status"] == "done"
    assert any(job["status"] == "done" for job in job_state["jobs"])


def test_worker_until_idle_processes_multiple_jobs_and_records_runtime_state(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: _FakeProvider()))

    planner_module = _load_module(ROOT / "skills" / "planner" / "script" / "handler.py", "planner_handler_worker_until_idle")
    worker_module = _load_module(ROOT / "skills" / "worker" / "script" / "handler.py", "worker_handler_until_idle_test")

    planner_module.handle("add --priority 2 memory add tugas worker satu")
    planner_module.handle("add --priority 1 memory add tugas worker dua")
    output = worker_module.handle("until-idle --enqueue")
    job_state = agent_context.load_job_queue_state()

    assert "Worker processing until idle" in output
    assert "processed: 2" in output
    assert job_state["worker"]["last_status"] in {"active", "idle"}
    assert int(job_state["worker"]["last_processed"]) == 2
    assert all(job["status"] == "done" for job in job_state["jobs"])


def test_executor_resolves_natural_language_to_known_prefix(monkeypatch):
    module = _load_module(ROOT / "skills" / "executor" / "script" / "handler.py", "executor_handler_resolve_test")
    monkeypatch.setattr(module.AIProviderFactory, "auto_detect", staticmethod(lambda: _ResolveProvider()))

    resolved = module._resolve_command("cari presiden saat ini")
    assert resolved == "research siapa presiden saat ini"


def test_executor_retries_transient_task_failure_before_blocking(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    module = _load_module(ROOT / "skills" / "executor" / "script" / "handler.py", "executor_handler_retry_test")

    planner_file = agent_context.PLANNER_FILE
    planner_file.write_text(
        json.dumps(
            {
                "goal": "",
                "tasks": [
                    {
                        "id": 1,
                        "text": "workspace read README.md",
                        "status": "todo",
                        "notes": [],
                        "retry_count": 0,
                        "max_retries": 1,
                        "last_error": "",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    class FakeAssistant:
        def __init__(self, *args, **kwargs):
            pass

        def initialize(self):
            return None

        def execute(self, command):
            return "[ERROR] TIMEOUT\nSkill `workspace` melebihi batas waktu 0.05 detik."

    monkeypatch.setattr(module, "Assistant", FakeAssistant)

    first = module.handle("next")
    first_task = agent_context.get_planner_task(1)
    second = module.handle("next")
    second_task = agent_context.get_planner_task(1)

    assert "dijadwalkan ulang" in first
    assert first_task is not None and first_task["status"] == "todo"
    assert first_task["retry_count"] == 1
    assert "gagal dieksekusi" in second
    assert second_task is not None and second_task["status"] == "blocked"


def test_assistant_applies_formatter_from_user_intent(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "README.md").write_text("README contoh untuk formatter\n", encoding="utf-8")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("workspace cari README dalam bentuk tabel")

    assert "| Path | Line | Text |" in result
    assert "README.md" in result


def test_assistant_writes_execution_history_with_trace_id(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "README.md").write_text("README contoh untuk execution history\n", encoding="utf-8")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.handle_message("workspace read README.md")
    events = load_execution_events(limit=10)

    assert "workspace_read" in result
    event_types = [event["event_type"] for event in events]
    assert "command_received" in event_types
    assert "skill_started" in event_types
    assert "skill_completed" in event_types
    assert "command_completed" in event_types
    trace_ids = {event["trace_id"] for event in events if event.get("trace_id")}
    assert len(trace_ids) == 1
    assert any(event.get("skill_name") == "workspace" for event in events)


def test_assistant_updates_execution_metrics_for_completed_commands(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "README.md").write_text("README untuk metrics\n", encoding="utf-8")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    assistant.handle_message("workspace read README.md")

    metrics = get_execution_metrics_snapshot()
    assert metrics["summary"]["events_total"] >= 2
    assert metrics["summary"]["commands_total"] >= 1
    assert metrics["summary"]["skills_total"] >= 1
    assert "command_completed" in "".join(metrics["counters"].keys())


def test_conversation_service_records_interaction_trace_events(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    response = service.handle(
        InteractionRequest(
            message="help",
            source="api",
            user_id="user-42",
            session_id="session-42",
        )
    )
    events = load_execution_events(limit=10)
    event_types = [event["event_type"] for event in events]
    traced = [
        event for event in events
        if event["event_type"] in {"interaction_received", "interaction_completed", "command_received", "command_completed"}
    ]

    assert response.trace_id
    assert "interaction_received" in event_types
    assert "interaction_completed" in event_types
    assert len({event["trace_id"] for event in traced}) == 1


def test_worker_trace_records_job_task_and_cycle_events(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    agent_context.add_planner_task("memory add jejak worker trace", status="todo")

    result = process_job_queue(
        assistant,
        max_jobs=1,
        enqueue_first=True,
        until_idle=False,
        trace_id="worker-cycle-root",
        source="worker",
    )
    events = load_execution_events(limit=20)
    event_types = [event["event_type"] for event in events]

    assert result["processed"] == 1
    assert "worker_cycle_started" in event_types
    assert "worker_cycle_completed" in event_types
    assert "job_enqueued" in event_types
    assert "job_leased" in event_types
    assert "task_execution_started" in event_types
    assert "task_execution_completed" in event_types
    assert "job_completed" in event_types
    assert any(
        event["event_type"] == "task_execution_completed"
        and event["data"].get("parent_trace_id") == "worker-cycle-root"
        for event in events
    )


def test_scheduler_trace_records_scheduler_and_worker_cycles(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    agent_context.add_planner_task("memory add jejak scheduler trace", status="todo")

    result = run_scheduler(
        assistant,
        cycles=1,
        interval_seconds=0.0,
        max_jobs_per_cycle=1,
        enqueue_first=True,
        until_idle=True,
        trace_id="scheduler-root",
        source="scheduler",
    )
    events = load_execution_events(limit=30)
    event_types = [event["event_type"] for event in events]

    assert result["processed"] == 1
    assert "scheduler_run_started" in event_types
    assert "scheduler_run_completed" in event_types
    assert "scheduler_cycle_started" in event_types
    assert "scheduler_cycle_completed" in event_types
    assert "worker_cycle_completed" in event_types
    assert any(
        event["event_type"] == "scheduler_cycle_completed"
        and event["data"].get("parent_trace_id") == "scheduler-root"
        for event in events
    )


def test_worker_service_records_service_cycle_trace_events(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    agent_context.add_planner_task("memory add jejak service worker", status="todo")

    result = run_worker_service(
        skills_dir=ROOT / "skills",
        interval_seconds=0.0,
        steps=1,
        enqueue_first=True,
        until_idle=False,
        max_loops=1,
    )
    events = load_execution_events(limit=30)
    event_types = [event["event_type"] for event in events]

    assert result["loops"] == 1
    assert "service_run_started" in event_types
    assert "service_cycle_started" in event_types
    assert "service_cycle_completed" in event_types
    assert "service_run_completed" in event_types


def test_durable_state_store_imports_newer_legacy_planner_file(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    initial = agent_context.load_planner_state()
    assert initial["tasks"] == []

    planner_payload = {
        "goal": "import dari legacy file",
        "tasks": [
            {
                "id": 1,
                "text": "memory add dari legacy file",
                "status": "todo",
                "notes": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }
    time.sleep(0.02)
    agent_context.PLANNER_FILE.write_text(json.dumps(planner_payload, indent=2), encoding="utf-8")

    reloaded = agent_context.load_planner_state()

    assert reloaded["goal"] == "import dari legacy file"
    assert reloaded["tasks"][0]["text"] == "memory add dari legacy file"


def test_admin_api_snapshot_exposes_status_metrics_and_history(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "README.md").write_text("README untuk admin api\n", encoding="utf-8")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    assistant.handle_message("workspace read README.md")

    status_code, metrics_payload = build_admin_snapshot("/metrics")
    history_code, history_payload = build_admin_snapshot("/history?limit=5")
    jobs_code, jobs_payload = build_admin_snapshot("/jobs")
    events_code, events_payload = build_admin_snapshot("/events?limit=5")

    assert status_code == 200
    assert history_code == 200
    assert jobs_code == 200
    assert events_code == 200
    assert metrics_payload["summary"]["commands_total"] >= 1
    assert "queue_depth" in metrics_payload
    assert len(history_payload["events"]) >= 1
    assert events_payload["total_events"] >= 1
    assert "summary" in jobs_payload


def test_admin_api_requires_token_when_configured(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("OTONOMASSIST_ADMIN_TOKEN", "token-rahasia")

    unauthorized_code, unauthorized_payload = build_admin_snapshot("/status")
    authorized_code, authorized_payload = build_admin_snapshot(
        "/status",
        headers={"X-OtonomAssist-Token": "token-rahasia"},
    )

    assert unauthorized_code == 401
    assert unauthorized_payload["error"] == "unauthorized"
    assert authorized_code == 200
    assert "overall" in authorized_payload


def test_conversation_api_handles_message_and_returns_trace_metadata(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    status_code, payload = build_conversation_response(
        "/v1/messages",
        service=service,
        method="POST",
        body=json.dumps(
            {
                "message": "help",
                "source": "api",
                "user_id": "user-1",
                "session_id": "session-1",
                "roles": ["api", "trusted"],
            }
        ).encode("utf-8"),
    )

    assert status_code == 200
    assert payload["status"] == "ok"
    assert payload["source"] == "api"
    assert payload["user_id"] == "user-1"
    assert payload["session_id"] == "session-1"
    assert payload["identity_id"]
    assert payload["trace_id"]
    assert payload["metadata"]["roles"] == ["api", "trusted"]
    assert payload["response"].startswith("OtonomAssist - Available commands:")


def test_conversation_service_keeps_identity_continuity_across_channels_with_identity_hint(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    api_response = service.handle(
        InteractionRequest(
            message="help",
            source="api",
            user_id="api-user-1",
            session_id="api-session-1",
            metadata={"identity_hint": "refy@example.local"},
        )
    )
    telegram_response = service.handle(
        InteractionRequest(
            message="help",
            source="telegram",
            user_id="tg-user-99",
            chat_id="tg-chat-99",
            roles=("telegram", "owner"),
            metadata={"identity_hint": "refy@example.local"},
        )
    )

    identity_state = agent_context.load_identity_state()
    session_state = agent_context.load_session_state()

    assert api_response.identity_id == telegram_response.identity_id
    assert api_response.session_id != telegram_response.session_id
    assert len(identity_state["identities"]) == 1
    assert len(session_state["sessions"]) == 2
    assert identity_state["identities"][0]["identity_hint"] == "refy@example.local"


def test_conversation_api_requires_token_when_configured(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("OTONOMASSIST_CONVERSATION_TOKEN", "token-rahasia")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)
    body = json.dumps({"message": "help"}).encode("utf-8")

    unauthorized_code, unauthorized_payload = build_conversation_response(
        "/v1/messages",
        service=service,
        method="POST",
        body=body,
    )
    authorized_code, authorized_payload = build_conversation_response(
        "/v1/messages",
        service=service,
        method="POST",
        body=body,
        headers={"Authorization": "Bearer token-rahasia"},
    )

    assert unauthorized_code == 401
    assert unauthorized_payload["error"] == "unauthorized"
    assert authorized_code == 200
    assert authorized_payload["status"] == "ok"


def test_assistant_times_out_slow_skill_and_records_timeout_status(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("OTONOMASSIST_SKILL_TIMEOUT_SECONDS", "0.05")

    skills_dir = tmp_path / "skills"
    slow_dir = skills_dir / "slowpoke"
    (slow_dir / "script").mkdir(parents=True, exist_ok=True)
    (slow_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "# Slowpoke",
                "",
                "## Metadata",
                "- name: slowpoke",
                "- description: Skill lambat untuk test timeout",
                "- aliases: [slowpoke]",
                "- category: utility",
                "",
                "## Triggers",
                "- slowpoke",
            ]
        ),
        encoding="utf-8",
    )
    (slow_dir / "script" / "handler.py").write_text(
        "import time\n"
        "def handle(args: str) -> str:\n"
        "    time.sleep(0.2)\n"
        "    return 'selesai lambat'\n",
        encoding="utf-8",
    )

    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()

    result = assistant.handle_message("slowpoke jalan")
    events = load_execution_events(limit=10)

    assert "[ERROR] TIMEOUT" in result
    assert "slowpoke" in result
    assert any(event["event_type"] == "skill_completed" and event["status"] == "timeout" for event in events)
    assert any(event["event_type"] == "command_completed" and event["status"] == "timeout" for event in events)


def test_memory_search_uses_hybrid_retrieval_for_relevant_entries(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    memory_module = _load_module(ROOT / "skills" / "memory" / "script" / "handler.py", "memory_handler_hybrid_test")

    memory_module.handle("add catatan tentang planner dependency runtime")
    memory_module.handle("add catatan tentang cuaca jakarta")
    result = memory_module.handle("search dependency planner")

    assert result["type"] == "memory_search"
    assert result["data"]["retrieval_mode"] == "hybrid_semantic_recency"
    assert any("planner dependency runtime" in entry["text"] for entry in result["data"]["entries"])


def test_memory_search_supports_lightweight_semantic_aliases(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    memory_module = _load_module(ROOT / "skills" / "memory" / "script" / "handler.py", "memory_handler_semantic_alias_test")

    memory_module.handle("add budget token harian untuk provider openai")
    memory_module.handle("add catatan cuaca jakarta hari ini")
    result = memory_module.handle("search anggaran token remote")

    assert result["type"] == "memory_search"
    assert any("budget token harian" in entry["text"] for entry in result["data"]["entries"])


def test_memory_consolidate_writes_structured_summary_to_lessons(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    memory_module = _load_module(ROOT / "skills" / "memory" / "script" / "handler.py", "memory_handler_consolidate_test")

    memory_module.handle("add planner butuh dependency jelas")
    memory_module.handle("add planner butuh retry aman")
    memory_module.handle("add planner perlu observability")
    result = memory_module.handle("consolidate planner")
    lessons = agent_context.LESSONS_FILE.read_text(encoding="utf-8")

    assert "dikonsolidasikan ke lessons.md" in result
    assert "memory consolidation:" in lessons
    assert "topic=planner" in lessons


def test_memory_summary_persists_chunk_summaries_and_prune_candidates(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    memory_module = _load_module(ROOT / "skills" / "memory" / "script" / "handler.py", "memory_handler_summary_state_test")

    for index in range(12):
        memory_module.handle(f"add catatan penting nomor {index} tentang planner runtime")

    result = memory_module.handle("summary")
    summary_state = agent_context.load_memory_summary_state()

    assert result["type"] == "memory_summary"
    assert result["data"]["summary_chunks"]
    assert summary_state["summaries"]
    assert summary_state["prune_candidates"] >= 1


def test_telegram_transport_handles_message_without_network(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(telegram_module, "TELEGRAM_AUTH_FILE", tmp_path / ".otonomassist" / "telegram_auth.json")
    monkeypatch.setattr(telegram_module, "TELEGRAM_STATE_FILE", tmp_path / ".otonomassist" / "telegram_state.json")

    sent_messages: list[tuple[str, str]] = []
    chat_actions: list[tuple[str, str]] = []
    transport = TelegramPollingTransport(token="dummy-token", poll_timeout=1)
    monkeypatch.setattr(transport, "_send_message", lambda chat_id, text: sent_messages.append((chat_id, text)))
    monkeypatch.setattr(transport, "_send_chat_action", lambda chat_id, action="typing": chat_actions.append((chat_id, action)))
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
    assert chat_actions == [("12345", "typing")]
    assert sent_messages == [("12345", "handled-ok")]


def test_interfaces_telegram_exports_polling_transport(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    transport = InterfaceTelegramPollingTransport(token="dummy-token", poll_timeout=1)

    assert transport.auth_file.name == "telegram_auth.json"
    assert transport.state_file.name == "telegram_state.json"


def test_telegram_transport_refreshes_typing_for_long_running_message(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(telegram_module, "TELEGRAM_AUTH_FILE", tmp_path / ".otonomassist" / "telegram_auth.json")
    monkeypatch.setattr(telegram_module, "TELEGRAM_STATE_FILE", tmp_path / ".otonomassist" / "telegram_state.json")

    sent_messages: list[tuple[str, str]] = []
    chat_actions: list[tuple[str, str]] = []
    transport = TelegramPollingTransport(token="dummy-token", poll_timeout=1)
    monkeypatch.setattr(transport, "CHAT_ACTION_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(transport, "_send_message", lambda chat_id, text: sent_messages.append((chat_id, text)))
    monkeypatch.setattr(transport, "_send_chat_action", lambda chat_id, action="typing": chat_actions.append((chat_id, action)))
    monkeypatch.setattr(transport, "_is_authorized", lambda *args, **kwargs: True)
    monkeypatch.setattr(transport, "_resolve_roles", lambda *args, **kwargs: ("telegram", "owner"))

    class SlowAssistant:
        def handle_message(self, message, context=None):
            time.sleep(0.035)
            return "handled-slow"

    update = {
        "update_id": 4,
        "message": {
            "message_id": 1,
            "text": "test pesan pertama",
            "chat": {"id": 55555, "type": "private"},
            "from": {"id": 1001, "username": "slow-user"},
        },
    }

    transport._handle_update(SlowAssistant(), update)

    assert len(chat_actions) >= 2
    assert all(item == ("55555", "typing") for item in chat_actions)
    assert sent_messages == [("55555", "handled-slow")]


def test_assistant_returns_no_provider_error_for_unmatched_natural_language(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: None))

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("tolong kerjakan sesuatu yang tidak cocok dengan prefix skill")

    assert "[ERROR] NO_PROVIDER" in result
    assert "Tidak ada AI provider tersedia" in result


def test_assistant_ai_prompt_uses_personality_service_and_runtime_context(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    PersonalityService().add_preference("jawaban formal")
    agent_context.append_memory_entry("catatan penting tentang dependency runtime", source="manual")
    provider = _PromptCaptureProvider("SKILL: profile | ARGS: show")
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: provider))

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("tolong bantu pilih langkah dependency runtime berikutnya")

    assert "# Agent Profile" in result
    assert provider.prompts
    _, system_prompt = provider.prompts[-1]
    assert system_prompt is not None
    assert "Assistant personality context:" in system_prompt
    assert "- jawaban formal" in system_prompt
    assert "Persistent runtime context:" in system_prompt
    assert "catatan penting tentang dependency runtime" in system_prompt


def test_ai_route_records_token_usage_in_trace_and_metrics(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: _UsageRouteProvider()))

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("tolong route via ai dengan usage")

    assert "# Agent Profile" in result
    metrics = get_execution_metrics_snapshot()
    assert metrics["summary"]["ai_requests_total"] == 1
    assert metrics["summary"]["ai_total_tokens"] == 18
    assert metrics["summary"]["provider_latency_samples"] == 1
    token_usage = metrics["token_usage"]["_usageroute:test-model-1"]
    assert token_usage["prompt_tokens"] == 11
    assert token_usage["completion_tokens"] == 7
    latency = metrics["provider_latency"]["_usageroute:test-model-1"]
    assert latency["count"] == 1
    assert latency["last_status"] == "ok"
    events = load_execution_events(limit=10)
    ai_event = next(event for event in events if event["event_type"] == "ai_route_completed")
    assert ai_event["data"]["model"] == "test-model-1"
    assert ai_event["data"]["usage"]["total_tokens"] == 18
    assert ai_event["duration_ms"] is not None


def test_model_router_falls_back_to_local_provider_when_remote_budget_is_hard_blocked(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OTONOMASSIST_REMOTE_DAILY_TOKEN_BUDGET", "10")
    monkeypatch.setenv("OTONOMASSIST_BUDGET_ENFORCEMENT", "hard")
    monkeypatch.setenv("OTONOMASSIST_LOCAL_AI_PROVIDERS", "ollama,lmstudio")
    monkeypatch.setenv("OTONOMASSIST_REMOTE_AI_PROVIDERS", "openai,claude")

    agent_context.save_metrics_state(
        {
            "counters": {
                "ai_total_tokens_total": 18,
            },
            "timings": {},
            "token_usage": {
                "openai:test-model": {
                    "provider": "openai",
                    "model": "test-model",
                    "requests": 1,
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "total_tokens": 18,
                }
            },
            "updated_at": "",
        }
    )

    def fake_create(provider_name: str, config=None):
        if provider_name == "ollama":
            return _NamedProvider("ollama")
        if provider_name == "openai":
            return _NamedProvider("openai")
        raise ValueError(provider_name)

    monkeypatch.setattr(AIProviderFactory, "create", staticmethod(fake_create))
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: None))
    monkeypatch.setattr(AIProviderFactory, "get_current_provider_name", staticmethod(lambda: "openai"))

    router = ModelRouter(BudgetManager())
    provider = router.get_provider()

    assert provider is not None
    assert provider.__class__ is _NamedProvider
    assert provider.get_model_name() == "ollama-model"
    assert router.get_last_decision()["selected_provider"] == "ollama"
    assert router.get_last_decision()["budget_reason"] == "remote_daily_token_budget_exceeded"


def test_assistant_returns_no_provider_when_budget_hard_blocks_remote_and_no_local_is_available(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OTONOMASSIST_REMOTE_DAILY_TOKEN_BUDGET", "10")
    monkeypatch.setenv("OTONOMASSIST_BUDGET_ENFORCEMENT", "hard")
    monkeypatch.setenv("OTONOMASSIST_LOCAL_AI_PROVIDERS", "ollama")
    monkeypatch.setenv("OTONOMASSIST_REMOTE_AI_PROVIDERS", "openai,claude")

    agent_context.save_metrics_state(
        {
            "counters": {
                "ai_total_tokens_total": 18,
            },
            "timings": {},
            "token_usage": {
                "openai:test-model": {
                    "provider": "openai",
                    "model": "test-model",
                    "requests": 1,
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "total_tokens": 18,
                }
            },
            "updated_at": "",
        }
    )

    monkeypatch.setattr(AIProviderFactory, "create", staticmethod(lambda provider_name, config=None: _NamedProvider(provider_name, available=False)))
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: None))
    monkeypatch.setattr(AIProviderFactory, "get_current_provider_name", staticmethod(lambda: "openai"))

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("tolong route-kan command ini lewat AI")

    assert "[ERROR] NO_PROVIDER" in result
    assert "Tidak ada AI provider tersedia" in result


def test_assistant_returns_api_error_when_provider_fails(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: _BrokenProvider()))

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("tolong rute-kan command ini lewat AI")

    assert "[ERROR] API_ERROR" in result
    assert "provider boom" in result


def test_assistant_blocks_unapproved_telegram_user(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.handle_message(
        "memory list",
        context=telegram_module.TransportContext(
            source="telegram",
            user_id="200",
            chat_id="300",
            roles=("telegram",),
        ),
    )

    assert result == "Akses Telegram belum diotorisasi untuk operasi ini."
    events = load_execution_events(limit=10)
    assert any(
        event["event_type"] == "policy_decision"
        and event["status"] == "denied"
        and event["data"].get("reason") == "telegram_unapproved"
        for event in events
    )


def test_assistant_blocks_owner_only_executor_for_approved_telegram_user(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.handle_message(
        "executor next",
        context=telegram_module.TransportContext(
            source="telegram",
            user_id="200",
            chat_id="300",
            roles=("telegram", "approved"),
        ),
    )

    assert "dibatasi untuk owner Telegram" in result
    assert "`executor`" in result


def test_assistant_allows_read_only_jobs_view_for_approved_telegram_user(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.handle_message(
        "jobs",
        context=telegram_module.TransportContext(
            source="telegram",
            user_id="200",
            chat_id="300",
            roles=("telegram", "approved"),
        ),
    )

    assert result.startswith("Job Queue")


def test_assistant_blocks_jobs_enqueue_for_approved_telegram_user(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.handle_message(
        "jobs enqueue",
        context=telegram_module.TransportContext(
            source="telegram",
            user_id="200",
            chat_id="300",
            roles=("telegram", "approved"),
        ),
    )

    assert "runtime job Telegram dibatasi untuk owner" in result
    assert agent_context.load_job_queue_state()["jobs"] == []


def test_assistant_ai_route_still_applies_policy_for_owner_only_skill(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(
        AIProviderFactory,
        "auto_detect",
        staticmethod(lambda: _StructuredRouteProvider("SKILL: executor | ARGS: next")),
    )

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.handle_message(
        "tolong jalankan task berikutnya",
        context=telegram_module.TransportContext(
            source="telegram",
            user_id="200",
            chat_id="300",
            roles=("telegram", "approved"),
        ),
    )

    assert "dibatasi untuk owner Telegram" in result
    assert "`executor`" in result


def test_policy_service_honors_owner_only_prefix_override(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("TELEGRAM_OWNER_ONLY_PREFIXES", "workspace")

    decision = PolicyService().authorize_command(
        "workspace",
        "read README.md",
        context=telegram_module.TransportContext(
            source="telegram",
            user_id="200",
            chat_id="300",
            roles=("telegram", "approved"),
            trace_id="trace-policy-1",
        ),
    )

    assert decision.allowed is False
    assert decision.reason == "telegram_owner_only_prefix"
    assert "owner Telegram" in (decision.message or "")


def test_telegram_transport_prompts_pairing_for_unapproved_dm(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(telegram_module, "TELEGRAM_AUTH_FILE", tmp_path / ".otonomassist" / "telegram_auth.json")
    monkeypatch.setattr(telegram_module, "TELEGRAM_STATE_FILE", tmp_path / ".otonomassist" / "telegram_state.json")

    sent_messages: list[tuple[str, str]] = []
    transport = TelegramPollingTransport(token="dummy-token", poll_timeout=1)
    monkeypatch.setattr(transport, "_send_message", lambda chat_id, text: sent_messages.append((chat_id, text)))

    class FakeAssistant:
        def handle_message(self, message, context=None):
            raise AssertionError("assistant.handle_message should not be called for unapproved DM")

    update = {
        "update_id": 2,
        "message": {
            "message_id": 1,
            "text": "memory list",
            "chat": {"id": 54321, "type": "private"},
            "from": {"id": 777, "username": "pending-user"},
        },
    }

    transport._handle_update(FakeAssistant(), update)

    assert sent_messages == [
        (
            "54321",
            "Anda belum diizinkan menggunakan bot ini. "
            "Kirim `/pair` dari DM untuk membuat request akses.",
        )
    ]


def test_telegram_transport_rejects_auth_command_for_non_owner(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(telegram_module, "TELEGRAM_AUTH_FILE", tmp_path / ".otonomassist" / "telegram_auth.json")
    monkeypatch.setattr(telegram_module, "TELEGRAM_STATE_FILE", tmp_path / ".otonomassist" / "telegram_state.json")

    sent_messages: list[tuple[str, str]] = []
    transport = TelegramPollingTransport(token="dummy-token", poll_timeout=1)
    monkeypatch.setattr(transport, "_send_message", lambda chat_id, text: sent_messages.append((chat_id, text)))

    class FakeAssistant:
        def handle_message(self, message, context=None):
            raise AssertionError("assistant.handle_message should not be called for /auth")

    update = {
        "update_id": 3,
        "message": {
            "message_id": 1,
            "text": "/auth status",
            "chat": {"id": 12345, "type": "private"},
            "from": {"id": 222, "username": "not-owner"},
        },
    }

    transport._handle_update(FakeAssistant(), update)

    assert sent_messages == [("12345", "Command `/auth` hanya untuk owner bot.")]
