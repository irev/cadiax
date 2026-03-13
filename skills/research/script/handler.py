"""Research skill handler."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from cadiax.ai.factory import AIProviderFactory
from cadiax.core.result_builder import build_result

USAGE = (
    "Usage: research <pertanyaan>\n"
    "Contoh: research kapan idul fitri 2026 di indonesia"
)


async def handle(args: str) -> str:
    """Run grounded research for time-sensitive or real-world questions."""
    query = args.strip()
    if not query:
        return USAGE

    provider = AIProviderFactory.auto_detect()
    if not provider:
        return _wrap_result(
            _build_fallback_data(
                query=query,
                error="Tidak ada AI provider yang tersedia untuk research.",
                verification_status="unavailable",
            ),
        )

    now = datetime.now().astimezone()
    metadata = _build_request_metadata(query, now)
    system_prompt = _build_system_prompt()
    prompt = _build_research_prompt(metadata)

    try:
        if hasattr(provider, "web_search_completion"):
            raw_result = await provider.web_search_completion(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            verification_status = "web_verified"
        elif hasattr(provider, "chat_completion"):
            raw_result = await provider.chat_completion(
                prompt=prompt,
                system_prompt=(
                    system_prompt
                    + "\nAnda TIDAK punya web search pada provider ini. "
                    "Jawab tetap dalam schema JSON yang sama, tetapi tandai hasil "
                    "sebagai belum terverifikasi web."
                ),
            )
            verification_status = "model_only"
        else:
            return _wrap_result(
                _build_fallback_data(
                    query=query,
                    error="Provider aktif tidak mendukung research.",
                    verification_status="unavailable",
                    metadata=metadata,
                ),
            )
    except Exception as exc:
        return _wrap_result(
            _build_fallback_data(
                query=query,
                error=str(exc),
                verification_status="error",
                metadata=metadata,
            ),
        )

    result = _coerce_result(raw_result, query, metadata, verification_status)
    return _wrap_result(result)


def _build_request_metadata(query: str, now: datetime) -> dict[str, str]:
    """Build request metadata injected into research prompts and output."""
    return {
        "query": query,
        "query_type": _infer_query_type(query),
        "checked_at_local": now.isoformat(timespec="seconds"),
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M:%S"),
        "timezone": now.tzname() or "",
    }


def _infer_query_type(query: str) -> str:
    """Infer a coarse query type to steer search behavior."""
    text = query.lower()
    if any(token in text for token in ("kapan", "tanggal", "jadwal", "schedule", "hari", "today", "hari ini")):
        return "date_schedule"
    if any(token in text for token in ("harga", "price", "kurs", "rate", "market", "saham", "btc", "kripto")):
        return "price_market"
    if any(token in text for token in ("siapa", "presiden", "ceo", "menteri", "kepala", "pemimpin")):
        return "person_role"
    if any(token in text for token in ("rencana", "plan", "itinerary", "liburan", "trip")):
        return "planning"
    if any(token in text for token in ("aturan", "regulasi", "policy", "hukum", "legal")):
        return "policy_regulation"
    return "general_research"


def _build_system_prompt() -> str:
    """Build the system prompt for grounded research."""
    return (
        "Anda adalah private AI research assistant. "
        "Anda wajib memulai dari tanggal saat ini yang diberikan dalam prompt, "
        "lalu melakukan pencarian yang relevan dengan konteks pertanyaan user, "
        "dan merangkum hasil sebagai data terstruktur. "
        "Output HARUS berupa JSON valid tanpa markdown fence dan tanpa teks tambahan. "
        "Jangan mengarang sumber. Hanya masukkan sumber yang benar-benar dipakai. "
        "Jika ada ketidakpastian, konflik sumber, atau batas verifikasi, tulis eksplisit di notes/gaps."
    )


def _build_research_prompt(metadata: dict[str, str]) -> str:
    """Build a detailed research prompt with a strict output schema."""
    return (
        f"Tanggal saat ini: {metadata['current_date']}\n"
        f"Waktu lokal saat ini: {metadata['current_time']} {metadata['timezone']}\n"
        f"Checked at local: {metadata['checked_at_local']}\n"
        f"Tipe query: {metadata['query_type']}\n"
        f"Pertanyaan user: {metadata['query']}\n\n"
        "Instruksi kerja:\n"
        "1. Mulai dari tanggal saat ini sebagai anchor temporal.\n"
        "2. Cari informasi yang paling relevan dengan konteks user.\n"
        "3. Jika query sensitif waktu, prioritaskan sumber terbaru dan tampilkan tanggal spesifik.\n"
        "4. Rangkum dalam bentuk data, bukan paragraf panjang.\n"
        "5. Jika ada konflik sumber, tampilkan ringkas di notes dan gaps.\n\n"
        "Schema JSON yang wajib dipenuhi:\n"
        "{\n"
        '  "checked_at_local": "",\n'
        '  "query": "",\n'
        '  "query_type": "",\n'
        '  "verification_status": "",\n'
        '  "summary": "",\n'
        '  "answer": "",\n'
        '  "confidence": "high|medium|low",\n'
        '  "data_points": [\n'
        '    {"label": "", "value": "", "date": "", "context": ""}\n'
        "  ],\n"
        '  "notes": [""],\n'
        '  "gaps": [""],\n'
        '  "sources": [\n'
        '    {"title": "", "url": "", "publisher": "", "date": ""}\n'
        "  ]\n"
        "}\n"
        "Isi `answer` dengan jawaban singkat paling langsung terhadap pertanyaan user."
    )


def _coerce_result(
    raw_result: str,
    query: str,
    metadata: dict[str, str],
    verification_status: str,
) -> dict[str, Any]:
    """Normalize model output into a stable JSON structure."""
    parsed = _try_parse_json(raw_result)
    if parsed is None:
        parsed = {
            "summary": raw_result.strip() or "Tidak ada output research yang bisa diparse.",
            "answer": raw_result.strip() or "Tidak ada jawaban.",
            "notes": ["Output provider tidak valid JSON; hasil dibungkus ulang oleh handler."],
            "gaps": ["Parser tidak menemukan JSON valid dari provider."],
            "data_points": [],
            "sources": [],
        }

    if not isinstance(parsed, dict):
        parsed = {
            "summary": "Output provider bukan object JSON.",
            "answer": str(parsed),
            "notes": ["Handler menerima JSON valid tetapi bukan object."],
            "gaps": ["Schema hasil tidak sesuai."],
            "data_points": [],
            "sources": [],
        }

    result = {
        "checked_at_local": metadata["checked_at_local"],
        "query": query,
        "query_type": parsed.get("query_type") or metadata["query_type"],
        "verification_status": parsed.get("verification_status") or verification_status,
        "summary": _as_text(parsed.get("summary")),
        "answer": _as_text(parsed.get("answer")),
        "confidence": _normalize_confidence(parsed.get("confidence")),
        "data_points": _normalize_data_points(parsed.get("data_points")),
        "notes": _normalize_string_list(parsed.get("notes")),
        "gaps": _normalize_string_list(parsed.get("gaps")),
        "sources": _normalize_sources(parsed.get("sources")),
    }

    if not result["summary"] and result["answer"]:
        result["summary"] = result["answer"]
    if not result["answer"] and result["summary"]:
        result["answer"] = result["summary"]
    if verification_status != "web_verified" and "Hasil tidak diverifikasi via web search." not in result["notes"]:
        result["notes"].append("Hasil tidak diverifikasi via web search.")
    if not result["sources"]:
        result["gaps"].append("Tidak ada sumber yang berhasil diekstrak.")

    return result


def _try_parse_json(raw_result: str) -> Any:
    """Parse JSON directly or recover the first JSON object from text."""
    text = raw_result.strip()
    if not text:
        return None

    for candidate in (text, _strip_code_fences(text), _extract_json_object(text)):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _strip_code_fences(text: str) -> str:
    """Strip surrounding markdown code fences if present."""
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
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


def _normalize_confidence(value: Any) -> str:
    """Normalize confidence to a stable low|medium|high value."""
    text = _as_text(value).lower()
    if text in {"high", "medium", "low"}:
        return text
    return "medium"


def _normalize_data_points(value: Any) -> list[dict[str, str]]:
    """Normalize result data points into a list of small dictionaries."""
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            label = _as_text(item.get("label"))
            datum = {
                "label": label,
                "value": _as_text(item.get("value")),
                "date": _as_text(item.get("date")),
                "context": _as_text(item.get("context")),
            }
        else:
            datum = {
                "label": "",
                "value": _as_text(item),
                "date": "",
                "context": "",
            }
        if any(datum.values()):
            normalized.append(datum)
    return normalized


def _normalize_sources(value: Any) -> list[dict[str, str]]:
    """Normalize and deduplicate source entries."""
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, dict):
            source = {
                "title": _as_text(item.get("title")),
                "url": _as_text(item.get("url")),
                "publisher": _as_text(item.get("publisher")),
                "date": _as_text(item.get("date")),
            }
        else:
            source = {
                "title": "",
                "url": _as_text(item),
                "publisher": "",
                "date": "",
            }

        key = source["url"] or source["title"]
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(source)
    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    """Normalize strings or lists into a clean list of strings."""
    if isinstance(value, list):
        return [text for item in value if (text := _as_text(item))]
    text = _as_text(value)
    return [text] if text else []


def _as_text(value: Any) -> str:
    """Convert arbitrary values to compact strings."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _build_fallback_data(
    query: str,
    error: str,
    verification_status: str,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a consistent fallback result when research cannot run."""
    metadata = metadata or _build_request_metadata(query, datetime.now().astimezone())
    return {
        "checked_at_local": metadata["checked_at_local"],
        "query": query,
        "query_type": metadata["query_type"],
        "verification_status": verification_status,
        "summary": "Research tidak berhasil dijalankan.",
        "answer": "Research tidak berhasil dijalankan.",
        "confidence": "low",
        "data_points": [],
        "notes": [error],
        "gaps": ["Tidak ada hasil research yang tervalidasi."],
        "sources": [],
    }


def _wrap_result(data: dict[str, Any]) -> dict[str, Any]:
    """Wrap research data into the shared structured-result envelope."""
    return build_result(
        "research_result",
        data,
        source_skill="research",
        default_view="summary",
        status="ok" if data.get("verification_status") not in {"error", "unavailable"} else "degraded",
        verification_status=data.get("verification_status", ""),
    )
