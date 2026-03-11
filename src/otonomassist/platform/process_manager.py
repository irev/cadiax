"""Cross-platform process manager capability reporting."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Sequence


def get_process_manager_info() -> dict[str, str]:
    """Describe the current process-management strategy for this OS."""
    if os.name == "nt":
        return {
            "backend": "windows-process",
            "service_strategy": "task-scheduler-or-service-wrapper",
            "status": "warning",
            "detail": (
                "Process manager dasar portable tersedia. "
                "Windows service wrapper belum diimplementasikan penuh."
            ),
        }

    return {
        "backend": "posix-process",
        "service_strategy": "foreground-process-or-systemd-wrapper",
        "status": "warning",
        "detail": (
            "Process manager dasar portable tersedia. "
            "Daemon/systemd integration belum diimplementasikan penuh."
        ),
    }


def run_process(
    command: Sequence[str],
    cwd: str | Path | None = None,
    timeout_seconds: float = 120.0,
) -> dict[str, object]:
    """Run a local process with a portable subprocess wrapper."""
    completed = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        shell=False,
        check=False,
    )
    return {
        "command": list(command),
        "cwd": str(cwd) if cwd is not None else None,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "ok": completed.returncode == 0,
    }
