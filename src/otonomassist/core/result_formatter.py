"""Structured result normalization and presentation formatting."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


SUPPORTED_VIEWS = {"auto", "json", "table", "summary", "short", "markdown"}


@dataclass
class PresentationRequest:
    """Requested presentation mode for a result."""

    view: str = "auto"
    explicit: bool = False


def extract_presentation_request(command: str, args: str) -> tuple[str, PresentationRequest]:
    """Extract view flags from skill args and infer view from the original command."""
    cleaned_args, explicit_view = _strip_view_flag(args)
    if explicit_view:
        return _strip_view_phrases(cleaned_args), PresentationRequest(view=explicit_view, explicit=True)

    inferred_view = infer_view_from_text(command)
    return _strip_view_phrases(cleaned_args), PresentationRequest(view=inferred_view, explicit=False)


def infer_view_from_text(text: str) -> str:
    """Infer the requested presentation mode from user text."""
    lowered = text.lower()
    if re.search(r"\b(json|raw data|data mentah|format json)\b", lowered):
        return "json"
    if re.search(r"\b(table|tabel|tabular)\b", lowered):
        return "table"
    if re.search(r"\b(summary|ringkas|ringkasan|rangkuman)\b", lowered):
        return "summary"
    if re.search(r"\b(singkat|brief|short|secara singkat|informasi singkat)\b", lowered):
        return "short"
    if re.search(r"\b(markdown|md)\b", lowered):
        return "markdown"
    return "auto"


def format_result(result: Any, request: PresentationRequest) -> str:
    """Format raw skill output into the requested presentation."""
    envelope = normalize_result(result)
    if envelope is None:
        return str(result)

    view = request.view
    if view == "auto":
        view = envelope["meta"].get("default_view", "json")

    if view not in SUPPORTED_VIEWS:
        view = envelope["meta"].get("default_view", "json")

    if view == "json":
        return json.dumps(envelope, ensure_ascii=False, indent=2)
    if view == "table":
        return _render_table(envelope)
    if view == "short":
        return _render_summary(envelope, short=True)
    if view == "markdown":
        return _render_markdown(envelope)
    return _render_summary(envelope, short=False)


def normalize_result(result: Any) -> dict[str, Any] | None:
    """Normalize arbitrary result data to a common envelope if possible."""
    if isinstance(result, dict):
        if {"type", "status", "data", "meta"}.issubset(result.keys()):
            return _normalize_envelope(result)
        return _normalize_envelope(
            {
                "type": "generic_result",
                "status": "ok",
                "data": result,
                "meta": {"default_view": "json"},
            }
        )

    if isinstance(result, list):
        return _normalize_envelope(
            {
                "type": "generic_result",
                "status": "ok",
                "data": {"items": result},
                "meta": {"default_view": "json"},
            }
        )

    if isinstance(result, str):
        text = result.strip()
        if not text:
            return None
        parsed = _try_parse_json(text)
        if isinstance(parsed, dict):
            return normalize_result(parsed)
        return None

    return None


def _normalize_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    """Normalize an envelope to the stable contract used by formatters."""
    data = envelope.get("data")
    meta = envelope.get("meta")
    if not isinstance(data, dict):
        data = {"value": data}
    if not isinstance(meta, dict):
        meta = {}

    normalized = {
        "type": str(envelope.get("type") or "generic_result"),
        "status": str(envelope.get("status") or "ok"),
        "data": data,
        "meta": {
            "default_view": str(meta.get("default_view") or "json"),
            "source_skill": str(meta.get("source_skill") or ""),
        },
    }
    for key, value in meta.items():
        if key not in normalized["meta"]:
            normalized["meta"][key] = value
    return normalized


def _render_summary(envelope: dict[str, Any], short: bool) -> str:
    """Render an envelope as a compact human-readable summary."""
    data = envelope["data"]
    if envelope["type"] == "research_result":
        answer = _as_text(data.get("answer")) or _as_text(data.get("summary"))
        lines = [answer or "Tidak ada jawaban."]
        if not short:
            summary = _as_text(data.get("summary"))
            if summary and summary != answer:
                lines.append(f"Ringkasan: {summary}")
            confidence = _as_text(data.get("confidence"))
            if confidence:
                lines.append(f"Confidence: {confidence}")
            verification = _as_text(data.get("verification_status"))
            if verification:
                lines.append(f"Verifikasi: {verification}")
            points = data.get("data_points")
            if isinstance(points, list):
                for item in points[:4]:
                    if isinstance(item, dict):
                        label = _as_text(item.get("label")) or "Data"
                        value = _as_text(item.get("value"))
                        date = _as_text(item.get("date"))
                        context = _as_text(item.get("context"))
                        parts = [value]
                        if date:
                            parts.append(date)
                        if context:
                            parts.append(context)
                        if any(parts):
                            lines.append(f"- {label}: {' | '.join(part for part in parts if part)}")
            sources = data.get("sources")
            if isinstance(sources, list) and sources:
                lines.append("Sumber:")
                for source in sources[:3]:
                    if isinstance(source, dict):
                        title = _as_text(source.get("title")) or _as_text(source.get("url"))
                        url = _as_text(source.get("url"))
                        if title:
                            lines.append(f"- {title}{f' ({url})' if url and url != title else ''}")
        return "\n".join(lines)

    summary = _as_text(data.get("summary"))
    if envelope["type"].startswith("planner_"):
        lines = [summary or "Planner result."]
        if short:
            return "\n".join(lines)
        goal = _as_text(data.get("goal"))
        if goal:
            lines.append(f"Goal: {goal}")
        next_task = data.get("next_task")
        if isinstance(next_task, dict):
            lines.append(f"Next: #{_as_text(next_task.get('id'))} {_as_text(next_task.get('text'))}")
        if not short and isinstance(data.get("tasks"), list):
            for task in data["tasks"][:5]:
                if isinstance(task, dict):
                    lines.append(
                        f"- #{_as_text(task.get('id'))} [{_as_text(task.get('status'))}] {_as_text(task.get('text'))}"
                    )
        return "\n".join(lines)

    if envelope["type"].startswith("workspace_"):
        lines = [summary or "Workspace result."]
        if envelope["type"] == "workspace_read":
            path = _as_text(data.get("path"))
            if path:
                lines.append(f"Path: {path}")
            content = _as_text(data.get("content"))
            if content and not short:
                lines.append("")
                lines.append(content)
            return "\n".join(lines)
        if not short:
            for item in _extract_tabular_rows(data)[:5]:
                lines.append("- " + " | ".join(item))
        return "\n".join(lines)

    if envelope["type"].startswith("memory_"):
        lines = [summary or "Memory result."]
        if short:
            return "\n".join(lines)
        entry = data.get("entry")
        if isinstance(entry, dict):
            lines.append(f"Memory #{_as_text(entry.get('id'))}")
            timestamp = _as_text(entry.get("timestamp"))
            source = _as_text(entry.get("source"))
            if timestamp:
                lines.append(f"Timestamp: {timestamp}")
            if source:
                lines.append(f"Source: {source}")
            text = _as_text(entry.get("text"))
            if text:
                lines.append(text)
            return "\n".join(lines)
        if isinstance(data.get("top_terms"), list) and data["top_terms"]:
            lines.append("Top terms: " + ", ".join(_as_text(term) for term in data["top_terms"]))
        for item in _extract_tabular_rows(data)[:5]:
            lines.append("- " + " | ".join(item))
        return "\n".join(lines)

    if envelope["type"] == "self_review_result":
        lines = [summary or "Self-review result."]
        if short:
            return "\n".join(lines)
        risk_level = _as_text(data.get("risk_level"))
        if risk_level:
            lines.append(f"Risk: {risk_level}")
        findings = data.get("findings")
        if isinstance(findings, list):
            for item in findings[:6]:
                if isinstance(item, dict):
                    lines.append(f"- {_as_text(item.get('text'))}")
        next_step = _as_text(data.get("next_step"))
        if next_step:
            lines.append(f"Next step: {next_step}")
        persistence = data.get("persistence")
        if isinstance(persistence, dict):
            follow_up_tasks = persistence.get("follow_up_tasks")
            if isinstance(follow_up_tasks, list) and follow_up_tasks:
                lines.append("Follow-up tasks:")
                for task in follow_up_tasks[:4]:
                    if isinstance(task, dict):
                        lines.append(
                            f"- #{_as_text(task.get('id'))} [{_as_text(task.get('status'))}] {_as_text(task.get('text'))}"
                        )
        return "\n".join(lines)

    if short:
        return _as_text(data.get("summary")) or _as_text(data.get("value")) or json.dumps(data, ensure_ascii=False)

    return json.dumps(data, ensure_ascii=False, indent=2)


def _render_markdown(envelope: dict[str, Any]) -> str:
    """Render an envelope as markdown."""
    data = envelope["data"]
    lines = [f"## {envelope['type']}"]
    answer = _as_text(data.get("answer"))
    if answer:
        lines.append(answer)
    summary = _as_text(data.get("summary"))
    if summary and summary != answer:
        lines.append("")
        lines.append(summary)

    points = data.get("data_points")
    if isinstance(points, list) and points:
        lines.append("")
        lines.append("### Data")
        for item in points:
            if isinstance(item, dict):
                label = _as_text(item.get("label")) or "Data"
                value = _as_text(item.get("value"))
                date = _as_text(item.get("date"))
                context = _as_text(item.get("context"))
                extra = " | ".join(part for part in (date, context) if part)
                lines.append(f"- {label}: {value}{f' ({extra})' if extra else ''}")

    sources = data.get("sources")
    if isinstance(sources, list) and sources:
        lines.append("")
        lines.append("### Sumber")
        for source in sources:
            if isinstance(source, dict):
                title = _as_text(source.get("title")) or _as_text(source.get("url"))
                url = _as_text(source.get("url"))
                lines.append(f"- {title}{f': {url}' if url else ''}")
    return "\n".join(lines)


def _render_table(envelope: dict[str, Any]) -> str:
    """Render an envelope as a markdown table where possible."""
    data = envelope["data"]
    if envelope["type"] == "research_result":
        points = data.get("data_points")
        rows: list[list[str]] = []
        if isinstance(points, list):
            for item in points:
                if isinstance(item, dict):
                    rows.append(
                        [
                            _as_text(item.get("label")),
                            _as_text(item.get("value")),
                            _as_text(item.get("date")),
                            _as_text(item.get("context")),
                        ]
                    )
        if rows:
            lines = [
                f"Jawaban: {_as_text(data.get('answer'))}",
                "",
                "| Label | Value | Date | Context |",
                "| --- | --- | --- | --- |",
            ]
            for row in rows:
                lines.append("| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |")
            return "\n".join(lines)

    headers, rows = _extract_named_table(data)
    if headers and rows:
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |")
        return "\n".join(lines)

    rows = [[key, _as_text(value)] for key, value in data.items() if not isinstance(value, (dict, list))]
    if rows:
        lines = [
            "| Key | Value |",
            "| --- | --- |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |")
        return "\n".join(lines)

    return json.dumps(envelope, ensure_ascii=False, indent=2)


def _strip_view_flag(args: str) -> tuple[str, str | None]:
    """Remove a leading --view flag from skill args."""
    match = re.match(r"^\s*--view\s+(json|table|summary|short|markdown)\b\s*(.*)$", args, re.IGNORECASE | re.DOTALL)
    if not match:
        return args, None
    view = match.group(1).lower()
    remainder = match.group(2).strip()
    return remainder, view


def _strip_view_phrases(text: str) -> str:
    """Remove common presentation-only phrases from args before skill execution."""
    cleaned = text.strip()
    patterns = [
        r"\bdalam bentuk tabel\b",
        r"\bdalam format tabel\b",
        r"\bbuat(?:kan)? dalam bentuk tabel\b",
        r"\bbentuk tabel\b",
        r"\bdalam bentuk json\b",
        r"\bdalam format json\b",
        r"\bformat json\b",
        r"\bdalam bentuk markdown\b",
        r"\bdalam format markdown\b",
        r"\bdalam bentuk ringkasan\b",
        r"\bdalam bentuk rangkuman\b",
        r"\bdalam bentuk summary\b",
        r"\binformasi singkat(?: saja)?\b",
        r"\bsecara singkat\b",
        r"\bringkas saja\b",
        r"\brangkuman saja\b",
        r"\bsummary saja\b",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,")
    return cleaned


def _extract_named_table(data: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Extract a named table from common structured-result collections."""
    mapping = (
        ("findings", ["index", "text"]),
        ("follow_up_tasks", ["id", "status", "text"]),
        ("entries", ["id", "timestamp", "source", "text"]),
        ("recent_entries", ["id", "timestamp", "source", "text"]),
        ("files", ["name", "path"]),
        ("tasks", ["id", "status", "text", "notes_count"]),
        ("matches", ["path", "line", "text"]),
        ("items", ["name", "relative_path", "kind", "depth"]),
        ("items", ["path"]),
        ("lines", ["line", "text"]),
    )
    for key, columns in mapping:
        value = data.get(key)
        if not isinstance(value, list) or not value:
            continue
        rows: list[list[str]] = []
        active_columns = [column for column in columns if any(isinstance(item, dict) and column in item for item in value)]
        if not active_columns:
            continue
        for item in value:
            if isinstance(item, dict):
                rows.append([_as_text(item.get(column)) for column in active_columns])
        if rows:
            headers = [column.replace("_", " ").title() for column in active_columns]
            return headers, rows
    return [], []


def _extract_tabular_rows(data: dict[str, Any]) -> list[list[str]]:
    """Extract lightweight row summaries from common list fields."""
    headers, rows = _extract_named_table(data)
    if headers and rows:
        return rows
    return []


def _try_parse_json(text: str) -> Any:
    """Parse JSON directly or recover the first object from text."""
    for candidate in (text, _strip_code_fences(text), _extract_json_object(text)):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _strip_code_fences(text: str) -> str:
    """Strip surrounding code fences if present."""
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def _extract_json_object(text: str) -> str:
    """Extract the first top-level JSON object from arbitrary text."""
    start = text.find("{")
    if start < 0:
        return ""

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return ""


def _escape_table_cell(value: str) -> str:
    """Escape markdown table cell delimiters."""
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _as_text(value: Any) -> str:
    """Convert arbitrary values to compact strings."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()
