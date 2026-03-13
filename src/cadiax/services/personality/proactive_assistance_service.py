"""Contextual proactive assistance derived from runtime state and learning signals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cadiax.core import agent_context
from cadiax.core.execution_history import append_execution_event, new_trace_id
from cadiax.core.job_runtime import get_job_queue_summary
from cadiax.core.runtime_interaction import get_current_interaction_context
from cadiax.core.scheduler_runtime import get_scheduler_summary
from cadiax.services.personality.episodic_learning_service import EpisodicLearningService
from cadiax.services.personality.habit_model_service import HabitModelService


class ProactiveAssistanceService:
    """Generate contextual proactive recommendations from local signals."""

    def refresh(self) -> dict[str, Any]:
        """Regenerate proactive insights from current runtime and personality signals."""
        insights: list[dict[str, Any]] = []
        interaction = get_current_interaction_context()
        default_scope = str(interaction.get("agent_scope") or "default").strip().lower() or "default"
        default_roles = tuple(
            item_text
            for item_text in (str(item).strip().lower() for item in interaction.get("roles", ()))
            if item_text
        )
        planner = agent_context.load_planner_state()
        next_task = next((task for task in planner.get("tasks", []) if task.get("status") == "todo"), None)
        if next_task:
            insights.append(
                _build_insight(
                    kind="next_task_focus",
                    confidence="high",
                    summary=f"Task berikutnya sudah siap: #{next_task.get('id')} {next_task.get('text')}",
                    suggested_action="jobs enqueue",
                    reason="planner_ready_task_detected",
                    agent_scope=str(next_task.get("agent_scope") or default_scope),
                    roles=default_roles,
                )
            )

        runtime = get_job_queue_summary()
        if int(runtime.get("failed_jobs", 0) or 0) > 0:
            insights.append(
                _build_insight(
                    kind="runtime_recovery",
                    confidence="medium",
                    summary=f"Ada {runtime.get('failed_jobs')} job gagal yang perlu ditinjau.",
                    suggested_action="jobs list",
                    reason="failed_jobs_detected",
                    agent_scope=default_scope,
                    roles=default_roles,
                )
            )
        elif int(runtime.get("queued_jobs", 0) or 0) > 0:
            insights.append(
                _build_insight(
                    kind="runtime_follow_up",
                    confidence="medium",
                    summary=f"Ada {runtime.get('queued_jobs')} job queued yang bisa diproses.",
                    suggested_action="worker --until-idle",
                    reason="queued_jobs_detected",
                    agent_scope=default_scope,
                    roles=default_roles,
                )
            )

        scheduler = get_scheduler_summary()
        if str(scheduler.get("last_status", "")).strip().lower() == "quiet_hours":
            insights.append(
                _build_insight(
                    kind="scheduler_deferral",
                    confidence="medium",
                    summary="Scheduler terakhir tertahan karena quiet hours.",
                    suggested_action="privacy show",
                    reason="scheduler_quiet_hours_detected",
                    agent_scope=default_scope,
                    roles=default_roles,
                )
            )

        episodes = EpisodicLearningService().list_episodes(limit=3)
        if episodes:
            latest = episodes[0]
            if str(latest.get("status", "")).lower() in {"failed", "timeout"}:
                insights.append(
                    _build_insight(
                        kind="recent_failure_follow_up",
                        confidence="medium",
                        summary=f"Episode terakhir menunjukkan status {latest.get('status')}.",
                        suggested_action="history",
                        reason="recent_episode_failure",
                        agent_scope=str(latest.get("agent_scope") or default_scope),
                        roles=default_roles,
                    )
                )

        habits = HabitModelService().list_habits(limit=3)
        preferred_source = next((item for item in habits if item.get("kind") == "preferred_source"), None)
        if preferred_source:
            insights.append(
                _build_insight(
                    kind="channel_alignment",
                    confidence=str(preferred_source.get("confidence", "low")),
                    summary=f"Interaksi paling sering datang dari {preferred_source.get('value')}.",
                    suggested_action="profile show-structured",
                    reason="habit_preferred_source",
                    agent_scope=default_scope,
                    roles=default_roles,
                )
            )

        preference_profile = agent_context.get_preference_profile()
        if preference_profile.get("preferred_channels"):
            insights.append(
                _build_insight(
                    kind="preference_alignment",
                    confidence="medium",
                    summary="Preferred channels sudah terdefinisi untuk personalisasi respons.",
                    suggested_action="profile show-structured",
                    reason="structured_preference_profile_present",
                    agent_scope=default_scope,
                    roles=default_roles,
                )
            )

        deduped = _dedupe_insights(insights)
        state = {
            "insights": deduped[:6],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "insights_generated": len(deduped),
        }
        agent_context.save_proactive_insight_state(state)
        append_execution_event(
            "proactive_insights_refreshed",
            trace_id=new_trace_id(),
            status="ok",
            source="proactive",
            command="proactive refresh",
            data={
                "insight_count": len(state["insights"]),
                "agent_scopes": sorted({str(item.get("agent_scope") or "default") for item in state["insights"]}),
            },
        )
        return state

    def load_or_refresh(
        self,
        *,
        agent_scope: str | None = None,
        roles: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Return proactive insights, refreshing when empty."""
        state = agent_context.load_proactive_insight_state()
        if state.get("insights"):
            return self._filter_state(state, agent_scope=agent_scope, roles=roles)
        return self._filter_state(self.refresh(), agent_scope=agent_scope, roles=roles)

    def get_snapshot(
        self,
        *,
        agent_scope: str | None = None,
        roles: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Return current proactive insight snapshot without implicit refresh."""
        return self._filter_state(
            agent_context.load_proactive_insight_state(),
            agent_scope=agent_scope,
            roles=roles,
        )

    def list_insights(
        self,
        *,
        limit: int = 5,
        agent_scope: str | None = None,
        roles: tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        """Return current proactive insights."""
        return list(self.load_or_refresh(agent_scope=agent_scope, roles=roles).get("insights", []))[: max(1, limit)]

    def render_report(
        self,
        *,
        limit: int = 5,
        agent_scope: str | None = None,
        roles: tuple[str, ...] = (),
    ) -> str:
        """Render proactive assistance recommendations for operators."""
        insights = self.list_insights(limit=limit, agent_scope=agent_scope, roles=roles)
        lines = ["Proactive Assistance", ""]
        if not insights:
            lines.append("- belum ada insight proaktif")
            return "\n".join(lines)
        for item in insights:
            lines.append(
                f"- [{item.get('confidence', '-')}] {item.get('summary')} "
                f"(aksi: {item.get('suggested_action') or '-'}; scope: {item.get('agent_scope') or 'default'})"
            )
        return "\n".join(lines)

    def _filter_state(
        self,
        state: dict[str, Any],
        *,
        agent_scope: str | None,
        roles: tuple[str, ...],
    ) -> dict[str, Any]:
        insights = list(state.get("insights", []))
        filtered = (
            agent_context.filter_proactive_insights_by_scope(
                insights,
                agent_scope=agent_scope or "default",
                roles=roles,
            )
            if agent_scope
            else insights
        )
        by_scope: dict[str, int] = {}
        for item in filtered:
            scope_name = str(item.get("agent_scope") or "default")
            by_scope[scope_name] = by_scope.get(scope_name, 0) + 1
        return {
            "insights": filtered,
            "updated_at": str(state.get("updated_at", "")),
            "insights_generated": int(state.get("insights_generated", 0) or 0),
            "visible_insight_count": len(filtered),
            "total_insight_count": len(insights),
            "by_scope": by_scope,
            "filter_agent_scope": str(agent_scope or ""),
            "filter_roles": list(roles),
        }


def _dedupe_insights(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("reason", "") or item.get("kind", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _build_insight(
    *,
    kind: str,
    confidence: str,
    summary: str,
    suggested_action: str,
    reason: str,
    agent_scope: str,
    roles: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "kind": kind,
        "confidence": confidence,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "suggested_action": suggested_action,
        "reason": reason,
        "agent_scope": str(agent_scope or "default").strip().lower() or "default",
        "roles": [str(item).strip().lower() for item in roles if str(item).strip()],
    }
