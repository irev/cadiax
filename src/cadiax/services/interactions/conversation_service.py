"""Conversation service boundary for inbound interactions."""

from __future__ import annotations

import time
from typing import Any

from cadiax.core.execution_control import classify_result_status
from cadiax.core.execution_history import append_execution_event, new_trace_id
from cadiax.core.execution_metrics import record_execution_metric
from cadiax.core.transport import TransportContext
from cadiax.services.interactions.identity_service import IdentitySessionService
from cadiax.services.interactions.models import InteractionRequest, InteractionResponse
from cadiax.services.personality.startup_document_service import StartupDocumentService


class ConversationService:
    """Service wrapper that normalizes channel interactions before invoking the assistant."""

    def __init__(self, assistant: Any) -> None:
        self.assistant = assistant
        self.identity_service = IdentitySessionService()
        self.startup_documents = StartupDocumentService()

    def handle(self, request: InteractionRequest) -> InteractionResponse:
        """Handle one canonical interaction request."""
        trace_id = request.trace_id or new_trace_id()
        started = time.perf_counter()
        resolution = self.identity_service.resolve(request)
        session_id = resolution.session_id
        session_mode = _resolve_session_mode(request)
        agent_scope = _resolve_agent_scope(request)
        startup_snapshot = self.startup_documents.get_snapshot(
            session_mode=session_mode,
            agent_scope=agent_scope,
            roles=request.roles,
            max_chars=160,
        )
        context = TransportContext(
            source=request.source,
            user_id=request.user_id,
            chat_id=request.chat_id,
            session_id=session_id,
            identity_id=resolution.identity_id,
            roles=request.roles,
            trace_id=trace_id,
            session_mode=session_mode,
            agent_scope=agent_scope,
        )
        append_execution_event(
            "interaction_received",
            trace_id=trace_id,
            status="started",
            source=request.source,
            command=request.message,
            data={
                "user_id": request.user_id or "",
                "identity_id": resolution.identity_id,
                "session_id": session_id or "",
                "chat_id": request.chat_id or "",
                "roles": list(request.roles),
                "metadata": request.metadata,
                "agent_scope": agent_scope,
            },
        )
        result = self.assistant.handle_message(request.message, context=context)
        duration_ms = int((time.perf_counter() - started) * 1000)
        status = classify_result_status(result)
        append_execution_event(
            "interaction_completed",
            trace_id=trace_id,
            status=status,
            source=request.source,
            command=request.message,
            duration_ms=duration_ms,
            data={
                "user_id": request.user_id or "",
                "identity_id": resolution.identity_id,
                "session_id": session_id or "",
                "chat_id": request.chat_id or "",
                "roles": list(request.roles),
                "result_preview": result[:240],
                "agent_scope": agent_scope,
            },
        )
        record_execution_metric(
            "interaction_completed",
            status=status,
            source=request.source,
            duration_ms=duration_ms,
        )
        return InteractionResponse(
            response=result,
            source=request.source,
            trace_id=trace_id,
            user_id=request.user_id,
            session_id=request.session_id or request.chat_id,
            chat_id=request.chat_id,
            identity_id=resolution.identity_id,
            metadata={
                "roles": list(request.roles),
                "identity_created": resolution.identity_created,
                "session_created": resolution.session_created,
                "canonical_session_id": session_id,
                "session_mode": session_mode,
                "agent_scope": agent_scope,
                "startup_document_names": [
                    item["name"] for item in startup_snapshot["documents"] if item.get("availability") == "available"
                ],
                "startup_document_count": sum(
                    1 for item in startup_snapshot["documents"] if item.get("availability") == "available"
                ),
                "startup_restricted_document_names": [
                    item["name"] for item in startup_snapshot["documents"] if item.get("availability") == "restricted"
                ],
                "startup_daily_notes_loaded": bool(startup_snapshot.get("daily_notes")),
                "startup_curated_memory_loaded": bool(startup_snapshot.get("curated_memory")),
                **request.metadata,
            },
        )

    def handle_message(self, message: str, context: TransportContext | None = None) -> str:
        """Compatibility wrapper for existing transports and CLI flows."""
        request = InteractionRequest(
            message=message,
            source=context.source if context else "cli",
            user_id=context.user_id if context else None,
            session_id=context.session_id if context else context.chat_id if context else None,
            chat_id=context.chat_id if context else None,
            identity_id=context.identity_id if context else None,
            roles=context.roles if context else (),
            trace_id=context.trace_id if context else None,
            session_mode=context.session_mode if context else None,
            agent_scope=context.agent_scope if context else None,
        )
        response = self.handle(request)
        if context is not None and not context.trace_id and response.trace_id:
            context.trace_id = response.trace_id
        if context is not None:
            context.session_id = str(response.metadata.get("canonical_session_id") or response.session_id or "")
            context.identity_id = response.identity_id
        return response.response


def _resolve_session_mode(request: InteractionRequest) -> str:
    explicit = str(request.session_mode or request.metadata.get("session_mode") or "").strip().lower()
    if explicit in {"main", "shared"}:
        return explicit
    if request.source in {"cli"}:
        return "main"
    if request.source == "api" and not request.chat_id:
        return "main"
    return "shared"


def _resolve_agent_scope(request: InteractionRequest) -> str:
    explicit = str(request.agent_scope or request.metadata.get("agent_scope") or request.metadata.get("scope") or "").strip().lower()
    return explicit or "default"
