from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import time
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from otonomassist.core import agent_context  # noqa: E402
from otonomassist.core.execution_history import append_execution_event, load_execution_events  # noqa: E402
from otonomassist.core.execution_metrics import get_execution_metrics_snapshot  # noqa: E402
from otonomassist.core.runtime_interaction import bind_interaction_context  # noqa: E402
from otonomassist.core import workspace_guard  # noqa: E402
from otonomassist.core.admin_api import build_admin_snapshot  # noqa: E402
from otonomassist.core.transport import TransportContext  # noqa: E402
from otonomassist.ai.base import AIResponse  # noqa: E402
from otonomassist.ai.factory import AIProviderFactory  # noqa: E402
from otonomassist.core.assistant import Assistant  # noqa: E402
from otonomassist.core.job_runtime import process_job_queue  # noqa: E402
from otonomassist.core.scheduler_runtime import run_scheduler  # noqa: E402
from otonomassist.interfaces.email import EmailInterfaceService  # noqa: E402
from otonomassist.interfaces.telegram import TelegramPollingTransport as InterfaceTelegramPollingTransport  # noqa: E402
from otonomassist.interfaces.whatsapp import WhatsAppInterfaceService  # noqa: E402
from otonomassist.platform import run_worker_service  # noqa: E402
from otonomassist.services import BudgetManager, ContextBudgeter, EpisodicLearningService, HabitModelService, ModelRouter, PersonalityService, PolicyService, RedactionPolicy  # noqa: E402
from otonomassist.services.personality.heartbeat_service import HeartbeatService  # noqa: E402
from otonomassist.services.personality.proactive_assistance_service import ProactiveAssistanceService  # noqa: E402
from otonomassist.services.privacy.privacy_control_service import PrivacyControlService  # noqa: E402
from otonomassist.services.interactions import (  # noqa: E402
    ConversationService,
    IdentitySessionService,
    InteractionRequest,
    NotificationDispatcher,
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
    monkeypatch.setattr(agent_context, "EPISODES_FILE", data_dir / "episodes.json")
    monkeypatch.setattr(agent_context, "PROACTIVE_INSIGHTS_FILE", data_dir / "proactive_insights.json")
    monkeypatch.setattr(agent_context, "IDENTITIES_FILE", data_dir / "identities.json")
    monkeypatch.setattr(agent_context, "SESSIONS_FILE", data_dir / "sessions.json")
    monkeypatch.setattr(agent_context, "NOTIFICATIONS_FILE", data_dir / "notifications.json")
    monkeypatch.setattr(agent_context, "EMAIL_MESSAGES_FILE", data_dir / "email_messages.json")
    monkeypatch.setattr(agent_context, "WHATSAPP_MESSAGES_FILE", data_dir / "whatsapp_messages.json")
    monkeypatch.setattr(agent_context, "PRIVACY_CONTROLS_FILE", data_dir / "privacy_controls.json")
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


class _FailIfCalledProvider:
    async def chat_completion(self, prompt, system_prompt=None, **kwargs):
        raise AssertionError("AI provider should not be called for heuristic routing")


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


class _ResearchProvider:
    async def web_search_completion(self, prompt, system_prompt=None, **kwargs):
        return json.dumps(
            {
                "query_type": "general_research",
                "verification_status": "web_verified",
                "summary": "Riset menemukan fakta utama yang relevan.",
                "answer": "Fakta riset utama tersimpan untuk tindak lanjut.",
                "confidence": "high",
                "data_points": [
                    {
                        "label": "fakta",
                        "value": "temuan penting",
                        "date": "2026-03-13",
                        "context": "hasil web",
                    }
                ],
                "notes": ["Sumber diverifikasi."],
                "gaps": [],
                "sources": [
                    {
                        "title": "Sumber Contoh",
                        "url": "https://example.com/fact",
                        "publisher": "Example",
                        "date": "2026-03-13",
                    }
                ],
            }
        )


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


def test_personality_service_persists_structured_preference_profile(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    service = PersonalityService()

    profile = service.update_structured_profile(
        preferred_channels=["telegram", "email"],
        preferred_brevity="ringkas",
        formality="semi-formal",
        proactive_mode="low",
        summary_style="bullet",
    )
    prompt = service.build_prompt_block()

    assert profile["preferred_channels"] == ["telegram", "email"]
    assert profile["preferred_brevity"] == "ringkas"
    assert "preferred_channels: telegram, email" in prompt
    assert "proactive_mode: low" in prompt


def test_personality_service_includes_identity_and_soul_documents(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text("# AGENTS\n\n- aturan workspace.\n", encoding="utf-8")
    (tmp_path / "USER.md").write_text("# User\n\n- suka jawaban ringkas.\n", encoding="utf-8")
    (tmp_path / "TOOLS.md").write_text("# Tools\n\n- tool lokal aktif.\n", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("# Identity\n\n- Fokus pada akurasi.\n", encoding="utf-8")
    (tmp_path / "SOUL.md").write_text("# Soul\n\n- Bergerak tenang dan reflektif.\n", encoding="utf-8")

    prompt = PersonalityService().build_prompt_block()

    assert "## Session Startup Docs" in prompt
    assert "aturan workspace" in prompt
    assert "## Identity" in prompt
    assert "Fokus pada akurasi." in prompt
    assert "## Soul" in prompt
    assert "Bergerak tenang dan reflektif." in prompt


def test_personality_service_filters_sensitive_startup_docs_by_scope_roles(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Ruang finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    (tmp_path / "USER.md").write_text("# User\n\n- data privat finansial.\n", encoding="utf-8")
    (tmp_path / "IDENTITY.md").write_text("# Identity\n\n- jaga akurasi finansial.\n", encoding="utf-8")
    (tmp_path / "SOUL.md").write_text("# Soul\n\n- reflektif.\n", encoding="utf-8")

    restricted_prompt = PersonalityService().build_prompt_block(
        session_mode="main",
        agent_scope="finance-agent",
        roles=("approved",),
    )
    allowed_prompt = PersonalityService().build_prompt_block(
        session_mode="main",
        agent_scope="finance-agent",
        roles=("finance",),
    )

    assert "- user: - dibatasi oleh scope policy" in restricted_prompt
    assert "- identity: - dibatasi oleh scope policy" in restricted_prompt
    assert "data privat finansial" not in restricted_prompt
    assert "jaga akurasi finansial" in allowed_prompt


def test_profile_skill_supports_structured_profile_commands(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    module = _load_module(ROOT / "skills" / "profile" / "script" / "handler.py", "profile_handler_structured_test")

    set_channels = module.handle("set-channels telegram,email")
    set_formality = module.handle("set-formality formal")
    set_brevity = module.handle("set-brevity singkat")
    show = module.handle("show-structured")
    remove_pref = module.handle("add-preference jawab ringkas")
    reset = module.handle("reset-preferences")

    assert "Preferred channels diperbarui." in set_channels
    assert "Formality preference diperbarui." in set_formality
    assert "Brevity preference diperbarui." in set_brevity
    assert "preferred_channels: telegram, email" in show
    assert "Preference ditambahkan" in remove_pref
    assert "Structured preferences direset." in reset


def test_observe_skill_returns_status_and_scope_filtered_events(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    observe_module = _load_module(ROOT / "skills" / "observe" / "script" / "handler.py", "observe_handler_test")
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    agent_context.append_memory_entry(
        "catatan default observasi",
        source="manual",
        agent_scope="default",
        session_mode="main",
    )
    with bind_interaction_context(source="cli", agent_scope="finance-agent", roles=("finance",)):
        agent_context.append_memory_entry(
            "catatan finance observasi",
            source="manual",
            agent_scope="finance-agent",
            session_mode="main",
        )
        append_execution_event(
            "command_completed",
            trace_id="trace-observe-finance",
            status="ok",
            source="cli",
            command="observe finance",
            data={"result_preview": "finance scope observed"},
        )

    status_result = observe_module.handle("status scope=finance-agent roles=finance")
    event_result = observe_module.handle("events scope=finance-agent roles=finance limit=10")

    assert status_result["type"] == "observe_status"
    assert status_result["data"]["scope_filter"]["agent_scope"] == "finance-agent"
    assert event_result["type"] == "observe_events"
    assert event_result["data"]["scope_filter"]["agent_scope"] == "finance-agent"
    assert event_result["data"]["returned_events"] >= 1


def test_assistant_executes_observe_skill_for_runtime_status(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("observe status")

    assert "Observe status:" in result
    assert "overall=" in result


def test_notify_skill_dispatches_single_and_batch_notifications(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    notify_module = _load_module(ROOT / "skills" / "notify" / "script" / "handler.py", "notify_handler_test")

    single = notify_module.handle("send build selesai channel=internal title=BuildAlert")
    batch = notify_module.handle(
        "batch deploy selesai delivery=email:ops@example.com delivery=whatsapp:+628123456789"
    )

    state = agent_context.load_notification_state()
    assert single["type"] == "notify_send"
    assert single["data"]["notification"]["title"] == "BuildAlert"
    assert batch["type"] == "notify_batch"
    assert batch["data"]["batch"]["delivery_count"] == 2
    assert len(state["notifications"]) == 3


def test_assistant_executes_notify_skill_for_outbound_message(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("notify send build selesai")
    notifications = agent_context.load_notification_state()

    assert "Notify send:" in result
    assert notifications["notifications"][0]["message"] == "build selesai"


def test_identity_skill_shows_and_resolves_continuity(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    identity_module = _load_module(ROOT / "skills" / "identity" / "script" / "handler.py", "identity_handler_test")
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )

    resolved = identity_module.handle(
        "resolve source=telegram user_id=200 session_id=chat-200 identity_hint=refy@example.local scope=finance-agent roles=finance"
    )
    shown = identity_module.handle("show scope=finance-agent roles=finance")

    assert resolved["type"] == "identity_resolve"
    assert resolved["data"]["identity_id"]
    assert shown["type"] == "identity_show"
    assert shown["data"]["snapshot"]["identity_count"] == 1
    assert shown["data"]["snapshot"]["session_count"] == 1


def test_assistant_executes_identity_skill_show(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("identity show")

    assert "Identity snapshot:" in result


def test_schedule_skill_shows_and_runs_scheduler(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    schedule_module = _load_module(ROOT / "skills" / "schedule" / "script" / "handler.py", "schedule_handler_test")
    agent_context.add_planner_task("memory add dari schedule skill", status="todo")

    shown = schedule_module.handle("show")
    ran = schedule_module.handle("run cycles=1 steps=3")

    assert shown["type"] == "schedule_show"
    assert ran["type"] == "schedule_run"
    assert ran["data"]["run"]["cycles"] == 1
    assert ran["data"]["run"]["status"] in {"idle", "active", "quiet_hours"}


def test_assistant_executes_schedule_skill_show(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("schedule show")

    assert "Schedule show:" in result


def test_policy_skill_shows_diagnostics_and_checks_decision(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    policy_module = _load_module(ROOT / "skills" / "policy" / "script" / "handler.py", "policy_handler_test")

    shown = policy_module.handle("show")
    checked = policy_module.handle("check prefix=executor args=next source=telegram roles=approved")

    assert shown["type"] == "policy_show"
    assert checked["type"] == "policy_check"
    assert checked["data"]["decision"]["allowed"] is False
    assert checked["data"]["decision"]["reason"] == "telegram_owner_only_prefix"


def test_assistant_executes_policy_skill_show(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("policy show")

    assert "Policy show:" in result


def test_expanded_capability_commands_cover_observe_notify_schedule_identity_policy_monitor(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    observe_module = _load_module(ROOT / "skills" / "observe" / "script" / "handler.py", "observe_handler_expansion_test")
    notify_module = _load_module(ROOT / "skills" / "notify" / "script" / "handler.py", "notify_handler_expansion_test")
    schedule_module = _load_module(ROOT / "skills" / "schedule" / "script" / "handler.py", "schedule_handler_expansion_test")
    identity_module = _load_module(ROOT / "skills" / "identity" / "script" / "handler.py", "identity_handler_expansion_test")
    policy_module = _load_module(ROOT / "skills" / "policy" / "script" / "handler.py", "policy_handler_expansion_test")
    monitor_module = _load_module(ROOT / "skills" / "monitor" / "script" / "handler.py", "monitor_handler_expansion_test")

    identity_module.handle(
        "resolve source=telegram user_id=777 session_id=chat-777 identity_hint=ops@example.local scope=ops-agent roles=ops"
    )
    notify_module.handle("send build selesai channel=internal title=OpsAlert")
    agent_context.add_planner_task("memory add dari schedule enqueue", status="todo")

    observe_identity = observe_module.handle("identity")
    observe_notifications = observe_module.handle("notifications")
    notify_history = notify_module.handle("history")
    schedule_enqueue = schedule_module.handle("enqueue")
    identity_sessions = identity_module.handle("sessions")
    policy_prefixes = policy_module.handle("prefixes")
    monitor_queue = monitor_module.handle("queue")
    monitor_latency = monitor_module.handle("latency")

    assert observe_identity["type"] == "observe_identity"
    assert observe_identity["data"]["snapshot"]["total_identity_count"] == 1
    assert observe_notifications["type"] == "observe_notifications"
    assert observe_notifications["data"]["snapshot"]["notification_count"] >= 1
    assert notify_history["type"] == "notify_history"
    assert notify_history["data"]["snapshot"]["notification_count"] >= 1
    assert schedule_enqueue["type"] == "schedule_enqueue"
    assert schedule_enqueue["data"]["job"]["task_text"] == "memory add dari schedule enqueue"
    assert identity_sessions["type"] == "identity_sessions"
    assert identity_sessions["data"]["session_count"] >= 1
    assert policy_prefixes["type"] == "policy_prefixes"
    assert "executor" in policy_prefixes["data"]["owner_only_prefixes"]
    assert monitor_queue["type"] == "monitor_queue"
    assert "queued=" in monitor_queue["data"]["summary"]
    assert monitor_latency["type"] == "monitor_latency"
    assert "providers=" in monitor_latency["data"]["summary"]


def test_assistant_executes_expanded_capability_commands(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    identity_module = _load_module(ROOT / "skills" / "identity" / "script" / "handler.py", "identity_handler_expansion_assistant_test")
    notify_module = _load_module(ROOT / "skills" / "notify" / "script" / "handler.py", "notify_handler_expansion_assistant_test")

    identity_module.handle(
        "resolve source=telegram user_id=991 session_id=chat-991 identity_hint=finance@example.local scope=finance-agent roles=finance"
    )
    notify_module.handle("send laporan siap channel=internal title=FinanceAlert")
    agent_context.add_planner_task("memory add untuk assistant expanded commands", status="todo")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    observe_result = assistant.execute("observe notifications")
    schedule_result = assistant.execute("schedule enqueue")
    identity_result = assistant.execute("identity sessions scope=finance-agent roles=finance")
    policy_result = assistant.execute("policy prefixes")
    monitor_result = assistant.execute("monitor queue")
    notify_result = assistant.execute("notify history")

    assert "Observe notifications:" in observe_result
    assert "Schedule enqueue:" in schedule_result
    assert "Identity sessions:" in identity_result
    assert "Policy prefixes:" in policy_result
    assert "Monitor queue:" in monitor_result
    assert "Notify history:" in notify_result


def test_monitor_skill_reports_operational_alerts(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monitor_module = _load_module(ROOT / "skills" / "monitor" / "script" / "handler.py", "monitor_handler_test")
    agent_context.save_metrics_state(
        {
            "counters": {
                "events_total": 10,
                "command_completed_total": 2,
                "skill_completed_total": 3,
                "skill_completed_status_timeout": 1,
                "command_completed_status_error": 1,
                "ai_provider_latency_total": 0,
            },
            "timings": {},
            "token_usage": {},
            "provider_latency": {
                "openai:gpt-4.1-mini": {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "count": 1,
                    "total_ms": 5200,
                    "max_ms": 5200,
                    "avg_ms": 5200.0,
                    "last_ms": 5200,
                    "last_status": "ok",
                }
            },
            "queue_depth": {
                "runtime_jobs": {
                    "queued": 6,
                    "leased": 1,
                    "done": 0,
                    "failed": 1,
                    "requeued": 0,
                    "current_depth": 7,
                    "high_watermark": 7,
                    "samples": 1,
                }
            },
            "updated_at": "",
        }
    )
    agent_context.save_job_queue_state(
        {
            "jobs": [
                {"id": 1, "task_id": 1, "task_text": "task", "status": "leased", "priority": 0},
                {"id": 2, "task_id": 2, "task_text": "task", "status": "failed", "priority": 0},
            ],
            "worker": {"last_status": "active", "last_processed": 1, "last_run_at": "", "last_trace_id": ""},
        }
    )

    result = monitor_module.handle("alerts")

    assert result["type"] == "monitor_alerts"
    assert result["data"]["health_status"] == "critical"
    assert result["data"]["dominant_alert"]["kind"] == "errors"
    assert result["data"]["dominant_alert"]["recommended_command"] == "monitor alerts"
    assert any(item["kind"] == "leased_jobs" for item in result["data"]["alerts"])
    assert any(item["kind"] == "timeouts" for item in result["data"]["alerts"])
    assert any(item["kind"] == "queue_depth" for item in result["data"]["alerts"])
    assert any(item["kind"] == "provider_latency" for item in result["data"]["alerts"])


def test_monitor_skill_health_and_queue_views_include_prioritized_runtime_signals(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monitor_module = _load_module(ROOT / "skills" / "monitor" / "script" / "handler.py", "monitor_handler_priority_test")

    PrivacyControlService().set_quiet_hours(start="00:00", end="23:59", enabled=True)
    agent_context.save_metrics_state(
        {
            "counters": {
                "events_total": 4,
                "command_completed_total": 1,
                "skill_completed_total": 1,
                "ai_provider_latency_total": 0,
            },
            "timings": {},
            "token_usage": {},
            "provider_latency": {},
            "queue_depth": {
                "runtime_jobs": {
                    "queued": 5,
                    "leased": 0,
                    "done": 0,
                    "failed": 0,
                    "requeued": 0,
                    "current_depth": 5,
                    "high_watermark": 6,
                    "samples": 2,
                }
            },
            "updated_at": "",
        }
    )
    agent_context.save_job_queue_state(
        {
            "jobs": [],
            "worker": {"last_status": "idle", "last_processed": 0, "last_run_at": "", "last_trace_id": ""},
        }
    )

    health_result = monitor_module.handle("health")
    queue_result = monitor_module.handle("queue")

    assert health_result["type"] == "monitor_health"
    assert health_result["data"]["health_status"] == "warning"
    assert health_result["data"]["dominant_alert"]["kind"] == "queue_depth"
    assert queue_result["type"] == "monitor_queue"
    assert "high_watermark=6" in queue_result["data"]["summary"]


def test_assistant_executes_monitor_skill_alerts(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("monitor alerts")

    assert "Monitor alerts:" in result


def test_decide_skill_selects_next_action_and_best_option(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    decide_module = _load_module(ROOT / "skills" / "decide" / "script" / "handler.py", "decide_handler_test")
    agent_context.add_planner_task("memory add catatan hasil decide", status="todo")

    next_result = decide_module.handle("next")
    between_result = decide_module.handle("between executor next | monitor alerts")

    assert next_result["type"] == "decide_next"
    assert next_result["data"]["decision"]["command"] == "executor next"
    assert between_result["type"] == "decide_between"
    assert between_result["data"]["selected"]["option"] == "executor next"


def test_decide_skill_prioritizes_alerts_quiet_hours_and_capability_aliases(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    decide_module = _load_module(ROOT / "skills" / "decide" / "script" / "handler.py", "decide_handler_priority_test")

    agent_context.save_job_queue_state(
        {
            "jobs": [
                {"id": 1, "task_id": 1, "task_text": "task gagal", "status": "failed", "priority": 0},
            ],
            "worker": {"last_status": "idle", "last_processed": 0, "last_run_at": "", "last_trace_id": ""},
        }
    )
    alert_result = decide_module.handle("next")
    alert_between = decide_module.handle("between act run | monitor alerts")

    assert alert_result["data"]["decision"]["command"] == "monitor alerts"
    assert alert_result["data"]["dominant_signal"] == "failed_jobs"
    assert alert_between["data"]["selected"]["option"] == "monitor alerts"

    agent_context.save_job_queue_state(
        {
            "jobs": [],
            "worker": {"last_status": "idle", "last_processed": 0, "last_run_at": "", "last_trace_id": ""},
        }
    )
    privacy_controls = PrivacyControlService()
    privacy_controls.set_quiet_hours(start="00:00", end="23:59", enabled=True)
    quiet_result = decide_module.handle("next")
    quiet_between = decide_module.handle("between schedule show | reflect")

    assert quiet_result["data"]["decision"]["command"] == "schedule show"
    assert quiet_result["data"]["dominant_signal"] == "quiet_hours_active"
    assert quiet_between["data"]["selected"]["option"] == "schedule show"


def test_assistant_executes_decide_skill_next(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    agent_context.add_planner_task("memory add dari decide assistant", status="todo")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("decide next")

    assert "Decide next:" in result


def test_standard_capability_alias_commands_route_to_existing_skills(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", lambda: _FakeProvider())

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    chat_result = assistant.execute("chat halo")
    plan_result = assistant.execute("plan list")
    act_result = assistant.execute("act run memory add alias capability")
    reflect_result = assistant.execute("reflect")
    inspect_result = assistant.execute("inspect tree .")
    persona_result = assistant.execute("persona show")
    review_result = assistant.execute("review text hasil alias review")

    assert "state terpantau" in chat_result
    assert "planner" in plan_result.lower() or "task" in plan_result.lower()
    assert "tersimpan" in act_result.lower()
    assert "Observasi" in reflect_result
    assert "Relative Path" in inspect_result
    assert "# Agent Profile" in persona_result
    assert "Self-review pada text" in review_result


def test_cross_skill_chain_observe_decide_act_executes_ready_task(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    decide_module = _load_module(ROOT / "skills" / "decide" / "script" / "handler.py", "decide_chain_handler_test")
    monkeypatch.setattr(
        decide_module,
        "get_config_status_data",
        lambda agent_scope=None, roles=(): {
            "overall": {"status": "healthy"},
            "runtime": {"queued_jobs": 0, "leased_jobs": 0, "failed_jobs": 0},
            "scheduler": {"last_status": "idle"},
            "metrics": {"summary": {"timeouts_total": 0, "errors_total": 0}},
            "policy": {"policy_denied_count": 0},
            "privacy_controls": {"quiet_hours_active": False},
            "issues": [],
            "scope_filter": {"agent_scope": agent_scope or "", "roles": list(roles)},
        },
    )
    agent_context.save_metrics_state(
        {
            "counters": {
                "events_total": 0,
                "command_completed_total": 0,
                "skill_completed_total": 0,
                "skill_completed_status_timeout": 0,
                "command_completed_status_error": 0,
                "skill_completed_status_error": 0,
                "ai_provider_latency_total": 1,
            },
            "timings": {},
            "token_usage": {},
            "provider_latency": {
                "stub:model": {
                    "provider": "stub",
                    "model": "model",
                    "count": 1,
                    "total_ms": 1,
                    "max_ms": 1,
                    "avg_ms": 1.0,
                    "last_ms": 1,
                    "last_status": "ok",
                }
            },
            "queue_depth": {},
            "updated_at": "",
        }
    )
    agent_context.save_job_queue_state({"jobs": [], "worker": {"last_status": "idle", "last_processed": 0, "last_run_at": "", "last_trace_id": ""}})
    task = agent_context.add_planner_task("memory add hasil chain observe decide act", status="todo")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    observed = assistant.execute("observe status")
    decision = decide_module.handle("next")
    executed = assistant.execute(decision["data"]["decision"]["command"])
    planner_state = agent_context.load_planner_state()
    task_state = next(item for item in planner_state["tasks"] if item["id"] == task["id"])

    assert "Observe status:" in observed
    assert decision["data"]["decision"]["command"] == "executor next"
    assert "Task #" in executed
    assert task_state["status"] == "done"


def test_cross_skill_chain_review_to_plan_creates_follow_up_task(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    review_result = assistant.execute("review text TODO dan api_key")
    planner_result = assistant.execute("plan next")

    assert "Self-review pada text" in review_result
    assert "Task berikutnya adalah #" in planner_result
    assert "agent-loop next" in planner_result or "follow-up self-review" in planner_result


def test_cross_skill_chain_research_to_memory_persists_distilled_note(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: _ResearchProvider()))
    research_module = _load_module(ROOT / "skills" / "research" / "script" / "handler.py", "research_chain_handler_test")

    research_result = asyncio.run(research_module.handle("fakta penting terbaru"))
    answer = research_result["data"]["answer"]

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    memory_result = assistant.execute(f"memory add {answer}")
    memories = agent_context.load_recent_memories(limit=10)

    assert research_result["type"] == "research_result"
    assert research_result["data"]["verification_status"] == "web_verified"
    assert "tersimpan" in memory_result.lower()
    assert any(answer in entry.get("text", "") for entry in memories)


def test_cross_skill_chain_inspect_to_plan_creates_backlog_entry(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "README.md").write_text("# Demo\n\nworkspace chain\n", encoding="utf-8")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    inspect_result = assistant.execute("inspect read README.md")
    plan_result = assistant.execute("plan add review README findings")
    next_result = assistant.execute("plan next")

    assert "README.md" in inspect_result
    assert "ditambahkan" in plan_result
    assert "review README findings" in next_result


def test_cross_skill_chain_monitor_decide_act_escalates_then_executes(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    decide_module = _load_module(ROOT / "skills" / "decide" / "script" / "handler.py", "decide_monitor_chain_handler_test")
    agent_context.save_metrics_state(
        {
            "counters": {
                "events_total": 3,
                "command_completed_total": 1,
                "skill_completed_total": 1,
                "skill_completed_status_timeout": 0,
                "command_completed_status_error": 1,
                "skill_completed_status_error": 0,
                "ai_provider_latency_total": 0,
            },
            "timings": {},
            "token_usage": {},
            "provider_latency": {},
            "queue_depth": {
                "runtime_jobs": {
                    "queued": 0,
                    "leased": 0,
                    "done": 0,
                    "failed": 1,
                    "requeued": 0,
                    "current_depth": 0,
                    "high_watermark": 1,
                    "samples": 1,
                }
            },
            "updated_at": "",
        }
    )
    agent_context.save_job_queue_state(
        {
            "jobs": [
                {"id": 1, "task_id": 1, "task_text": "task gagal", "status": "failed", "priority": 0},
            ],
            "worker": {"last_status": "idle", "last_processed": 0, "last_run_at": "", "last_trace_id": ""},
        }
    )

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    monitored = assistant.execute("monitor alerts")
    decision = decide_module.handle("between act run | monitor alerts")
    executed = assistant.execute(decision["data"]["selected"]["option"])

    assert "Monitor alerts:" in monitored
    assert decision["data"]["selected"]["option"] == "monitor alerts"
    assert "utama=errors (critical)" in executed or "utama=failed_jobs (critical)" in executed


def test_cross_skill_chain_persona_reflect_plan_links_preferences_to_follow_up(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", lambda: _FakeProvider())

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    persona_result = assistant.execute("persona set-brevity concise")
    reflect_result = assistant.execute("reflect")
    plan_result = assistant.execute("plan add tindak lanjut hasil refleksi persona")
    next_result = assistant.execute("plan next")

    assert "updated" in persona_result.lower() or "brevity" in persona_result.lower()
    assert "Observasi" in reflect_result
    assert "ditambahkan" in plan_result
    assert "tindak lanjut hasil refleksi persona" in next_result


def test_help_lists_standard_aliases_and_recommended_capability_chains(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    help_result = assistant.execute("help")

    assert "Standard capability aliases:" in help_result
    assert "- chat -> ai" in help_result
    assert "- plan -> planner" in help_result
    assert "- act -> executor" in help_result
    assert "- reflect -> agent-loop" in help_result
    assert "- inspect -> workspace" in help_result
    assert "- persona -> profile" in help_result
    assert "- review -> self-review" in help_result
    assert "Recommended capability chains:" in help_result
    assert "- observe -> decide -> act" in help_result
    assert "- review -> plan" in help_result
    assert "- research -> memory" in help_result
    assert "- inspect -> plan" in help_result


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


def test_runtime_context_loads_curated_memory_only_for_main_session(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "MEMORY.md").write_text("# Memory\n\n- fakta privat utama\n", encoding="utf-8")

    main_prompt = ContextBudgeter().build_general_reasoning_context(
        query="cek konteks",
        personality_service=PersonalityService(),
        session_mode="main",
    )
    shared_prompt = ContextBudgeter().build_general_reasoning_context(
        query="cek konteks",
        personality_service=PersonalityService(),
        session_mode="shared",
    )

    assert "fakta privat utama" in main_prompt
    assert "tidak dimuat pada shared session" in shared_prompt
    assert "fakta privat utama" not in shared_prompt


def test_curated_memory_write_requires_main_session(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    payload = agent_context.append_curated_memory(
        "preferensi privat utama",
        source="test",
        session_mode="main",
        agent_scope="default",
    )

    assert "MEMORY.md" in payload["path"]
    assert "preferensi privat utama" in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")

    with pytest.raises(PermissionError):
        agent_context.append_curated_memory(
            "tidak boleh bocor",
            source="test",
            session_mode="shared",
            agent_scope="group",
        )


def test_memory_entry_projects_to_daily_workspace_journal(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    entry = agent_context.append_memory_entry(
        "catatan operasional harian",
        source="manual",
        session_mode="shared",
        agent_scope="default",
    )

    journal_path = tmp_path / "memory" / f"{datetime.now(timezone.utc).date().isoformat()}.md"
    assert entry["daily_journal_written"] is True
    assert journal_path.exists()
    assert "catatan operasional harian" in journal_path.read_text(encoding="utf-8")


def test_runtime_context_filters_scope_bound_memory_and_daily_journal(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    agent_context.append_memory_entry(
        "catatan umum default",
        source="manual",
        session_mode="main",
        agent_scope="default",
    )
    agent_context.append_memory_entry(
        "catatan finansial rahasia",
        source="manual",
        session_mode="main",
        agent_scope="finance-agent",
    )

    default_prompt = agent_context.build_runtime_context_block(
        "catatan",
        session_mode="main",
        agent_scope="default",
        roles=("approved",),
    )
    restricted_prompt = agent_context.build_runtime_context_block(
        "finansial",
        session_mode="main",
        agent_scope="finance-agent",
        roles=("approved",),
    )
    allowed_prompt = agent_context.build_runtime_context_block(
        "finansial",
        session_mode="main",
        agent_scope="finance-agent",
        roles=("finance",),
    )

    assert "catatan umum default" in default_prompt
    assert "catatan finansial rahasia" not in default_prompt
    assert "catatan finansial rahasia" not in restricted_prompt
    assert "catatan finansial rahasia" in allowed_prompt


def test_curated_memory_and_daily_notes_follow_scope_role_filters(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    agent_context.append_curated_memory(
        "preferensi default umum",
        source="test",
        session_mode="main",
        agent_scope="default",
    )
    agent_context.append_curated_memory(
        "preferensi finansial khusus",
        source="test",
        session_mode="main",
        agent_scope="finance-agent",
    )

    restricted_curated = agent_context.load_workspace_curated_memory(
        agent_scope="finance-agent",
        roles=("approved",),
    )
    allowed_curated = agent_context.load_workspace_curated_memory(
        agent_scope="finance-agent",
        roles=("finance",),
    )
    default_curated = agent_context.load_workspace_curated_memory(
        agent_scope="default",
        roles=("approved",),
    )

    assert "preferensi finansial khusus" not in restricted_curated
    assert "preferensi finansial khusus" in allowed_curated
    assert "preferensi default umum" in default_curated
    assert "preferensi finansial khusus" not in default_curated


def test_memory_write_inherits_active_interaction_scope(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.handle_message(
        "memory add catatan scoped interaction",
        context=TransportContext(
            source="cli",
            roles=("finance",),
            session_mode="main",
            agent_scope="finance-agent",
        ),
    )

    entries = agent_context.load_all_memories(agent_scope="finance-agent", roles=("finance",))
    assert "tersimpan" in result
    assert entries[-1]["agent_scope"] == "finance-agent"
    assert "catatan scoped interaction" in entries[-1]["text"]


def test_executor_nested_command_inherits_active_interaction_scope(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    with bind_interaction_context(session_mode="main", agent_scope="finance-agent", roles=("finance",)):
        agent_context.add_planner_task("memory add catatan nested executor", status="todo")
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.handle_message(
        "executor next",
        context=TransportContext(
            source="cli",
            roles=("finance",),
            session_mode="main",
            agent_scope="finance-agent",
        ),
    )

    entries = agent_context.load_all_memories(agent_scope="finance-agent", roles=("finance",))
    assert "Task #1 selesai dieksekusi." in result
    assert any("catatan nested executor" in entry["text"] for entry in entries)


def test_memory_write_rejects_scope_override_mismatch_under_active_context(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )

    with bind_interaction_context(session_mode="main", agent_scope="finance-agent", roles=("finance",)):
        with pytest.raises(PermissionError):
            agent_context.append_memory_entry(
                "tidak boleh keluar scope aktif",
                source="manual",
                agent_scope="default",
            )


def test_planner_follow_up_inherits_active_interaction_scope(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    module = _load_module(ROOT / "skills" / "self-review" / "script" / "handler.py", "self_review_scope_test")

    with bind_interaction_context(session_mode="main", agent_scope="finance-agent", roles=("finance",)):
        result = module.handle("text TODO dan api_key")

    planner_state = agent_context.load_planner_state()
    scoped_tasks = [task for task in planner_state["tasks"] if task.get("agent_scope") == "finance-agent"]
    assert result["data"]["persistence"]["follow_up_tasks"]
    assert any(task["text"] == "agent-loop next" for task in scoped_tasks)
    assert any("memory add follow-up self-review" in task["text"] for task in scoped_tasks)


def test_executor_next_uses_only_visible_scope_tasks(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    agent_context.add_planner_task("memory add default task", status="todo")
    with bind_interaction_context(session_mode="main", agent_scope="finance-agent", roles=("finance",)):
        agent_context.add_planner_task("memory add finance task", status="todo")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    result = assistant.handle_message(
        "executor next",
        context=TransportContext(
            source="cli",
            roles=("finance",),
            session_mode="main",
            agent_scope="finance-agent",
        ),
    )

    planner_state = agent_context.load_planner_state()
    default_task = next(task for task in planner_state["tasks"] if task["text"] == "memory add default task")
    finance_task = next(task for task in planner_state["tasks"] if task["text"] == "memory add finance task")
    finance_entries = agent_context.load_all_memories(agent_scope="finance-agent", roles=("finance",))
    assert "Task #2 selesai dieksekusi." in result
    assert default_task["status"] == "todo"
    assert finance_task["status"] == "done"
    assert any("finance task" in entry["text"] for entry in finance_entries)


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


def test_episodic_learning_derives_recent_trace_summaries(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    assistant.execute("list")
    assistant.execute("metrics")

    episodes = EpisodicLearningService().refresh(limit=50)
    summaries = [item["summary"] for item in episodes["episodes"]]
    prompt = PersonalityService().build_prompt_block()

    assert episodes["episodes_analyzed"] >= 2
    assert any("command `list`" in summary or "command `metrics`" in summary for summary in summaries)
    assert "## Episodic Learning" in prompt


def test_proactive_assistance_generates_contextual_insights(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    agent_context.add_planner_task("memory add tindak lanjut penting", status="todo")
    assistant.execute("list")

    state = ProactiveAssistanceService().refresh()
    prompt = PersonalityService().build_prompt_block()

    assert state["insights_generated"] >= 1
    assert any(item["reason"] == "planner_ready_task_detected" for item in state["insights"])
    assert "## Proactive Assistance Hints" in prompt


def test_heartbeat_service_persists_runtime_pulse(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    agent_context.add_planner_task("memory add heartbeat task", status="todo")

    payload = HeartbeatService().pulse(trigger="test")

    assert payload["pulse_count"] >= 1
    assert payload["last_trigger"] == "test"
    assert payload["last_mode"] in {"ready", "active", "reflective", "deferred"}
    assert agent_context.load_heartbeat_state()["last_trigger"] == "test"
    assert (tmp_path / "memory" / "heartbeat-state.json").exists()


def test_heartbeat_service_runs_periodic_memory_maintenance(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    agent_context.save_heartbeat_state(
        {
            "pulse_count": 2,
            "last_pulse_at": "2026-03-12T00:00:00+00:00",
            "last_mode": "reflective",
            "last_summary": "lama",
            "last_trigger": "old",
            "last_actions": [],
        }
    )
    agent_context.append_memory_entry("catatan untuk maintenance heartbeat", source="manual")

    payload = HeartbeatService().pulse(trigger="maintenance-test")

    assert payload["pulse_count"] == 3
    assert "memory maintain" in payload["last_actions"]
    assert "heartbeat-maintenance:" in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")


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
    (tmp_path / "notifications.json").write_text(json.dumps({"notifications": [], "updated_at": ""}, indent=2), encoding="utf-8")
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
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n- aturan startup admin\n\n## Agent Scopes\n- finance-agent: Admin startup | roles: owner, finance\n",
        encoding="utf-8",
    )
    (tmp_path / "IDENTITY.md").write_text("# IDENTITY\n\n- observability aktif\n", encoding="utf-8")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    assistant.handle_message("workspace read README.md")

    status_code, metrics_payload = build_admin_snapshot("/metrics")
    history_code, history_payload = build_admin_snapshot("/history?limit=5")
    jobs_code, jobs_payload = build_admin_snapshot("/jobs")
    events_code, events_payload = build_admin_snapshot("/events?limit=5")
    startup_code, startup_payload = build_admin_snapshot("/startup?session_mode=shared&agent_scope=finance-agent&roles=approved")

    assert status_code == 200
    assert history_code == 200
    assert jobs_code == 200
    assert events_code == 200
    assert startup_code == 200
    assert metrics_payload["summary"]["commands_total"] >= 1
    assert "queue_depth" in metrics_payload
    assert len(history_payload["events"]) >= 1
    assert events_payload["total_events"] >= 1
    assert "summary" in jobs_payload
    assert startup_payload["startup"]["session_mode"] == "shared"
    assert startup_payload["startup"]["agent_scope"] == "finance-agent"
    assert startup_payload["startup"]["documents"][0]["name"] == "agents"
    identity_entry = next(item for item in startup_payload["startup"]["documents"] if item["name"] == "identity")
    assert identity_entry["availability"] == "restricted"


def test_admin_api_scope_filtered_status_and_jobs(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    agent_context.add_planner_task("memory add default task", status="todo")
    with bind_interaction_context(session_mode="main", agent_scope="finance-agent", roles=("finance",)):
        finance_task = agent_context.add_planner_task("memory add finance task", status="todo")
        agent_context.append_memory_entry("catatan finance", source="manual")
    job_state = agent_context.load_job_queue_state()
    job_state["jobs"] = [
        {
            "id": 1,
            "task_id": 1,
            "task_text": "memory add default task",
            "agent_scope": "default",
            "session_mode": "main",
            "priority": 0,
            "status": "queued",
        },
        {
            "id": 2,
            "task_id": finance_task["id"],
            "task_text": "memory add finance task",
            "agent_scope": "finance-agent",
            "session_mode": "main",
            "priority": 0,
            "status": "done",
        },
    ]
    agent_context.save_job_queue_state(job_state)

    status_code, status_payload = build_admin_snapshot("/status?agent_scope=finance-agent&roles=finance")
    jobs_code, jobs_payload = build_admin_snapshot("/jobs?agent_scope=finance-agent&roles=finance")

    assert status_code == 200
    assert jobs_code == 200
    assert status_payload["scope_filter"]["agent_scope"] == "finance-agent"
    assert status_payload["scope_filter"]["visible_memory_entries"] == 1
    assert status_payload["scope_filter"]["visible_planner_tasks"] == 1
    assert jobs_payload["summary"]["total_jobs"] == 1
    assert jobs_payload["queue"]["jobs"][0]["agent_scope"] == "finance-agent"


def test_admin_api_scope_filtered_history_and_events(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    assistant.handle_message(
        "memory add catatan default history",
        context=TransportContext(source="cli", roles=("approved",), session_mode="main", agent_scope="default"),
    )
    assistant.handle_message(
        "memory add catatan finance history",
        context=TransportContext(source="cli", roles=("finance",), session_mode="main", agent_scope="finance-agent"),
    )

    history_code, history_payload = build_admin_snapshot("/history?limit=50&agent_scope=finance-agent&roles=finance")
    events_code, events_payload = build_admin_snapshot("/events?limit=50&agent_scope=finance-agent&roles=finance")

    assert history_code == 200
    assert events_code == 200
    assert history_payload["events"]
    assert all((event.get("data") or {}).get("agent_scope") == "finance-agent" for event in history_payload["events"])
    assert events_payload["events"]
    assert all((event.get("data") or {}).get("agent_scope") == "finance-agent" for event in events_payload["events"])


def test_admin_api_scope_filtered_notifications_and_proactive(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    dispatcher = NotificationDispatcher()
    dispatcher.dispatch(channel="internal", title="Default", message="default notice")
    with bind_interaction_context(session_mode="main", agent_scope="finance-agent", roles=("finance",)):
        dispatcher.dispatch(channel="internal", title="Finance", message="finance notice")

    agent_context.save_proactive_insight_state(
        {
            "insights": [
                {
                    "kind": "default_scope_insight",
                    "confidence": "medium",
                    "summary": "Insight default.",
                    "suggested_action": "review default",
                    "reason": "default_scope",
                    "agent_scope": "default",
                },
                {
                    "kind": "finance_scope_insight",
                    "confidence": "high",
                    "summary": "Insight finance.",
                    "suggested_action": "review finance",
                    "reason": "finance_scope",
                    "agent_scope": "finance-agent",
                },
            ],
            "updated_at": "2026-03-12T00:00:00+00:00",
            "insights_generated": 2,
        }
    )

    status_code, status_payload = build_admin_snapshot("/status?agent_scope=finance-agent&roles=finance")
    proactive_code, proactive_payload = build_admin_snapshot("/proactive?agent_scope=finance-agent&roles=finance")

    assert status_code == 200
    assert proactive_code == 200
    assert status_payload["scope_filter"]["visible_notifications"] == 1
    assert status_payload["scope_filter"]["visible_proactive_insights"] == 1
    assert status_payload["notifications"]["notification_count"] == 1
    assert status_payload["notifications"]["latest_notification"]["agent_scope"] == "finance-agent"
    assert proactive_payload["proactive"]["visible_insight_count"] == 1
    assert proactive_payload["proactive"]["insights"][0]["agent_scope"] == "finance-agent"


def test_admin_api_scope_filtered_email_and_whatsapp_snapshots(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    EmailInterfaceService().send(
        to_address="ops-default@example.com",
        subject="Default Alert",
        body="default delivery",
        metadata={"agent_scope": "default", "roles": ["approved"]},
    )
    with bind_interaction_context(session_mode="main", agent_scope="finance-agent", roles=("finance",)):
        EmailInterfaceService().send(
            to_address="ops-finance@example.com",
            subject="Finance Alert",
            body="finance delivery",
        )
        WhatsAppInterfaceService().send(
            phone_number="+628123456789",
            display_name="Budi",
            body="finance whatsapp",
        )

    status_code, status_payload = build_admin_snapshot("/status?agent_scope=finance-agent&roles=finance")
    email_code, email_payload = build_admin_snapshot("/email?agent_scope=finance-agent&roles=finance")
    whatsapp_code, whatsapp_payload = build_admin_snapshot("/whatsapp?agent_scope=finance-agent&roles=finance")

    assert status_code == 200
    assert email_code == 200
    assert whatsapp_code == 200
    assert status_payload["scope_filter"]["visible_email_messages"] == 1
    assert status_payload["scope_filter"]["visible_whatsapp_messages"] == 1
    assert status_payload["email"]["message_count"] == 1
    assert status_payload["whatsapp"]["message_count"] == 1
    assert email_payload["email"]["latest_message"]["agent_scope"] == "finance-agent"
    assert whatsapp_payload["whatsapp"]["latest_message"]["agent_scope"] == "finance-agent"


def test_identity_session_service_separates_sessions_by_scope_and_filters_snapshot(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\n## Agent Scopes\n- finance-agent: Scope finansial | roles: owner, finance\n",
        encoding="utf-8",
    )
    service = IdentitySessionService()

    default_resolution = service.resolve(
        InteractionRequest(
            message="halo default",
            source="api",
            user_id="user-1",
            session_id="shared-session",
            roles=("approved",),
            agent_scope="default",
        )
    )
    finance_resolution = service.resolve(
        InteractionRequest(
            message="halo finance",
            source="api",
            user_id="user-1",
            session_id="shared-session",
            roles=("finance",),
            agent_scope="finance-agent",
        )
    )

    identity_code, identity_payload = build_admin_snapshot("/identity?agent_scope=finance-agent&roles=finance")
    status_code, status_payload = build_admin_snapshot("/status?agent_scope=finance-agent&roles=finance")

    assert default_resolution.identity_id == finance_resolution.identity_id
    assert default_resolution.session_id != finance_resolution.session_id
    assert identity_code == 200
    assert status_code == 200
    assert identity_payload["identity"]["identity_count"] == 1
    assert identity_payload["identity"]["session_count"] == 1
    assert identity_payload["identity"]["sessions"][0]["agent_scope"] == "finance-agent"
    assert status_payload["scope_filter"]["visible_identities"] == 1
    assert status_payload["scope_filter"]["visible_sessions"] == 1


def test_admin_api_requires_token_when_configured(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setenv("OTONOMASSIST_ADMIN_TOKEN", "token-rahasia")

    unauthorized_code, unauthorized_payload = build_admin_snapshot("/status")
    authorized_code, authorized_payload = build_admin_snapshot(
        "/status",
        headers={"X-Autonomiq-Token": "token-rahasia"},
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
    assert payload["response"].startswith("Autonomiq - Available commands:")


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


def test_webhook_event_without_message_is_accepted_into_event_bus(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    status_code, payload = build_conversation_response(
        "/v1/webhooks/events",
        service=service,
        method="POST",
        body=json.dumps(
            {
                "event_type": "calendar.reminder",
                "source": "webhook",
                "session_id": "hook-session-1",
                "metadata": {"kind": "reminder"},
            }
        ).encode("utf-8"),
    )

    events = build_admin_snapshot("/events?limit=20")[1]
    assert status_code == 202
    assert payload["status"] == "accepted"
    assert payload["event_topic"] == "webhook.event"
    assert events["topics"]["webhook.event"] >= 1


def test_webhook_message_routes_through_conversation_boundary(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    status_code, payload = build_conversation_response(
        "/v1/webhooks/events",
        service=service,
        method="POST",
        body=json.dumps(
            {
                "event_type": "message.created",
                "source": "webhook",
                "user_id": "web-user-1",
                "session_id": "web-session-1",
                "message": "help",
            }
        ).encode("utf-8"),
    )

    assert status_code == 200
    assert payload["status"] == "accepted"
    assert payload["interaction"]["response"].startswith("Autonomiq - Available commands:")
    assert payload["interaction"]["identity_id"]


def test_notification_api_dispatches_and_persists_notification(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    status_code, payload = build_conversation_response(
        "/v1/notifications",
        service=service,
        method="POST",
        body=json.dumps(
            {
                "channel": "operator",
                "title": "Build Alert",
                "message": "pipeline selesai",
                "target": "owner",
            }
        ).encode("utf-8"),
    )

    state = agent_context.load_notification_state()
    events = build_admin_snapshot("/events?limit=20")[1]
    assert status_code == 200
    assert payload["status"] == "ok"
    assert state["notifications"][0]["title"] == "Build Alert"


def test_notification_api_dispatches_multichannel_batch(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    status_code, payload = build_conversation_response(
        "/v1/notifications",
        service=service,
        method="POST",
        body=json.dumps(
            {
                "title": "Build Alert",
                "message": "pipeline selesai",
                "deliveries": [
                    {"channel": "email", "target": "ops@example.com"},
                    {"channel": "whatsapp", "target": "+628123456789", "metadata": {"display_name": "Budi"}},
                    {"channel": "webhook", "target": "build-hook"},
                ],
            }
        ).encode("utf-8"),
    )

    notification_state = agent_context.load_notification_state()
    email_state = agent_context.load_email_message_state()
    whatsapp_state = agent_context.load_whatsapp_message_state()
    events = build_admin_snapshot("/events?limit=50")[1]
    assert status_code == 200
    assert payload["status"] == "ok"
    assert payload["batch"]["delivery_count"] == 3
    assert len(notification_state["notifications"]) == 3
    assert notification_state["notifications"][0]["metadata"]["notification_batch_id"]
    assert email_state["messages"][0]["to_address"] == "ops@example.com"
    assert whatsapp_state["messages"][0]["phone_number"] == "+628123456789"
    assert any(event["topic"] == "notification.webhook" for event in events["events"])


def test_notification_dispatcher_defers_proactive_delivery_without_consent_during_quiet_hours(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    PrivacyControlService().set_quiet_hours(start="22:00", end="07:00", enabled=True)

    dispatcher = NotificationDispatcher()
    payload = dispatcher.dispatch(
        channel="email",
        title="Night Summary",
        message="ringkasan proaktif",
        target="ops@example.com",
        metadata={"proactive": True},
    )

    email_state = agent_context.load_email_message_state()
    notification_state = agent_context.load_notification_state()
    assert payload["status"] == "deferred"
    assert payload["metadata"]["deferred_reason"] == "proactive_consent_required"
    assert email_state["messages"] == []
    assert notification_state["notifications"][0]["status"] == "deferred"


def test_email_inbound_api_routes_through_conversation_boundary_and_persists_message(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    status, payload = build_conversation_response(
        "/v1/email/inbound",
        service=service,
        method="POST",
        body=json.dumps(
            {
                "from_address": "user@example.com",
                "to_address": "agent@example.com",
                "subject": "Planner Update",
                "body": "memory list",
                "thread_id": "thread-123",
            }
        ).encode("utf-8"),
    )

    state = agent_context.load_email_message_state()
    assert status == 200
    assert payload["status"] == "accepted"
    assert payload["interaction"]["source"] == "email"
    assert payload["interaction"]["identity_id"]
    assert payload["email"]["direction"] == "inbound"
    assert payload["email"]["thread_id"] == "thread-123"
    assert state["messages"][0]["from_address"] == "user@example.com"
    assert state["messages"][0]["subject"] == "Planner Update"


def test_email_outbound_api_dispatches_notification_and_persists_email_state(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    status, payload = build_conversation_response(
        "/v1/email/outbound",
        service=service,
        method="POST",
        body=json.dumps(
            {
                "to_address": "ops@example.com",
                "subject": "Build Alert",
                "message": "pipeline gagal",
            }
        ).encode("utf-8"),
    )

    email_state = agent_context.load_email_message_state()
    notification_state = agent_context.load_notification_state()
    assert status == 200
    assert payload["status"] == "ok"
    assert payload["email"]["direction"] == "outbound"
    assert payload["email"]["to_address"] == "ops@example.com"
    assert email_state["messages"][0]["subject"] == "Build Alert"
    assert notification_state["notifications"][0]["channel"] == "email"


def test_whatsapp_inbound_api_routes_through_conversation_boundary_and_persists_message(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    status, payload = build_conversation_response(
        "/v1/whatsapp/inbound",
        service=service,
        method="POST",
        body=json.dumps(
            {
                "phone_number": "+628123456789",
                "display_name": "Budi",
                "body": "memory list",
                "thread_id": "wa-thread-1",
            }
        ).encode("utf-8"),
    )

    state = agent_context.load_whatsapp_message_state()
    assert status == 200
    assert payload["status"] == "accepted"
    assert payload["interaction"]["source"] == "whatsapp"
    assert payload["interaction"]["identity_id"]
    assert payload["whatsapp"]["direction"] == "inbound"
    assert payload["whatsapp"]["thread_id"] == "wa-thread-1"
    assert state["messages"][0]["phone_number"] == "+628123456789"
    assert state["messages"][0]["display_name"] == "Budi"


def test_whatsapp_outbound_api_dispatches_notification_and_persists_state(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()
    service = ConversationService(assistant)

    status, payload = build_conversation_response(
        "/v1/whatsapp/outbound",
        service=service,
        method="POST",
        body=json.dumps(
            {
                "phone_number": "+628123456789",
                "display_name": "Budi",
                "message": "build selesai",
            }
        ).encode("utf-8"),
    )

    whatsapp_state = agent_context.load_whatsapp_message_state()
    notification_state = agent_context.load_notification_state()
    assert status == 200
    assert payload["status"] == "ok"
    assert payload["whatsapp"]["direction"] == "outbound"
    assert payload["whatsapp"]["phone_number"] == "+628123456789"
    assert whatsapp_state["messages"][0]["display_name"] == "Budi"
    assert notification_state["notifications"][0]["channel"] == "whatsapp"


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


def test_skill_completed_event_includes_skill_contract_metadata(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    trace_id = "trace-skill-contract"
    assistant.handle_message(
        "workspace tree .",
        context=TransportContext(source="cli", roles=("approved",), session_mode="main", agent_scope="default", trace_id=trace_id),
    )
    events = load_execution_events(limit=20)
    skill_event = next(
        event
        for event in events
        if event.get("event_type") == "skill_completed" and event.get("trace_id") == trace_id
    )

    contract = (skill_event.get("data") or {}).get("skill_contract") or {}
    assert contract["schema_version"] == "v1"
    assert contract["timeout_behavior"] == "fail_fast"
    assert contract["retry_policy"] == "none"


def test_execution_service_retries_transient_skill_once(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    skills_dir = tmp_path / "skills"
    flaky_dir = skills_dir / "flaky"
    state_file = tmp_path / "flaky_state.txt"
    (flaky_dir / "script").mkdir(parents=True, exist_ok=True)
    (flaky_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "# Flaky",
                "",
                "## Metadata",
                "- name: flaky",
                "- description: Skill transient untuk test retry",
                "- retry_policy: transient_once",
                "",
                "## Triggers",
                "- flaky",
            ]
        ),
        encoding="utf-8",
    )
    (flaky_dir / "script" / "handler.py").write_text(
        "from pathlib import Path\n"
        f"STATE_FILE = Path(r'{state_file}')\n"
        "def handle(args: str) -> str:\n"
        "    attempts = int(STATE_FILE.read_text(encoding='utf-8') or '0') if STATE_FILE.exists() else 0\n"
        "    attempts += 1\n"
        "    STATE_FILE.write_text(str(attempts), encoding='utf-8')\n"
        "    if attempts == 1:\n"
        "        return 'Error executing skill: connection reset by peer'\n"
        "    return 'retry success'\n",
        encoding="utf-8",
    )

    assistant = Assistant(skills_dir=skills_dir)
    assistant.initialize()
    trace_id = "trace-flaky-retry"
    result = assistant.handle_message(
        "flaky",
        context=TransportContext(source="cli", roles=("approved",), session_mode="main", agent_scope="default", trace_id=trace_id),
    )
    events = load_execution_events(limit=20)
    skill_event = next(
        event
        for event in events
        if event.get("event_type") == "skill_completed" and event.get("trace_id") == trace_id
    )

    assert result == "retry success"
    assert state_file.read_text(encoding="utf-8") == "2"
    assert (skill_event.get("data") or {}).get("attempt_count") == 2
    assert ((skill_event.get("data") or {}).get("skill_contract") or {}).get("retry_policy") == "transient_once"


def test_scheduler_skips_cycles_during_quiet_hours(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    PrivacyControlService().set_quiet_hours(start="00:00", end="23:59", enabled=True)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = run_scheduler(assistant, cycles=2, max_jobs_per_cycle=2)

    scheduler = agent_context.load_scheduler_state()
    events = load_execution_events(limit=10)
    assert result["status"] == "quiet_hours"
    assert result["processed"] == 0
    assert "quiet hours active" in result["output"]
    assert scheduler["last_status"] == "quiet_hours"
    assert any(
        event["event_type"] == "scheduler_run_completed" and event["status"] == "quiet_hours"
        for event in events
    )


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


def test_orchestration_prompt_is_compact_and_capability_level(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    prompt = assistant._get_orchestration_system_prompt("lihat status runtime")

    assert "Aturan inti:" in prompt
    assert "Contoh singkat:" in prompt
    assert "32." not in prompt
    assert "kirim notifikasi build selesai" not in prompt
    assert "Routing targets:" in prompt
    assert len(prompt) < 6500


def test_heuristic_router_handles_common_runtime_intents_without_ai(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: _FailIfCalledProvider()))
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    status_result = assistant.execute("lihat status runtime")
    alert_result = assistant.execute("lihat alert aktif")
    decide_result = assistant.execute("pilih next action terbaik")
    read_result = assistant.execute("baca README.md")
    tree_result = assistant.execute("lihat struktur file yang ada di workspace")
    notify_result = assistant.execute("kirim notifikasi build selesai")
    metrics = get_execution_metrics_snapshot()
    events = load_execution_events(limit=40)

    assert "Observe status:" in status_result
    assert "Monitor alerts:" in alert_result
    assert "Decide next:" in decide_result
    assert "README.md" in read_result
    assert "Relative Path" in tree_result
    assert "Notify send:" in notify_result
    assert metrics["summary"]["heuristic_routes_total"] >= 6
    assert metrics["summary"]["ai_requests_total"] == 0
    assert any(event["event_type"] == "command_routed" and event["status"] == "heuristic" for event in events)
    status_code, status_payload = build_admin_snapshot("/status")
    assert status_code == 200
    assert status_payload["routing"]["heuristic_routes_total"] >= 6
    assert status_payload["routing"]["ai_routes_total"] == 0
    assert status_payload["routing"]["heuristic_rate"].endswith("%")


def test_ai_route_records_token_usage_in_trace_and_metrics(tmp_path, monkeypatch):
    _configure_temp_agent_state(tmp_path, monkeypatch)
    monkeypatch.setattr(AIProviderFactory, "auto_detect", staticmethod(lambda: _UsageRouteProvider()))

    assistant = Assistant(skills_dir=ROOT / "skills")
    assistant.initialize()

    result = assistant.execute("tolong route via ai dengan usage")

    assert "# Agent Profile" in result
    metrics = get_execution_metrics_snapshot()
    assert metrics["summary"]["ai_requests_total"] == 1
    assert metrics["summary"]["ai_routes_total"] == 1
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
