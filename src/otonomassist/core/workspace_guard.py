"""Workspace boundary and access guardrails."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_ROOT = Path(
    os.getenv("OTONOMASSIST_WORKSPACE_ROOT", str(PROJECT_ROOT))
).expanduser().resolve()
WORKSPACE_ACCESS = os.getenv("OTONOMASSIST_WORKSPACE_ACCESS", "ro").strip().lower() or "ro"
SKIP_DIRS = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache", "node_modules"}


def get_workspace_root() -> Path:
    """Return the effective workspace root."""
    return WORKSPACE_ROOT


def get_workspace_access() -> str:
    """Return configured workspace access mode."""
    return WORKSPACE_ACCESS


def resolve_workspace_path(path_text: str) -> Path:
    """Resolve a path under the workspace root and block traversal."""
    raw = (path_text or ".").strip()
    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (WORKSPACE_ROOT / candidate).resolve()

    if resolved != WORKSPACE_ROOT and WORKSPACE_ROOT not in resolved.parents:
        raise ValueError("Path di luar workspace tidak diizinkan.")

    return resolved


def ensure_read_allowed(path: Path) -> None:
    """Validate a read target remains inside workspace and is not a symlink escape."""
    resolved = path.resolve()
    if resolved != WORKSPACE_ROOT and WORKSPACE_ROOT not in resolved.parents:
        raise ValueError("Path di luar workspace tidak diizinkan.")


def ensure_write_allowed(path: Path) -> None:
    """Validate write access against workspace policy."""
    ensure_read_allowed(path)
    if WORKSPACE_ACCESS != "rw":
        raise PermissionError(
            f"Workspace saat ini berada pada mode '{WORKSPACE_ACCESS}', write tidak diizinkan."
        )


def ensure_internal_state_write_allowed(path: Path) -> None:
    """Allow writes for internal state under .otonomassist regardless of workspace mode."""
    resolved = path.resolve()
    internal_root = (WORKSPACE_ROOT / ".otonomassist").resolve()
    if resolved == internal_root or internal_root in resolved.parents:
        return
    ensure_write_allowed(path)


def should_skip_path(path: Path, relative_to: Path) -> bool:
    """Check whether a path should be skipped during traversal."""
    try:
        relative = path.relative_to(relative_to)
    except ValueError:
        return True

    if any(part in SKIP_DIRS for part in relative.parts):
        return True
    if path.is_symlink():
        return True
    try:
        resolved = path.resolve()
    except OSError:
        return True
    return resolved != WORKSPACE_ROOT and WORKSPACE_ROOT not in resolved.parents
