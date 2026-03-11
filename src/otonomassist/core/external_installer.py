"""Installer workflow for workspace-managed external skills."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from otonomassist.core.external_assets import (
    append_external_asset_event,
    evaluate_external_asset_compatibility,
    get_external_asset_manifest,
    get_external_skills_dir,
    sync_external_skill_inventory,
)
from otonomassist.platform import get_toolchain_info, run_process


GIT_PREFIXES = ("http://", "https://", "ssh://", "git@", "git+https://", "git+ssh://")


def install_external_skill(
    source: str,
    *,
    name: str = "",
    actor: str = "system",
) -> dict[str, Any]:
    """Install an external skill into workspace/skills-external."""
    source = (source or "").strip()
    if not source:
        raise ValueError("Source skill eksternal tidak boleh kosong.")

    skills_dir = get_external_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)
    target_name = _normalize_asset_name(name or _derive_asset_name(source))
    if not target_name:
        raise ValueError("Nama skill eksternal tidak dapat ditentukan dari source.")

    target_dir = skills_dir / target_name
    try:
        if target_dir.exists():
            raise FileExistsError(
                f"Target skill eksternal sudah ada: {target_dir}. "
                "Gunakan nama lain atau hapus direktori lama terlebih dahulu."
            )

        source_kind = _detect_source_kind(source)
        if source_kind == "local":
            _install_from_local_path(Path(source), target_dir)
        else:
            _install_from_git(source, target_dir)

        skill_md = target_dir / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(
                f"SKILL.md tidak ditemukan setelah install di {target_dir}"
            )

        manifest = get_external_asset_manifest(target_dir)
        compatibility = evaluate_external_asset_compatibility(manifest)
        sync_result = sync_external_skill_inventory(installed_by=actor)
        append_external_asset_event(
            action="install-request",
            name=str(manifest.get("name") or target_name),
            asset_type="skill",
            target_path=str(target_dir),
            actor=actor,
            source=source,
            detail=(
                f"source_kind={source_kind}; compatibility={compatibility['status']}; "
                f"scanned={sync_result['discovered_count']}"
            ),
        )
        return {
            "ok": True,
            "name": str(manifest.get("name") or target_name),
            "source": source,
            "source_kind": source_kind,
            "target_path": str(target_dir),
            "compatibility": compatibility,
            "manifest": manifest,
        }
    except Exception as exc:
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        append_external_asset_event(
            action="install-request",
            name=target_name,
            asset_type="skill",
            target_path=str(target_dir),
            actor=actor,
            source=source,
            result="failed",
            detail=str(exc),
        )
        raise


def render_external_install_result(result: dict[str, Any]) -> str:
    """Render a concise install result."""
    compatibility = result.get("compatibility", {})
    lines = [
        "External skill installed",
        f"- name: {result.get('name')}",
        f"- source: {result.get('source')}",
        f"- source_kind: {result.get('source_kind')}",
        f"- target_path: {result.get('target_path')}",
        f"- compatibility: {compatibility.get('status', 'unknown')}",
    ]
    if compatibility.get("missing_toolchains"):
        lines.append(
            "- missing_toolchains: "
            + ", ".join(compatibility.get("missing_toolchains", []))
        )
    if compatibility.get("required_platforms"):
        lines.append(
            "- required_platforms: "
            + ", ".join(compatibility.get("required_platforms", []))
        )
    return "\n".join(lines)


def _install_from_local_path(source_path: Path, target_dir: Path) -> None:
    source_path = source_path.expanduser().resolve()
    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"Source lokal tidak ditemukan: {source_path}")
    shutil.copytree(source_path, target_dir)


def _install_from_git(source: str, target_dir: Path) -> None:
    toolchains = get_toolchain_info()
    git_info = toolchains["tools"].get("git", {})
    if not bool(git_info.get("available")):
        raise RuntimeError("Git belum tersedia di OS ini; install tidak dapat dilanjutkan.")
    normalized_source = source.removeprefix("git+")
    result = run_process(
        ["git", "clone", "--depth", "1", normalized_source, str(target_dir)],
        cwd=get_external_skills_dir(),
        timeout_seconds=300.0,
    )
    if not result["ok"]:
        raise RuntimeError(
            "Git clone gagal: " + (str(result["stderr"]).strip() or str(result["stdout"]).strip() or "unknown error")
        )


def _detect_source_kind(source: str) -> str:
    if Path(source).expanduser().exists():
        return "local"
    if source.startswith(GIT_PREFIXES) or source.endswith(".git") or "github.com/" in source:
        return "git"
    raise ValueError(
        "Source tidak dikenali. Gunakan path lokal atau URL git."
    )


def _derive_asset_name(source: str) -> str:
    source_path = Path(source).expanduser()
    if source_path.exists():
        return source_path.name

    parsed = urlparse(source.removeprefix("git+"))
    candidate = Path(parsed.path).name if parsed.path else source
    if candidate.endswith(".git"):
        candidate = candidate[:-4]
    return candidate or "external-skill"


def _normalize_asset_name(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip()).strip("-_.").lower()
    return normalized
