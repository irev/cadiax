"""Toolchain capability reporting for external skill ecosystems."""

from __future__ import annotations

import shutil


DEFAULT_TOOLCHAINS = {
    "git": "Git-based skill install/update",
    "python": "Python runtime and script execution",
    "pip": "Python package install flow",
    "node": "Node.js runtime for npm-based skills",
    "npm": "NPM package install flow",
}


def get_toolchain_info() -> dict[str, object]:
    """Describe availability of common external toolchains."""
    tools: dict[str, dict[str, object]] = {}
    statuses: list[str] = []
    for name, purpose in DEFAULT_TOOLCHAINS.items():
        resolved = shutil.which(name)
        available = bool(resolved)
        tools[name] = {
            "available": available,
            "path": resolved or "",
            "purpose": purpose,
        }
        statuses.append("healthy" if available else "warning")

    overall = "healthy" if all(item == "healthy" for item in statuses) else "warning"
    return {
        "status": overall,
        "tools": tools,
    }
