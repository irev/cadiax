"""Agent scope registry derived from workspace documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from cadiax.core.agent_context import ensure_agent_storage
from cadiax.core.workspace_guard import get_workspace_root


class AgentScopeService:
    """Resolve declared agent or domain scopes from the workspace manifest."""

    SECTION_PATTERN = re.compile(r"^##\s+Agent Scopes\s*$", re.IGNORECASE | re.MULTILINE)
    BULLET_PATTERN = re.compile(
        r"^-\s*(?P<name>[a-z0-9][a-z0-9_-]*)\s*:\s*(?P<description>.*?)(?:\s*\|\s*roles:\s*(?P<roles>.+))?$",
        re.IGNORECASE,
    )

    def __init__(self, document_path: Path | None = None) -> None:
        self.document_path = document_path or (get_workspace_root() / "AGENTS.md")

    def list_scopes(self) -> list[dict[str, Any]]:
        """Return declared scopes from AGENTS.md, or a default scope when absent."""
        ensure_agent_storage()
        if not self.document_path.exists():
            return [self._default_scope()]
        content = self.document_path.read_text(encoding="utf-8", errors="replace")
        section = self._extract_scope_section(content)
        scopes: list[dict[str, Any]] = []
        for raw_line in section.splitlines():
            line = raw_line.strip()
            if not line.startswith("-"):
                continue
            match = self.BULLET_PATTERN.match(line)
            if not match:
                continue
            role_text = str(match.group("roles") or "").strip()
            scopes.append(
                {
                    "scope": match.group("name").strip().lower(),
                    "description": match.group("description").strip(),
                    "allowed_roles": _parse_roles(role_text),
                }
            )
        if not scopes:
            scopes.append(self._default_scope())
        return scopes

    def get_scope(self, scope: str) -> dict[str, Any]:
        """Return one declared scope or an undeclared placeholder."""
        normalized = _normalize_scope(scope)
        for item in self.list_scopes():
            if item["scope"] == normalized:
                return item
        return {
            "scope": normalized,
            "description": "",
            "allowed_roles": [],
            "declared": False,
        }

    def get_snapshot(self) -> dict[str, Any]:
        """Return machine-readable scope registry diagnostics."""
        scopes = []
        for item in self.list_scopes():
            scopes.append({**item, "declared": True})
        return {
            "scope_count": len(scopes),
            "scopes": scopes,
            "document_path": str(self.document_path),
        }

    def render_report(self) -> str:
        """Render a human-readable scope registry report."""
        snapshot = self.get_snapshot()
        lines = [
            "Agent Scopes",
            "",
            f"- scope_count: {snapshot['scope_count']}",
            f"- document_path: {snapshot['document_path']}",
        ]
        for item in snapshot["scopes"]:
            lines.append(
                f"- {item['scope']}: {item['description'] or '-'} "
                f"(roles: {', '.join(item['allowed_roles']) or '-'})"
            )
        return "\n".join(lines)

    def _extract_scope_section(self, content: str) -> str:
        match = self.SECTION_PATTERN.search(content)
        if not match:
            return ""
        remainder = content[match.end() :].lstrip("\n")
        lines: list[str] = []
        for line in remainder.splitlines():
            if line.startswith("## "):
                break
            lines.append(line)
        return "\n".join(lines)

    def _default_scope(self) -> dict[str, Any]:
        return {
            "scope": "default",
            "description": "Runtime utama dan percakapan umum.",
            "allowed_roles": [],
        }


def _parse_roles(value: str) -> list[str]:
    return sorted(
        {
            item_text
            for item_text in (item.strip().lower() for item in value.split(","))
            if item_text
        }
    )


def _normalize_scope(value: str) -> str:
    normalized = str(value or "").strip().lower().replace(" ", "-")
    return normalized or "default"
