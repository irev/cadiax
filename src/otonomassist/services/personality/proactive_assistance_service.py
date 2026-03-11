"""Contextual proactive assistance derived from runtime state and learning signals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from otonomassist.core import agent_context
from otonomassist.core.execution_history import append_execution_event, new_trace_id
from otonomassist.core.job_runtime import get_job_queue_summary
from otonomassist.core.scheduler_runtime import get_scheduler_summary
from otonomassist.services.personality.episodic_learning_service import EpisodicLearningService
from otonomassist.services.personality.habit_model_service import HabitModelService


class ProactiveAssistanceService:
    """Generate contextual proactive recommendations from local signals."""

    def refresh(self) -> dict[str, Any]:
        """Regenerate proactive insights from current runtime and personality signals."""
        insights: list[dict[str, Any]] = []
        planner = agent_context.load_planner_state()
        next_task = next((task for task in planner.get("tasks", []) if task.get("status") == "todo"), None)
        if next_task:
            insights.append(
                {
                    "kind": "next_task_focus",
                    "confidence": "high",
                    "summary": f"Task berikutnya sudah siap: #{next_task.get('id')} {next_task.get('text')}",
                    "suggested_action": f"jobs enqueue",
                    "reason": "planner_ready_task_detected",
                }
            )

        runtime = get_job_queue_summary()
        if int(runtime.get("failed_jobs", 0) or 0) > 0:
            insights.append(
                {
                    "kind": "runtime_recovery",
                    "confidence": "medium",
                    "summary": f"Ada {runtime.get('failed_jobs')} job gagal yang perlu ditinjau.",
                    "suggested_action": "jobs list",
                    "reason": "failed_jobs_detected",
                }
            )
        elif int(runtime.get("queued_jobs", 0) or 0) > 0:
            insights.append(
                {
                    "kind": "runtime_follow_up",
                    "confidence": "medium",
                    "summary": f"Ada {runtime.get('queued_jobs')} job queued yang bisa diproses.",
                    "suggested_action": "worker --until-idle",
                    "reason": "queued_jobs_detected",
                }
            )

        scheduler = get_scheduler_summary()
        if str(scheduler.get("last_status", "")).strip().lower() == "quiet_hours":
            insights.append(
                {
                    "kind": "scheduler_deferral",
                    "confidence": "medium",
                    "summary": "Scheduler terakhir tertahan karena quiet hours.",
                    "suggested_action": "privacy show",
                    "reason": "scheduler_quiet_hours_detected",
                }
            )

        episodes = EpisodicLearningService().list_episodes(limit=3)
        if episodes:
            latest = episodes[0]
            if str(latest.get("status", "")).lower() in {"failed", "timeout"}:
                insights.append(
                    {
                        "kind": "recent_failure_follow_up",
                        "confidence": "medium",
                        "summary": f"Episode terakhir menunjukkan status {latest.get('status')}.",
                        "suggested_action": "history",
                        "reason": "recent_episode_failure",
                    }
                )

        habits = HabitModelService().list_habits(limit=3)
        preferred_source = next((item for item in habits if item.get("kind") == "preferred_source"), None)
        if preferred_source:
            insights.append(
                {
                    "kind": "channel_alignment",
                    "confidence": preferred_source.get("confidence", "low"),
                    "summary": f"Interaksi paling sering datang dari {preferred_source.get('value')}.",
                    "suggested_action": "profile show-structured",
                    "reason": "habit_preferred_source",
                }
            )

        preference_profile = agent_context.get_preference_profile()
        if preference_profile.get("preferred_channels"):
            insights.append(
                {
                    "kind": "preference_alignment",
                    "confidence": "medium",
                    "summary": "Preferred channels sudah terdefinisi untuk personalisasi respons.",
                    "suggested_action": f"profile show-structured",
                    "reason": "structured_preference_profile_present",
                }
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
            data={"insight_count": len(state["insights"])},
        )
        return state

    def load_or_refresh(self) -> dict[str, Any]:
        """Return proactive insights, refreshing when empty."""
        state = agent_context.load_proactive_insight_state()
        if state.get("insights"):
            return state
        return self.refresh()

    def list_insights(self, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return current proactive insights."""
        return list(self.load_or_refresh().get("insights", []))[: max(1, limit)]

    def render_report(self, *, limit: int = 5) -> str:
        """Render proactive assistance recommendations for operators."""
        insights = self.list_insights(limit=limit)
        lines = ["Proactive Assistance", ""]
        if not insights:
            lines.append("- belum ada insight proaktif")
            return "\n".join(lines)
        for item in insights:
            lines.append(
                f"- [{item.get('confidence', '-')}] {item.get('summary')} "
                f"(aksi: {item.get('suggested_action') or '-'})"
            )
        return "\n".join(lines)


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
