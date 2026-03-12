"""Bootstrap OpenClaw-style workspace skeleton documents from bundled templates."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from otonomassist.core import agent_context
from otonomassist.core.workspace_guard import get_workspace_root


OPENCLAW_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "bootstrap_assets" / "openclaw" / "official"
OPENCLAW_TEMPLATE_FILES = (
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
BOOTSTRAP_SOURCE_URL = "https://github.com/openclaw/openclaw/tree/main/docs/reference/templates"


def ensure_openclaw_workspace_skeleton(
    *,
    force: bool = False,
    only_if_workspace_empty: bool = False,
) -> dict[str, Any]:
    """Seed OpenClaw workspace templates into the workspace root."""
    workspace_root = get_workspace_root()
    workspace_root.mkdir(parents=True, exist_ok=True)
    agent_context.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if only_if_workspace_empty and not _workspace_is_empty_enough(workspace_root):
        return _build_result([], [], skipped="workspace_not_empty")

    written: list[str] = []
    existing: list[str] = []
    for name in OPENCLAW_TEMPLATE_FILES:
        source = OPENCLAW_TEMPLATE_DIR / name
        target = workspace_root / name
        if target.exists() and not force:
            existing.append(name)
            continue
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        written.append(name)

    manifest = {
        "source": "openclaw-official-templates",
        "source_url": BOOTSTRAP_SOURCE_URL,
        "template_count": len(OPENCLAW_TEMPLATE_FILES),
        "written": written,
        "existing": existing,
        "seeded_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace_root),
    }
    _write_manifest(manifest)
    return _build_result(written, existing, skipped="")


def get_openclaw_bootstrap_status() -> dict[str, Any]:
    """Describe bundled template availability and workspace seed status."""
    workspace_root = get_workspace_root()
    manifest_path = agent_context.DATA_DIR / BOOTSTRAP_MANIFEST_FILE
    seeded_files = [
        name for name in OPENCLAW_TEMPLATE_FILES
        if (workspace_root / name).exists()
    ]
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
    return {
        "template_count": len(OPENCLAW_TEMPLATE_FILES),
        "bundled_template_dir": str(OPENCLAW_TEMPLATE_DIR),
        "workspace_seeded_count": len(seeded_files),
        "workspace_seeded_files": seeded_files,
        "manifest_file": str(manifest_path),
        "manifest": manifest,
        "source_url": BOOTSTRAP_SOURCE_URL,
    }


def render_openclaw_bootstrap_status() -> str:
    """Render the OpenClaw bootstrap status for operator inspection."""
    status = get_openclaw_bootstrap_status()
    lines = [
        "OpenClaw Bootstrap",
        "",
        f"- source_url: {status['source_url']}",
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
