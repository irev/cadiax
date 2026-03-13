"""Bootstrap workspace skeleton documents from bundled foundation templates."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

from otonomassist.core import agent_context
from otonomassist.core.execution_history import append_execution_event, new_trace_id
from otonomassist.core.workspace_guard import get_workspace_root


FOUNDATION_TEMPLATE_FILES = (
    "AGENTS.dev.md",
    "AGENTS.md",
    "BOOT.md",
    "BOOTSTRAP.md",
    "HEARTBEAT.md",
    "IDENTITY.dev.md",
    "IDENTITY.md",
    "SOUL.dev.md",
    "SOUL.md",
    "TOOLS.dev.md",
    "TOOLS.md",
    "USER.dev.md",
    "USER.md",
)
BOOTSTRAP_MANIFEST_FILE = "bootstrap_manifest.json"


def _foundation_template_dir() -> Path:
    """Return the bundled template directory from installed package data."""
    return Path(resources.files("otonomassist")).joinpath(
        "bootstrap_assets",
        "foundation",
        "official",
    )


def ensure_workspace_skeleton(
    *,
    force: bool = False,
    only_if_workspace_empty: bool = False,
) -> dict[str, Any]:
    """Seed bundled foundation templates into the workspace root."""
    workspace_root = get_workspace_root()
    workspace_root.mkdir(parents=True, exist_ok=True)
    agent_context.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if only_if_workspace_empty and not _workspace_is_empty_enough(workspace_root):
        result = _build_result([], [], skipped="workspace_not_empty")
        _record_bootstrap_event(result, workspace_root=workspace_root, force=force, only_if_workspace_empty=only_if_workspace_empty)
        return result

    written: list[str] = []
    existing: list[str] = []
    template_dir = _foundation_template_dir()
    for name in FOUNDATION_TEMPLATE_FILES:
        source = template_dir / name
        target = workspace_root / name
        if target.exists() and not force:
            existing.append(name)
            continue
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        written.append(name)

    manifest = {
        "source": "official-foundation-templates",
        "template_count": len(FOUNDATION_TEMPLATE_FILES),
        "written": written,
        "existing": existing,
        "seeded_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace_root),
    }
    _write_manifest(manifest)
    result = _build_result(written, existing, skipped="")
    _record_bootstrap_event(result, workspace_root=workspace_root, force=force, only_if_workspace_empty=only_if_workspace_empty)
    return result


def get_workspace_bootstrap_status() -> dict[str, Any]:
    """Describe bundled template availability and workspace seed status."""
    workspace_root = get_workspace_root()
    manifest_path = agent_context.DATA_DIR / BOOTSTRAP_MANIFEST_FILE
    seeded_files = [
        name for name in FOUNDATION_TEMPLATE_FILES
        if (workspace_root / name).exists()
    ]
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
    return {
        "template_count": len(FOUNDATION_TEMPLATE_FILES),
        "bundled_template_dir": str(_foundation_template_dir()),
        "workspace_seeded_count": len(seeded_files),
        "workspace_seeded_files": seeded_files,
        "manifest_file": str(manifest_path),
        "manifest": manifest,
    }


def render_workspace_bootstrap_status() -> str:
    """Render the workspace bootstrap status for operator inspection."""
    status = get_workspace_bootstrap_status()
    lines = [
        "Workspace Bootstrap",
        "",
        f"- bundled_template_dir: {status['bundled_template_dir']}",
        f"- template_count: {status['template_count']}",
        f"- workspace_seeded_count: {status['workspace_seeded_count']}",
        f"- manifest_file: {status['manifest_file']}",
    ]
    for name in status["workspace_seeded_files"]:
        lines.append(f"- seeded: {name}")
    return "\n".join(lines)


def _write_manifest(payload: dict[str, Any]) -> None:
    manifest_path = agent_context.DATA_DIR / BOOTSTRAP_MANIFEST_FILE
    temp_path = manifest_path.with_name(f"{manifest_path.name}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(manifest_path)


def _workspace_is_empty_enough(workspace_root: Path) -> bool:
    existing = [item for item in workspace_root.iterdir() if item.name not in {".gitkeep"}]
    return len(existing) == 0


def _build_result(written: list[str], existing: list[str], *, skipped: str) -> dict[str, Any]:
    return {
        "written": written,
        "written_count": len(written),
        "existing": existing,
        "existing_count": len(existing),
        "skipped": skipped,
    }


def _record_bootstrap_event(
    result: dict[str, Any],
    *,
    workspace_root: Path,
    force: bool,
    only_if_workspace_empty: bool,
) -> None:
    append_execution_event(
        "workspace_bootstrap_completed",
        trace_id=new_trace_id(),
        status="skipped" if result.get("skipped") else "ok",
        source="bootstrap",
        command="bootstrap foundation",
        data={
            "workspace_root": str(workspace_root),
            "force": bool(force),
            "only_if_workspace_empty": bool(only_if_workspace_empty),
            "written_count": int(result.get("written_count", 0) or 0),
            "existing_count": int(result.get("existing_count", 0) or 0),
            "skipped": str(result.get("skipped") or ""),
        },
    )
