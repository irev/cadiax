"""External asset layout, manifest parsing, and audit registry for workspace-managed extensions."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import otonomassist.core.agent_context as agent_context
from otonomassist.platform import get_toolchain_info
import otonomassist.core.workspace_guard as workspace_guard


def get_external_registry_file() -> Path:
    return agent_context.DATA_DIR / "external_assets.json"


def get_external_skills_dir() -> Path:
    return workspace_guard.WORKSPACE_ROOT / "skills-external"


def get_external_tools_dir() -> Path:
    return workspace_guard.WORKSPACE_ROOT / "tools"


def get_external_packages_dir() -> Path:
    return workspace_guard.WORKSPACE_ROOT / "packages"


def ensure_external_asset_layout() -> None:
    """Ensure default directories for workspace-managed external assets exist."""
    workspace_guard.ensure_workspace_root_exists()
    for path in (get_external_skills_dir(), get_external_tools_dir(), get_external_packages_dir()):
        path.mkdir(parents=True, exist_ok=True)
    registry_file = get_external_registry_file()
    if not registry_file.exists():
        workspace_guard.ensure_internal_state_write_allowed(registry_file)
        registry_file.write_text(
            json.dumps({"assets": [], "events": [], "updated_at": None}, indent=2),
            encoding="utf-8",
        )


def get_external_asset_layout() -> dict[str, str]:
    """Return canonical directories for external assets."""
    ensure_external_asset_layout()
    return {
        "workspace_root": str(workspace_guard.WORKSPACE_ROOT),
        "skills_dir": str(get_external_skills_dir()),
        "tools_dir": str(get_external_tools_dir()),
        "packages_dir": str(get_external_packages_dir()),
        "registry_file": str(get_external_registry_file()),
    }


def load_external_asset_registry() -> dict[str, Any]:
    """Load the external asset registry state."""
    ensure_external_asset_layout()
    raw = get_external_registry_file().read_text(encoding="utf-8")
    if not raw.strip():
        return {"assets": [], "events": [], "updated_at": None}
    state = json.loads(raw)
    state.setdefault("assets", [])
    state.setdefault("events", [])
    state.setdefault("updated_at", None)
    return state


def save_external_asset_registry(state: dict[str, Any]) -> None:
    """Persist the external asset registry state."""
    ensure_external_asset_layout()
    registry_file = get_external_registry_file()
    workspace_guard.ensure_internal_state_write_allowed(registry_file)
    temp_path = registry_file.with_name(f"{registry_file.name}.tmp")
    temp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp_path.replace(registry_file)


def get_external_asset_manifest(asset_root: Path) -> dict[str, Any]:
    """Load optional external asset manifest from asset.json."""
    manifest_file = asset_root / "asset.json"
    if not manifest_file.exists():
        return {}
    try:
        payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "manifest_file": str(manifest_file),
            "manifest_error": "invalid_json",
        }
    payload["manifest_file"] = str(manifest_file)
    return payload


def evaluate_external_asset_compatibility(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate an asset manifest against current OS and available toolchains."""
    manifest = manifest or {}
    current_platform = _get_platform_name()
    required_platforms = [
        str(item).strip().lower()
        for item in manifest.get("platforms", [])
        if str(item).strip()
    ]
    required_toolchains = [
        str(item).strip().lower()
        for item in manifest.get("requires", [])
        if str(item).strip()
    ]

    toolchains = get_toolchain_info()
    missing_toolchains = [
        name for name in required_toolchains
        if not bool(toolchains["tools"].get(name, {}).get("available"))
    ]

    platform_supported = not required_platforms or current_platform in required_platforms
    if not platform_supported:
        status = "degraded"
    elif missing_toolchains:
        status = "degraded"
    else:
        status = "ready"

    return {
        "status": status,
        "platform": current_platform,
        "platform_supported": platform_supported,
        "required_platforms": required_platforms,
        "required_toolchains": required_toolchains,
        "missing_toolchains": missing_toolchains,
    }


def append_external_asset_event(
    *,
    action: str,
    name: str,
    asset_type: str,
    target_path: str,
    actor: str,
    source: str = "",
    result: str = "ok",
    detail: str = "",
) -> dict[str, Any]:
    """Append an auditable asset event to the registry."""
    state = load_external_asset_registry()
    events = state.setdefault("events", [])
    event = {
        "id": len(events) + 1,
        "action": action,
        "name": name,
        "type": asset_type,
        "target_path": str(Path(target_path)),
        "actor": actor,
        "source": source,
        "result": result,
        "detail": detail,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    events.append(event)
    state["updated_at"] = event["created_at"]
    save_external_asset_registry(state)
    return event


def record_external_asset(
    *,
    name: str,
    asset_type: str,
    manager: str,
    source: str,
    target_path: str,
    status: str = "installed",
    installed_by: str = "system",
    version: str = "",
    requirements: list[str] | None = None,
    compatibility: dict[str, Any] | None = None,
    notes: list[str] | None = None,
    compatibility_status: str = "",
) -> dict[str, Any]:
    """Create or update an audited external asset entry."""
    state = load_external_asset_registry()
    assets = state.setdefault("assets", [])
    normalized_target = str(Path(target_path))
    existing = next(
        (
            item
            for item in assets
            if item.get("name") == name
            and item.get("type") == asset_type
            and item.get("target_path") == normalized_target
        ),
        None,
    )
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "name": name,
        "type": asset_type,
        "manager": manager,
        "source": source,
        "target_path": normalized_target,
        "status": status,
        "installed_by": installed_by,
        "version": version,
        "requirements": requirements or [],
        "compatibility": compatibility or _build_default_compatibility_snapshot(),
        "compatibility_status": compatibility_status or "ready",
        "notes": notes or [],
        "updated_at": now,
    }
    changed = True
    created = False
    if existing:
        previous = {
            "manager": existing.get("manager"),
            "source": existing.get("source"),
            "status": existing.get("status"),
            "installed_by": existing.get("installed_by"),
            "version": existing.get("version"),
            "requirements": existing.get("requirements", []),
            "compatibility_status": existing.get("compatibility_status"),
            "notes": existing.get("notes", []),
        }
        existing.update(payload)
        existing.setdefault("installed_at", now)
        record = existing
        changed = previous != {
            "manager": record.get("manager"),
            "source": record.get("source"),
            "status": record.get("status"),
            "installed_by": record.get("installed_by"),
            "version": record.get("version"),
            "requirements": record.get("requirements", []),
            "compatibility_status": record.get("compatibility_status"),
            "notes": record.get("notes", []),
        }
    else:
        payload["installed_at"] = now
        payload["id"] = len(assets) + 1
        assets.append(payload)
        record = payload
        created = True
    state["updated_at"] = now
    save_external_asset_registry(state)
    record["_changed"] = changed
    record["_created"] = created
    return record


def sync_external_skill_inventory(installed_by: str = "system-sync") -> dict[str, Any]:
    """Scan workspace external skill directories and sync them into the audit registry."""
    ensure_external_asset_layout()
    discovered: list[dict[str, Any]] = []
    for entry in sorted(get_external_skills_dir().iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue
        manifest = get_external_asset_manifest(entry)
        compatibility = evaluate_external_asset_compatibility(manifest)
        requirements = [
            str(item).strip()
            for item in manifest.get("requires", [])
            if str(item).strip()
        ]
        notes = ["Discovered from workspace/skills-external scan."]
        if manifest.get("manifest_error"):
            notes.append("asset.json tidak valid dan di-skip sebagian.")
        if compatibility["missing_toolchains"]:
            notes.append(
                "Missing toolchains: " + ", ".join(compatibility["missing_toolchains"])
            )
        if not compatibility["platform_supported"]:
            notes.append(
                "Platform unsupported for this asset: "
                + ", ".join(compatibility["required_platforms"])
            )
        discovered.append(
            record_external_asset(
                name=str(manifest.get("name") or entry.name),
                asset_type="skill",
                manager=str(manifest.get("manager") or "workspace-local"),
                source=str(manifest.get("source") or skill_md),
                target_path=str(entry),
                status=str(manifest.get("status") or "installed"),
                installed_by=installed_by,
                version=str(manifest.get("version") or ""),
                requirements=requirements,
                compatibility=compatibility,
                compatibility_status=str(compatibility["status"]),
                notes=notes,
            )
        )
        if discovered[-1].get("_created") or discovered[-1].get("_changed"):
            append_external_asset_event(
                action="install" if discovered[-1].get("_created") else "update",
                name=str(manifest.get("name") or entry.name),
                asset_type="skill",
                target_path=str(entry),
                actor=installed_by,
                source=str(manifest.get("source") or skill_md),
                detail=f"compatibility={compatibility['status']}",
            )
    return {
        "discovered_count": len(discovered),
        "assets": [_strip_internal_flags(item) for item in discovered],
    }


def list_external_assets() -> list[dict[str, Any]]:
    """Return all audited external assets."""
    state = load_external_asset_registry()
    assets = state.get("assets", [])
    return sorted(
        [_strip_internal_flags(item) for item in assets],
        key=lambda item: (item.get("type", ""), item.get("name", "")),
    )


def build_external_asset_audit_summary() -> dict[str, Any]:
    """Build a compact summary for external assets and layout."""
    sync_external_skill_inventory()
    assets = list_external_assets()
    by_type: dict[str, int] = {}
    incompatible_count = 0
    for item in assets:
        by_type[item.get("type", "unknown")] = by_type.get(item.get("type", "unknown"), 0) + 1
        if item.get("compatibility_status") != "ready":
            incompatible_count += 1
    registry = load_external_asset_registry()
    return {
        "layout": get_external_asset_layout(),
        "asset_count": len(assets),
        "event_count": len(registry.get("events", [])),
        "incompatible_count": incompatible_count,
        "by_type": by_type,
        "assets": assets,
    }


def render_external_asset_audit() -> str:
    """Render a human-readable audit report for workspace-managed external assets."""
    summary = build_external_asset_audit_summary()
    lines = [
        "External Asset Audit",
        "",
        "[Layout]",
        f"- workspace_root: {summary['layout']['workspace_root']}",
        f"- skills_dir: {summary['layout']['skills_dir']}",
        f"- tools_dir: {summary['layout']['tools_dir']}",
        f"- packages_dir: {summary['layout']['packages_dir']}",
        f"- registry_file: {summary['layout']['registry_file']}",
        "",
        "[Summary]",
        f"- asset_count: {summary['asset_count']}",
        f"- event_count: {summary['event_count']}",
        f"- incompatible_count: {summary['incompatible_count']}",
    ]
    for key, value in sorted(summary["by_type"].items()):
        lines.append(f"- {key}: {value}")

    lines.extend(["", "[Assets]"])
    if not summary["assets"]:
        lines.append("- belum ada asset eksternal yang teraudit")
        return "\n".join(lines)

    for item in summary["assets"]:
        lines.append(
            f"- #{item.get('id')} {item.get('type')} {item.get('name')} "
            f"[manager={item.get('manager')}, status={item.get('status')}, compatibility={item.get('compatibility_status')}]"
        )
        lines.append(f"  target: {item.get('target_path')}")
        lines.append(f"  source: {item.get('source')}")
        lines.append(f"  installed_by: {item.get('installed_by')}")
        lines.append(f"  installed_at: {item.get('installed_at')}")
        if item.get("version"):
            lines.append(f"  version: {item.get('version')}")
        if item.get("requirements"):
            lines.append("  requirements: " + ", ".join(item.get("requirements", [])))
        compatibility = item.get("compatibility") or {}
        if compatibility.get("missing_toolchains"):
            lines.append("  missing_toolchains: " + ", ".join(compatibility.get("missing_toolchains", [])))
        if compatibility.get("required_platforms"):
            lines.append("  required_platforms: " + ", ".join(compatibility.get("required_platforms", [])))
    return "\n".join(lines)


def _build_default_compatibility_snapshot() -> dict[str, Any]:
    toolchains = get_toolchain_info()
    return {
        "os": os.name,
        "toolchains": {
            name: {"available": meta["available"], "path": meta["path"]}
            for name, meta in toolchains["tools"].items()
        },
    }


def _get_platform_name() -> str:
    if os.name == "nt":
        return "windows"
    if os.name == "posix":
        return "linux"
    return os.name


def _strip_internal_flags(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if not key.startswith("_")}
