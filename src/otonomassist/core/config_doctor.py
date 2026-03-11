"""Read-only configuration status and diagnostics."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

import otonomassist.core.agent_context as agent_context
from otonomassist.core.execution_control import get_skill_timeout_seconds
from otonomassist.core.event_bus import get_event_bus_snapshot
from otonomassist.core.external_assets import build_external_asset_audit_summary
from otonomassist.core.job_runtime import get_job_queue_summary
from otonomassist.core.execution_metrics import get_execution_metrics_snapshot
from otonomassist.core.scheduler_runtime import get_scheduler_summary
from otonomassist.interfaces.telegram import TelegramAuthService
from otonomassist.core.secure_storage import PORTABLE_KEY_FILE, get_secret_storage_info
from otonomassist.platform import get_process_manager_info, get_service_runtime_info, get_toolchain_info
from otonomassist.services.personality import HabitModelService, PersonalityService
from otonomassist.services.policy.policy_service import PolicyService
from otonomassist.services.runtime.budget_manager import BudgetManager
from otonomassist.services.runtime.context_budgeter import ContextBudgeter
from otonomassist.services.runtime.redaction_policy import RedactionPolicy


ENV_FILE = agent_context.PROJECT_ROOT / ".env"


def get_config_status_data() -> dict[str, object]:
    """Build machine-readable configuration status data."""
    agent_context.ensure_agent_storage()
    env_values = _load_env_values(ENV_FILE)
    provider_info = _build_provider_info(env_values)
    provider = provider_info["provider"]
    workspace_root = env_values.get("OTONOMASSIST_WORKSPACE_ROOT") or str(agent_context.PROJECT_ROOT / "workspace")
    workspace_access = env_values.get("OTONOMASSIST_WORKSPACE_ACCESS") or "ro"
    telegram_auth = TelegramAuthService.from_config(
        env_values,
        auth_file=agent_context.DATA_DIR / "telegram_auth.json",
    )
    telegram = _get_telegram_status(env_values, telegram_auth)
    policy = _get_policy_status(env_values)
    budget = BudgetManager(env_values).get_diagnostics()
    context_budget = ContextBudgeter(env_values).get_diagnostics()
    privacy = RedactionPolicy(env_values).get_diagnostics()
    secret_storage = get_secret_storage_info()
    process_manager = get_process_manager_info()
    service_runtime = get_service_runtime_info()
    toolchains = get_toolchain_info()
    external_assets = build_external_asset_audit_summary()
    event_bus = get_event_bus_snapshot()
    runtime = get_job_queue_summary()
    metrics = get_execution_metrics_snapshot()
    scheduler = get_scheduler_summary()
    state_storage = agent_context.get_state_storage_info()
    personality = PersonalityService()
    habits = HabitModelService().load_or_refresh()
    memory_summary = agent_context.load_memory_summary_state()
    identity_state = agent_context.load_identity_state()
    session_state = agent_context.load_session_state()
    issues = _collect_issues(env_values, provider_info, telegram, workspace_root, workspace_access)
    ai_status = _get_ai_status(provider, env_values, provider_info)
    workspace_status = _get_workspace_status(workspace_root, workspace_access)
    telegram_status = _get_telegram_section_status(telegram)
    storage_status = _get_storage_status()
    platform_status = _get_platform_status(secret_storage, process_manager, service_runtime, toolchains)
    runtime_status = _get_runtime_status(runtime)
    overall_status = _combine_statuses(
        ai_status,
        workspace_status,
        telegram_status,
        policy["status"],
        budget["status"],
        storage_status,
        platform_status,
        runtime_status,
    )
    return {
        "overall": {"status": overall_status},
        "ai": {
            "status": ai_status,
            "provider": provider,
            "configured": _provider_has_credential(provider, env_values),
            "config": provider_info.get("config", {}),
            "issues": list(provider_info.get("issues", [])),
        },
        "workspace": {
            "status": workspace_status,
            "root": workspace_root,
            "access": workspace_access,
            "root_exists": Path(workspace_root).exists(),
        },
        "telegram": {
            "status": telegram_status,
            **telegram,
        },
        "policy": policy,
        "budget": budget,
        "context_budget": context_budget,
        "privacy": privacy,
        "platform": {
            "status": platform_status,
            "os": os.name,
            "secret_backend": secret_storage["backend"],
            "secret_backend_detail": secret_storage["detail"],
            "process_manager": process_manager["backend"],
            "process_manager_detail": process_manager["detail"],
            "service_runtime": service_runtime["backend"],
            "service_runtime_detail": service_runtime["detail"],
        },
        "toolchains": toolchains,
        "runtime": {
            "status": runtime_status,
            **runtime,
        },
        "metrics": metrics,
        "scheduler": {
            "status": "healthy" if not scheduler["last_status"] or scheduler["last_status"] in {"idle", "active"} else "warning",
            **scheduler,
        },
        "storage": {
            "status": storage_status,
            "env_file": str(ENV_FILE if ENV_FILE.exists() else "(missing)"),
            "state_dir": str(agent_context.DATA_DIR),
            "secrets_file": str(agent_context.SECRETS_FILE),
            "execution_history_file": str(agent_context.EXECUTION_HISTORY_FILE),
            "metrics_file": str(agent_context.METRICS_FILE),
            "state_backend": state_storage["backend"],
            "state_db_file": state_storage["path"],
            "preference_count": len(personality.list_preferences()),
            "habit_count": len(habits.get("habits", [])),
            "identity_count": len(identity_state.get("identities", [])),
            "session_count": len(session_state.get("sessions", [])),
            "portable_key_file": str(PORTABLE_KEY_FILE),
            "skill_timeout_seconds": get_skill_timeout_seconds(),
        },
        "personality": {
            "habit_count": len(habits.get("habits", [])),
            "habit_signals_analyzed": habits.get("signals_analyzed", 0),
            "habits": habits.get("habits", []),
        },
        "memory": {
            "summary_count": len(memory_summary.get("summaries", [])),
            "prune_candidates": memory_summary.get("prune_candidates", 0),
            "updated_at": memory_summary.get("updated_at", ""),
        },
        "identity": {
            "identity_count": len(identity_state.get("identities", [])),
            "session_count": len(session_state.get("sessions", [])),
            "latest_identity_id": str(identity_state.get("identities", [])[-1].get("id", "")) if identity_state.get("identities") else "",
            "latest_session_id": str(session_state.get("sessions", [])[-1].get("id", "")) if session_state.get("sessions") else "",
        },
        "external_assets": {
            "asset_count": external_assets["asset_count"],
            "event_count": external_assets["event_count"],
            "incompatible_count": external_assets["incompatible_count"],
            "unapproved_count": external_assets["unapproved_count"],
            "undeclared_capability_count": external_assets["undeclared_capability_count"],
            "blocked_capability_count": external_assets["blocked_capability_count"],
            "isolated_skill_count": external_assets["isolated_skill_count"],
            "approval_by_state": external_assets["approval_by_state"],
            "approval_event_count": external_assets["approval_event_count"],
            "latest_approval_event": external_assets["latest_approval_event"],
            "trust_policy": external_assets["trust_policy"],
            "allowed_capabilities": external_assets["allowed_capabilities"],
            "layout": external_assets["layout"],
        },
        "event_bus": {
            "status": event_bus["status"],
            "total_events": event_bus["total_events"],
            "returned_events": event_bus["returned_events"],
            "automation_event_count": event_bus["automation_event_count"],
            "policy_event_count": event_bus["policy_event_count"],
            "external_event_count": event_bus["external_event_count"],
            "last_event_at": event_bus["last_event_at"],
            "last_event_topic": event_bus["last_event_topic"],
            "last_event_type": event_bus["last_event_type"],
            "topics": event_bus["topics"],
        },
        "issues": issues,
    }


def get_config_status_report() -> str:
    """Build a human-readable configuration report."""
    data = get_config_status_data()
    provider = str(data["ai"]["provider"])

    lines = [
        "OtonomAssist Config Status",
        "",
        "[Overall]",
        f"- status: {data['overall']['status']}",
        "",
        "[AI]",
        f"- status: {data['ai']['status']}",
        f"- provider: {provider}",
        f"- configured: {'yes' if data['ai']['configured'] else 'no'}",
    ]
    for key, value in data["ai"].get("config", {}).items():
        if "key" in key.lower():
            lines.append(f"- {key}: {_mask_value(value)}")
        else:
            lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "[Workspace]",
            f"- status: {data['workspace']['status']}",
            f"- root: {data['workspace']['root']}",
            f"- access: {data['workspace']['access']}",
            f"- root_exists: {'yes' if data['workspace']['root_exists'] else 'no'}",
        ]
    )

    lines.extend(
        [
            "",
            "[Telegram]",
            f"- status: {data['telegram']['status']}",
            f"- token_configured: {'yes' if data['telegram']['token_configured'] else 'no'}",
            f"- owner_ids: {data['telegram']['owner_ids'] or '-'}",
            f"- auth_file: {data['telegram']['auth_file']}",
            f"- dm_policy: {data['telegram']['dm_policy']}",
            f"- group_policy: {data['telegram']['group_policy']}",
            f"- require_mention: {'yes' if data['telegram']['require_mention'] else 'no'}",
            f"- approved_users: {data['telegram']['approved_users']}",
            f"- approved_groups: {data['telegram']['approved_groups']}",
            f"- pending_requests: {data['telegram']['pending_requests']}",
        ]
    )
    lines.extend(
        [
            "",
            "[Policy]",
            f"- status: {data['policy']['status']}",
            f"- telegram_owner_only_prefixes: {', '.join(data['policy']['telegram_owner_only_prefixes']) or '-'}",
            f"- telegram_approved_prefixes: {', '.join(data['policy']['telegram_approved_prefixes']) or '-'}",
            f"- telegram_read_only_prefixes: {', '.join(data['policy']['telegram_read_only_prefixes']) or '-'}",
            f"- telegram_mutating_prefixes: {', '.join(data['policy']['telegram_mutating_prefixes']) or '-'}",
            f"- policy_event_count: {data['policy']['policy_event_count']}",
            f"- policy_allowed_count: {data['policy']['policy_allowed_count']}",
            f"- policy_denied_count: {data['policy']['policy_denied_count']}",
            f"- last_policy_reason: {data['policy']['last_policy_reason'] or '-'}",
            f"- admin_api_token_required: {'yes' if data['policy']['admin_api_token_required'] else 'no'}",
            f"- conversation_api_token_required: {'yes' if data['policy']['conversation_api_token_required'] else 'no'}",
        ]
    )
    lines.extend(
        [
            "",
            "[Budget]",
            f"- status: {data['budget']['status']}",
            f"- enforcement: {data['budget']['enforcement']}",
            f"- daily_token_budget: {data['budget']['daily_token_budget'] or '-'}",
            f"- remote_daily_token_budget: {data['budget']['remote_daily_token_budget'] or '-'}",
            f"- ai_total_tokens: {data['budget']['ai_total_tokens']}",
            f"- remote_ai_total_tokens: {data['budget']['remote_ai_total_tokens']}",
            f"- remote_providers: {', '.join(data['budget']['remote_providers']) or '-'}",
            f"- local_providers: {', '.join(data['budget']['local_providers']) or '-'}",
        ]
    )
    lines.extend(
        [
            "",
            "[Context Budget]",
            f"- total_budget_chars: {data['context_budget']['total_budget_chars']}",
            f"- skills_max_chars: {data['context_budget']['skills_max_chars']}",
            f"- personality_max_chars: {data['context_budget']['personality_max_chars']}",
            f"- profile_max_chars: {data['context_budget']['profile_max_chars']}",
            f"- runtime_max_chars: {data['context_budget']['runtime_max_chars']}",
            f"- redaction_enabled: {'yes' if data['context_budget']['redaction_enabled'] else 'no'}",
        ]
    )
    lines.extend(
        [
            "",
            "[Privacy]",
            f"- status: {data['privacy']['status']}",
            f"- redaction_enabled: {'yes' if data['privacy']['redaction_enabled'] else 'no'}",
            f"- replacement_label: {data['privacy']['replacement_label']}",
            f"- pattern_count: {data['privacy']['pattern_count']}",
        ]
    )

    lines.extend(
        [
            "",
            "[Platform]",
            f"- status: {data['platform']['status']}",
            f"- os: {data['platform']['os']}",
            f"- secret_backend: {data['platform']['secret_backend']}",
            f"- secret_backend_detail: {data['platform']['secret_backend_detail']}",
            f"- process_manager: {data['platform']['process_manager']}",
            f"- process_manager_detail: {data['platform']['process_manager_detail']}",
            f"- service_runtime: {data['platform']['service_runtime']}",
            f"- service_runtime_detail: {data['platform']['service_runtime_detail']}",
        ]
    )

    lines.extend(
        [
            "",
            "[Toolchains]",
            f"- status: {data['toolchains']['status']}",
        ]
    )
    for name, info in data["toolchains"]["tools"].items():
        lines.append(
            f"- {name}: {'yes' if info['available'] else 'no'}"
            + (f" ({info['path']})" if info["path"] else "")
        )

    lines.extend(
        [
            "",
            "[Storage]",
            f"- status: {data['storage']['status']}",
            f"- env_file: {data['storage']['env_file']}",
            f"- state_dir: {data['storage']['state_dir']}",
            f"- secrets_file: {data['storage']['secrets_file']}",
            f"- execution_history_file: {data['storage']['execution_history_file']}",
            f"- metrics_file: {data['storage']['metrics_file']}",
            f"- state_backend: {data['storage']['state_backend']}",
            f"- state_db_file: {data['storage']['state_db_file']}",
            f"- preference_count: {data['storage']['preference_count']}",
            f"- habit_count: {data['storage']['habit_count']}",
            f"- identity_count: {data['storage']['identity_count']}",
            f"- session_count: {data['storage']['session_count']}",
            f"- portable_key_file: {data['storage']['portable_key_file']}",
            f"- skill_timeout_seconds: {data['storage']['skill_timeout_seconds']:.2f}",
        ]
    )
    lines.extend(
        [
            "",
            "[Personality]",
            f"- habit_count: {data['personality']['habit_count']}",
            f"- habit_signals_analyzed: {data['personality']['habit_signals_analyzed']}",
        ]
    )
    for habit in data["personality"].get("habits", [])[:3]:
        lines.append(
            f"- habit:{habit.get('kind')} -> {habit.get('value')} "
            f"(confidence={habit.get('confidence')}, evidence={habit.get('evidence_count')})"
        )
    lines.extend(
        [
            "",
            "[Memory]",
            f"- summary_count: {data['memory']['summary_count']}",
            f"- prune_candidates: {data['memory']['prune_candidates']}",
            f"- updated_at: {data['memory']['updated_at'] or '-'}",
        ]
    )
    lines.extend(
        [
            "",
            "[Identity]",
            f"- identity_count: {data['identity']['identity_count']}",
            f"- session_count: {data['identity']['session_count']}",
            f"- latest_identity_id: {data['identity']['latest_identity_id'] or '-'}",
            f"- latest_session_id: {data['identity']['latest_session_id'] or '-'}",
        ]
    )
    lines.extend(
        [
            "",
            "[Runtime]",
            f"- status: {data['runtime']['status']}",
            f"- total_jobs: {data['runtime']['total_jobs']}",
            f"- queued_jobs: {data['runtime']['queued_jobs']}",
            f"- leased_jobs: {data['runtime']['leased_jobs']}",
            f"- done_jobs: {data['runtime']['done_jobs']}",
            f"- failed_jobs: {data['runtime']['failed_jobs']}",
            f"- requeued_jobs: {data['runtime']['requeued_jobs']}",
            f"- last_worker_run_at: {data['runtime']['last_worker_run_at'] or '-'}",
            f"- last_worker_status: {data['runtime']['last_worker_status'] or '-'}",
            f"- last_worker_processed: {data['runtime']['last_worker_processed']}",
            f"- last_worker_trace_id: {data['runtime']['last_worker_trace_id'] or '-'}",
        ]
    )
    lines.extend(
        [
            "",
            "[Scheduler]",
            f"- status: {data['scheduler']['status']}",
            f"- last_run_at: {data['scheduler']['last_run_at'] or '-'}",
            f"- last_status: {data['scheduler']['last_status'] or '-'}",
            f"- last_cycles: {data['scheduler']['last_cycles']}",
            f"- last_processed: {data['scheduler']['last_processed']}",
            f"- last_trace_id: {data['scheduler']['last_trace_id'] or '-'}",
        ]
    )
    lines.extend(
        [
            "",
            "[Metrics]",
            f"- events_total: {data['metrics']['summary']['events_total']}",
            f"- commands_total: {data['metrics']['summary']['commands_total']}",
            f"- skills_total: {data['metrics']['summary']['skills_total']}",
            f"- timeouts_total: {data['metrics']['summary']['timeouts_total']}",
            f"- errors_total: {data['metrics']['summary']['errors_total']}",
            f"- provider_latency_samples: {data['metrics']['summary']['provider_latency_samples']}",
        ]
    )
    for name, summary in data["metrics"].get("queue_depth", {}).items():
        lines.append(
            f"- queue {name}: current_depth={summary.get('current_depth', 0)}, "
            f"high_watermark={summary.get('high_watermark', 0)}"
        )

    lines.extend(
        [
            "",
            "[External Assets]",
            f"- asset_count: {data['external_assets']['asset_count']}",
            f"- event_count: {data['external_assets']['event_count']}",
            f"- incompatible_count: {data['external_assets']['incompatible_count']}",
            f"- unapproved_count: {data['external_assets']['unapproved_count']}",
            f"- undeclared_capability_count: {data['external_assets']['undeclared_capability_count']}",
            f"- blocked_capability_count: {data['external_assets']['blocked_capability_count']}",
            f"- isolated_skill_count: {data['external_assets']['isolated_skill_count']}",
            f"- approval_event_count: {data['external_assets']['approval_event_count']}",
            f"- trust_policy: {data['external_assets']['trust_policy']}",
            f"- allowed_capabilities: {', '.join(data['external_assets']['allowed_capabilities']) or '-'}",
            f"- skills_dir: {data['external_assets']['layout']['skills_dir']}",
            f"- tools_dir: {data['external_assets']['layout']['tools_dir']}",
            f"- packages_dir: {data['external_assets']['layout']['packages_dir']}",
        ]
    )
    for state, count in data["external_assets"]["approval_by_state"].items():
        lines.append(f"- approval_{state}: {count}")
    latest_approval = data["external_assets"]["latest_approval_event"]
    if latest_approval.get("action"):
        lines.append(
            f"- latest_approval: {latest_approval['action']} {latest_approval['name']} by {latest_approval['actor'] or '-'}"
        )
    lines.extend(
        [
            "",
            "[Event Bus]",
            f"- status: {data['event_bus']['status']}",
            f"- total_events: {data['event_bus']['total_events']}",
            f"- returned_events: {data['event_bus']['returned_events']}",
            f"- automation_event_count: {data['event_bus']['automation_event_count']}",
            f"- policy_event_count: {data['event_bus']['policy_event_count']}",
            f"- external_event_count: {data['event_bus']['external_event_count']}",
            f"- last_event_topic: {data['event_bus']['last_event_topic'] or '-'}",
            f"- last_event_type: {data['event_bus']['last_event_type'] or '-'}",
        ]
    )
    for topic, count in data["event_bus"]["topics"].items():
        lines.append(f"- topic {topic}: {count}")

    if data["issues"]:
        lines.extend(["", "[Issues]"])
        lines.extend(f"- {issue}" for issue in data["issues"])
    else:
        lines.extend(["", "[Issues]", "- tidak ada masalah kritis terdeteksi"])

    lines.extend(["", "[Next Steps]"])
    if data["issues"]:
        lines.append("- Jalankan `otonomassist setup` untuk memperbaiki konfigurasi inti.")
    else:
        lines.append("- Konfigurasi inti terlihat sehat. Gunakan `otonomassist setup` bila ingin reconfigure.")
    if provider in {"openai", "claude"} and not data["ai"]["configured"]:
        lines.append("- Simpan API key ke encrypted secrets lokal agar provider remote bisa dipakai.")
    if data["telegram"]["token_configured"] and not data["telegram"]["owner_ids"]:
        lines.append("- Isi `TELEGRAM_OWNER_IDS` agar otorisasi Telegram tidak ambigu.")

    return "\n".join(lines)


def _load_env_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values = dotenv_values(path)
    return {key: value or "" for key, value in values.items()}


def _build_provider_info(env_values: dict[str, str]) -> dict[str, object]:
    provider = (env_values.get("AI_PROVIDER") or "openai").strip().lower()
    info: dict[str, object] = {
        "provider": provider,
        "available_providers": ["openai", "ollama", "lmstudio", "claude"],
        "config": {},
        "issues": [],
    }

    if provider == "openai":
        api_key = agent_context.get_secret_value("openai_api_key") or env_values.get("OPENAI_API_KEY", "")
        base_url = env_values.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        model = env_values.get("OPENAI_MODEL") or "gpt-4o-mini"
        fallback_model = env_values.get("OPENAI_FALLBACK_MODEL", "")
        info["config"] = {"base_url": base_url, "model": model}
        if api_key:
            info["config"]["api_key"] = api_key
        if fallback_model:
            info["config"]["fallback_model"] = fallback_model
        if not api_key:
            info["issues"].append("OPENAI_API_KEY tidak ditemukan di .env atau secrets")
        elif len(api_key) < 20:
            info["issues"].append("OPENAI_API_KEY tampak tidak valid (terlalu pendek)")
        return info

    if provider == "claude":
        api_key = agent_context.get_secret_value("anthropic_api_key") or env_values.get("ANTHROPIC_API_KEY", "")
        base_url = env_values.get("CLAUDE_BASE_URL") or "https://api.anthropic.com"
        model = env_values.get("CLAUDE_MODEL") or "claude-3-haiku-20240307"
        info["config"] = {"base_url": base_url, "model": model}
        if api_key:
            info["config"]["api_key"] = api_key
        if not api_key:
            info["issues"].append("ANTHROPIC_API_KEY tidak ditemukan di .env atau secrets")
        return info

    if provider == "ollama":
        base_url = env_values.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        model = env_values.get("OLLAMA_MODEL") or "llama3.2"
        info["config"] = {"base_url": base_url, "model": model}
        info["issues"].append(f"Pastikan Ollama running di {base_url}")
        return info

    if provider == "lmstudio":
        base_url = env_values.get("LMSTUDIO_BASE_URL") or "http://localhost:1234/v1"
        model = env_values.get("LMSTUDIO_MODEL") or "local-model"
        info["config"] = {"base_url": base_url, "model": model}
        info["issues"].append(f"Pastikan LM Studio running di {base_url}")
        return info

    info["issues"].append(f"AI_PROVIDER tidak dikenal: {provider}")
    return info


def _provider_has_credential(provider: str, env_values: dict[str, str]) -> bool:
    if provider == "openai":
        return bool(agent_context.get_secret_value("openai_api_key") or env_values.get("OPENAI_API_KEY"))
    if provider == "claude":
        return bool(agent_context.get_secret_value("anthropic_api_key") or env_values.get("ANTHROPIC_API_KEY"))
    return True


def _get_telegram_status(
    env_values: dict[str, str],
    auth_service: TelegramAuthService,
) -> dict[str, object]:
    auth_state = auth_service.get_diagnostics()
    owner_ids = _parse_csv(env_values.get("TELEGRAM_OWNER_IDS", ""))
    token_configured = bool(
        agent_context.get_secret_value("telegram_bot_token") or env_values.get("TELEGRAM_BOT_TOKEN")
    )
    return {
        "token_configured": token_configured,
        "auth_file": auth_state["auth_file"],
        "owner_ids": ", ".join(owner_ids),
        "dm_policy": (env_values.get("TELEGRAM_DM_POLICY") or "pairing").strip().lower() or "pairing",
        "group_policy": (env_values.get("TELEGRAM_GROUP_POLICY") or "allowlist").strip().lower() or "allowlist",
        "require_mention": bool(auth_state["require_mention"]),
        "approved_users": int(auth_state.get("approved_users", 0) or 0),
        "approved_groups": int(auth_state.get("approved_groups", 0) or 0),
        "pending_requests": int(auth_state.get("pending_requests", 0) or 0),
    }


def _get_policy_status(env_values: dict[str, str]) -> dict[str, object]:
    diagnostics = PolicyService().get_diagnostics(env_values)
    return {
        "status": "healthy",
        **diagnostics,
        "admin_api_token_required": bool(env_values.get("OTONOMASSIST_ADMIN_TOKEN", "").strip()),
        "conversation_api_token_required": bool(
            env_values.get("OTONOMASSIST_CONVERSATION_TOKEN", "").strip()
        ),
    }


def _collect_issues(
    env_values: dict[str, str],
    provider_info: dict[str, object],
    telegram: dict[str, object],
    workspace_root: str,
    workspace_access: str,
) -> list[str]:
    issues: list[str] = []
    provider = str(provider_info["provider"])
    if not ENV_FILE.exists():
        issues.append(".env belum ada.")
    if provider in {"openai", "claude"} and not _provider_has_credential(provider, env_values):
        issues.append(f"Credential untuk provider '{provider}' belum dikonfigurasi.")
    if workspace_access not in {"ro", "rw"}:
        issues.append(f"OTONOMASSIST_WORKSPACE_ACCESS tidak valid: {workspace_access}")
    if not Path(workspace_root).exists():
        issues.append("Workspace root belum ada di filesystem.")
    if bool(telegram["token_configured"]) and not str(telegram["owner_ids"]).strip():
        issues.append("Telegram token ada tetapi TELEGRAM_OWNER_IDS masih kosong.")
    for issue in provider_info.get("issues", []):
        issues.append(str(issue))
    return issues


def _get_ai_status(provider: str, env_values: dict[str, str], provider_info: dict[str, object]) -> str:
    if provider in {"openai", "claude"} and not _provider_has_credential(provider, env_values):
        return "critical"
    if provider_info.get("issues"):
        return "warning"
    return "healthy"


def _get_workspace_status(workspace_root: str, workspace_access: str) -> str:
    if workspace_access not in {"ro", "rw"}:
        return "critical"
    if not Path(workspace_root).exists():
        return "critical"
    if workspace_access == "rw":
        return "warning"
    return "healthy"


def _get_telegram_section_status(telegram: dict[str, object]) -> str:
    if not bool(telegram["token_configured"]):
        return "healthy"
    if not str(telegram["owner_ids"]).strip():
        return "warning"
    if int(telegram["pending_requests"]) > 0:
        return "warning"
    return "healthy"


def _get_storage_status() -> str:
    if not ENV_FILE.exists():
        return "warning"
    if not agent_context.DATA_DIR.exists():
        return "critical"
    if not agent_context.get_state_db_path().exists():
        return "critical"
    if not agent_context.SECRETS_FILE.exists():
        return "critical"
    return "healthy"


def _get_platform_status(
    secret_storage: dict[str, str],
    process_manager: dict[str, str],
    service_runtime: dict[str, object],
    toolchains: dict[str, object],
) -> str:
    return _combine_statuses(
        _normalize_status(secret_storage.get("status")),
        _normalize_status(process_manager.get("status")),
        _normalize_status(service_runtime.get("status")),
        _normalize_status(toolchains.get("status")),
    )


def _get_runtime_status(runtime: dict[str, object]) -> str:
    leased_jobs = int(runtime.get("leased_jobs", 0) or 0)
    failed_jobs = int(runtime.get("failed_jobs", 0) or 0)
    queued_jobs = int(runtime.get("queued_jobs", 0) or 0)
    if leased_jobs > 0:
        return "warning"
    if failed_jobs > 0 and queued_jobs == 0:
        return "warning"
    return "healthy"


def _combine_statuses(*statuses: str) -> str:
    if "critical" in statuses:
        return "critical"
    if "warning" in statuses:
        return "warning"
    return "healthy"


def _normalize_status(status: object) -> str:
    if status in {"healthy", "warning", "critical"}:
        return str(status)
    return "warning"


def _parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _mask_value(value: str) -> str:
    if not value:
        return "(kosong)"
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * 8}...{value[-4:]}"
