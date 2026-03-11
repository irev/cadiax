"""External asset layout, manifest parsing, and audit registry for workspace-managed extensions."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
import re

import otonomassist.core.agent_context as agent_context
from otonomassist.core.event_bus import publish_event
from otonomassist.platform import get_toolchain_info
import otonomassist.core.workspace_guard as workspace_guard


KNOWN_EXTERNAL_CAPABILITIES = {
    "workspace_read",
    "workspace_write",
    "network",
    "subprocess",
    "memory_write",
    "planner_write",
    "profile_write",
}


def get_external_registry_file() -> Path:
    return agent_context.DATA_DIR / "external_assets.json"


def get_external_skill_trust_policy() -> str:
    """Return effective trust policy for workspace-managed external skills."""
    policy = os.getenv("OTONOMASSIST_EXTERNAL_SKILL_POLICY", "approval-required").strip().lower()
    if policy in {"allow-all", "approval-required"}:
        return policy
    return "approval-required"


def get_allowed_external_capabilities() -> set[str]:
    """Return capabilities currently allowed for external skills."""
    raw = os.getenv("OTONOMASSIST_EXTERNAL_CAPABILITY_ALLOW", "workspace_read").strip().lower()
    if raw in {"*", "all"}:
        return set(KNOWN_EXTERNAL_CAPABILITIES)
    return {
        item.strip()
        for item in raw.split(",")
        if item.strip()
    }


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


def get_external_skill_metadata_name(asset_root: Path) -> str:
    """Read skill name from SKILL.md metadata when manifest is absent."""
    skill_md = asset_root / "SKILL.md"
    if not skill_md.exists():
        return ""
    pattern = re.compile(r"^- name:\s*(.+)$", re.MULTILINE)
    match = pattern.search(skill_md.read_text(encoding="utf-8"))
    if not match:
        return ""
    return str(match.group(1)).strip()


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


def evaluate_external_asset_capabilities(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate declared capabilities for one external asset."""
    manifest = manifest or {}
    declared = [
        str(item).strip().lower()
        for item in manifest.get("capabilities", [])
        if str(item).strip()
    ]
    unknown = [name for name in declared if name not in KNOWN_EXTERNAL_CAPABILITIES]
    allowed = get_allowed_external_capabilities()
    disallowed = [name for name in declared if name in KNOWN_EXTERNAL_CAPABILITIES and name not in allowed]
    if not declared:
        status = "missing"
    elif unknown:
        status = "unknown"
    elif disallowed:
        status = "blocked"
    else:
        status = "declared"
    return {
        "status": status,
        "declared_capabilities": declared,
        "unknown_capabilities": unknown,
        "disallowed_capabilities": disallowed,
        "allowed_capabilities": sorted(allowed),
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
    publish_event(
        "external.asset",
        event_type=f"external_asset_{action}",
        source=asset_type,
        data={
            "name": name,
            "asset_type": asset_type,
            "target_path": str(Path(target_path)),
            "actor": actor,
            "result": result,
            "detail": detail,
        },
    )
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
        "execution_mode": _get_execution_mode(asset_type, normalized_target),
        "status": status,
        "installed_by": installed_by,
        "version": version,
        "requirements": requirements or [],
        "compatibility": compatibility or _build_default_compatibility_snapshot(),
        "compatibility_status": compatibility_status or "ready",
        "capability_status": "missing",
        "declared_capabilities": [],
        "approval_state": "approved" if get_external_skill_trust_policy() == "allow-all" else "pending",
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
            "execution_mode": existing.get("execution_mode"),
            "installed_by": existing.get("installed_by"),
            "version": existing.get("version"),
            "requirements": existing.get("requirements", []),
            "compatibility_status": existing.get("compatibility_status"),
            "capability_status": existing.get("capability_status", "missing"),
            "declared_capabilities": existing.get("declared_capabilities", []),
            "approval_state": existing.get("approval_state", "pending"),
            "notes": existing.get("notes", []),
        }
        existing.update(payload)
        existing.setdefault("installed_at", now)
        existing.setdefault("approval_state", "approved" if get_external_skill_trust_policy() == "allow-all" else "pending")
        record = existing
        changed = previous != {
            "manager": record.get("manager"),
            "source": record.get("source"),
            "status": record.get("status"),
            "execution_mode": record.get("execution_mode"),
            "installed_by": record.get("installed_by"),
            "version": record.get("version"),
            "requirements": record.get("requirements", []),
            "compatibility_status": record.get("compatibility_status"),
            "capability_status": record.get("capability_status", "missing"),
            "declared_capabilities": record.get("declared_capabilities", []),
            "approval_state": record.get("approval_state", "pending"),
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
        capabilities = evaluate_external_asset_capabilities(manifest)
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
        if capabilities["status"] == "missing":
            notes.append("Capabilities belum dideklarasikan di asset.json.")
        if capabilities["unknown_capabilities"]:
            notes.append("Unknown capabilities: " + ", ".join(capabilities["unknown_capabilities"]))
        if capabilities["disallowed_capabilities"]:
            notes.append("Disallowed capabilities: " + ", ".join(capabilities["disallowed_capabilities"]))
        discovered.append(
            record_external_asset(
                name=str(manifest.get("name") or get_external_skill_metadata_name(entry) or entry.name),
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
        discovered[-1]["capability_status"] = capabilities["status"]
        discovered[-1]["declared_capabilities"] = capabilities["declared_capabilities"]
        state = load_external_asset_registry()
        asset = next(
            (
                item for item in state.get("assets", [])
                if item.get("name") == discovered[-1]["name"]
                and item.get("target_path") == discovered[-1]["target_path"]
            ),
            None,
        )
        if asset is not None:
            asset["capability_status"] = capabilities["status"]
            asset["declared_capabilities"] = capabilities["declared_capabilities"]
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_external_asset_registry(state)
        if discovered[-1].get("_created") or discovered[-1].get("_changed"):
            append_external_asset_event(
                action="install" if discovered[-1].get("_created") else "update",
                name=str(manifest.get("name") or get_external_skill_metadata_name(entry) or entry.name),
                asset_type="skill",
                target_path=str(entry),
                actor=installed_by,
                source=str(manifest.get("source") or skill_md),
                detail=f"compatibility={compatibility['status']}; capabilities={capabilities['status']}",
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


def set_external_asset_approval(name: str, approval_state: str, actor: str = "system") -> dict[str, Any]:
    """Approve or reject one external asset by name."""
    if approval_state not in {"approved", "rejected", "pending"}:
        raise ValueError("approval_state harus approved, rejected, atau pending.")
    state = load_external_asset_registry()
    asset = next((item for item in state.get("assets", []) if item.get("name") == name), None)
    if not asset:
        raise ValueError(f"Asset eksternal '{name}' tidak ditemukan.")
    if approval_state == "approved" and asset.get("capability_status") != "declared":
        raise ValueError(
            f"Asset eksternal '{name}' belum bisa di-approve karena capability declaration belum valid."
        )
    asset["approval_state"] = approval_state
    asset["updated_at"] = datetime.now(timezone.utc).isoformat()
    state["updated_at"] = asset["updated_at"]
    save_external_asset_registry(state)
    append_external_asset_event(
        action=f"approval-{approval_state}",
        name=name,
        asset_type=str(asset.get("type") or "skill"),
        target_path=str(asset.get("target_path") or ""),
        actor=actor,
        source=str(asset.get("source") or ""),
        detail=f"policy={get_external_skill_trust_policy()}",
    )
    return _strip_internal_flags(asset)


def is_external_skill_approved(skill_dir: Path) -> bool:
    """Check whether an external skill directory is approved under current policy."""
    if get_external_skill_trust_policy() == "allow-all":
        return True
    state = load_external_asset_registry()
    normalized_target = str(Path(skill_dir).resolve())
    for asset in state.get("assets", []):
        if asset.get("type") != "skill":
            continue
        if str(Path(str(asset.get("target_path") or "")).resolve()) == normalized_target:
            return asset.get("approval_state", "pending") == "approved"
    return False


def build_external_asset_audit_summary() -> dict[str, Any]:
    """Build a compact summary for external assets and layout."""
    sync_external_skill_inventory()
    assets = list_external_assets()
    by_type: dict[str, int] = {}
    incompatible_count = 0
    unapproved_count = 0
    undeclared_capability_count = 0
    blocked_capability_count = 0
    isolated_skill_count = 0
    for item in assets:
        by_type[item.get("type", "unknown")] = by_type.get(item.get("type", "unknown"), 0) + 1
        if item.get("compatibility_status") != "ready":
            incompatible_count += 1
        if item.get("approval_state") != "approved":
            unapproved_count += 1
        if item.get("capability_status") != "declared":
            undeclared_capability_count += 1
        if item.get("capability_status") == "blocked":
            blocked_capability_count += 1
        if item.get("type") == "skill" and item.get("execution_mode") == "subprocess-isolated":
            isolated_skill_count += 1
    registry = load_external_asset_registry()
    return {
        "layout": get_external_asset_layout(),
        "asset_count": len(assets),
        "event_count": len(registry.get("events", [])),
        "incompatible_count": incompatible_count,
        "unapproved_count": unapproved_count,
        "undeclared_capability_count": undeclared_capability_count,
        "blocked_capability_count": blocked_capability_count,
        "isolated_skill_count": isolated_skill_count,
        "trust_policy": get_external_skill_trust_policy(),
        "allowed_capabilities": sorted(get_allowed_external_capabilities()),
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
        f"- unapproved_count: {summary['unapproved_count']}",
        f"- undeclared_capability_count: {summary['undeclared_capability_count']}",
        f"- blocked_capability_count: {summary['blocked_capability_count']}",
        f"- isolated_skill_count: {summary['isolated_skill_count']}",
        f"- trust_policy: {summary['trust_policy']}",
        f"- allowed_capabilities: {', '.join(summary['allowed_capabilities']) or '-'}",
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
            f"[manager={item.get('manager')}, status={item.get('status')}, compatibility={item.get('compatibility_status')}, approval={item.get('approval_state', 'pending')}, execution={item.get('execution_mode', 'unknown')}]"
        )
        lines.append(f"  target: {item.get('target_path')}")
        lines.append(f"  source: {item.get('source')}")
        lines.append(f"  installed_by: {item.get('installed_by')}")
        lines.append(f"  installed_at: {item.get('installed_at')}")
        if item.get("version"):
            lines.append(f"  version: {item.get('version')}")
        if item.get("requirements"):
            lines.append("  requirements: " + ", ".join(item.get("requirements", [])))
        if item.get("declared_capabilities"):
            lines.append("  capabilities: " + ", ".join(item.get("declared_capabilities", [])))
        lines.append(f"  capability_status: {item.get('capability_status', 'missing')}")
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


def _get_execution_mode(asset_type: str, target_path: str) -> str:
    if asset_type != "skill":
        return "host-managed"
    try:
        external_root = get_external_skills_dir().resolve()
        resolved_target = Path(target_path).resolve()
    except OSError:
        return "subprocess-isolated"
    if resolved_target == external_root or external_root in resolved_target.parents:
        return "subprocess-isolated"
    return "in-process"


def _strip_internal_flags(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if not key.startswith("_")}
