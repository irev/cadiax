"""Cross-platform service runtime capability reporting."""

from __future__ import annotations

import os


def get_service_runtime_info() -> dict[str, object]:
    """Describe the current service-runtime capability for this OS."""
    if os.name == "nt":
        return {
            "backend": "windows-runtime",
            "supervisor_ready": False,
            "recommended_mode": "foreground-cli",
            "status": "warning",
            "detail": (
                "Service runtime lintas-OS sudah dipersiapkan, "
                "tetapi supervisor Windows belum diimplementasikan."
            ),
        }

    return {
        "backend": "posix-runtime",
        "supervisor_ready": False,
        "recommended_mode": "foreground-cli",
        "status": "warning",
        "detail": (
            "Service runtime lintas-OS sudah dipersiapkan, "
            "tetapi supervisor daemon/systemd belum diimplementasikan."
        ),
    }
