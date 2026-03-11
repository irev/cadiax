"""Conversation service boundary for inbound interactions."""

from __future__ import annotations

import time
from typing import Any

from otonomassist.core.execution_control import classify_result_status
from otonomassist.core.execution_history import append_execution_event, new_trace_id
from otonomassist.core.execution_metrics import record_execution_metric
from otonomassist.core.transport import TransportContext
from otonomassist.services.interactions.models import InteractionRequest, InteractionResponse


class ConversationService:
    """Service wrapper that normalizes channel interactions before invoking the assistant."""

    def __init__(self, assistant: Any) -> None:
        self.assistant = assistant

    def handle(self, request: InteractionRequest) -> InteractionResponse:
        """Handle one canonical interaction request."""
        trace_id = request.trace_id or new_trace_id()
        started = time.perf_counter()
        session_id = request.session_id or request.chat_id
        context = TransportContext(
            source=request.source,
            user_id=request.user_id,
            chat_id=request.chat_id,
            roles=request.roles,
            trace_id=trace_id,
        )
        append_execution_event(
            "interaction_received",
            trace_id=trace_id,
            status="started",
            source=request.source,
            command=request.message,
            data={
                "user_id": request.user_id or "",
                "session_id": session_id or "",
                "chat_id": request.chat_id or "",
                "roles": list(request.roles),
                "metadata": request.metadata,
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
                "session_id": session_id or "",
                "chat_id": request.chat_id or "",
                "roles": list(request.roles),
                "result_preview": result[:240],
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
            session_id=session_id,
            chat_id=request.chat_id,
            metadata={"roles": list(request.roles), **request.metadata},
        )

    def handle_message(self, message: str, context: TransportContext | None = None) -> str:
        """Compatibility wrapper for existing transports and CLI flows."""
        request = InteractionRequest(
            message=message,
            source=context.source if context else "cli",
            user_id=context.user_id if context else None,
            session_id=context.chat_id if context else None,
            chat_id=context.chat_id if context else None,
            roles=context.roles if context else (),
            trace_id=context.trace_id if context else None,
        )
        response = self.handle(request)
        if context is not None and not context.trace_id and response.trace_id:
            context.trace_id = response.trace_id
        return response.response
