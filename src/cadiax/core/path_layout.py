"""Cross-platform runtime path layout helpers."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from dotenv import load_dotenv


def apply_env_aliases() -> None:
    """Mirror public and legacy env keys in both directions."""
    items = list(os.environ.items())
    for key, value in items:
        if key.startswith("CADIAX_"):
            legacy_key = "OTONOMASSIST_" + key[len("CADIAX_") :]
            os.environ.setdefault(legacy_key, value)
        elif key.startswith("OTONOMASSIST_"):
            public_key = "CADIAX_" + key[len("OTONOMASSIST_") :]
            os.environ.setdefault(public_key, value)


def get_project_root() -> Path:
    """Return the package project root when running from the source tree."""
    return Path(__file__).resolve().parents[3]


def get_path_mode() -> str:
    """Return the effective runtime path mode."""
    override = _get_env("CADIAX_PATH_MODE", "OTONOMASSIST_PATH_MODE").strip().lower()
    if override in {"project", "user"}:
        return override
    return "project" if _is_project_tree(get_project_root()) else "user"


def get_config_env_file() -> Path:
    """Return the effective config env file path."""
    override = _get_env("CADIAX_CONFIG_FILE", "OTONOMASSIST_CONFIG_FILE").strip()
    if override:
        return Path(override).expanduser().resolve()
    if get_path_mode() == "project":
        return (get_project_root() / ".env").resolve()
    return (get_config_dir() / "config.env").resolve()


def get_config_dir() -> Path:
    """Return the effective config directory."""
    config_file = _get_env("CADIAX_CONFIG_FILE", "OTONOMASSIST_CONFIG_FILE").strip()
    if config_file:
        return Path(config_file).expanduser().resolve().parent
    if get_path_mode() == "project":
        return get_project_root().resolve()
    if os.name == "nt":
        root = _expand_native_base(
            _get_env("APPDATA"),
            _get_user_home() / "AppData" / "Roaming",
        )
        return (root / "Cadiax").resolve()
    root = _expand_native_base(
        _get_env("XDG_CONFIG_HOME"),
        _get_user_home() / ".config",
    )
    return (root / "cadiax").resolve()


def get_state_dir() -> Path:
    """Return the effective durable state directory."""
    override = _get_env("CADIAX_STATE_DIR", "OTONOMASSIST_STATE_DIR").strip()
    if override:
        return Path(override).expanduser().resolve()
    if get_path_mode() == "project":
        return (get_project_root() / ".cadiax").resolve()
    if os.name == "nt":
        root = _expand_native_base(
            _get_env("LOCALAPPDATA"),
            _get_user_home() / "AppData" / "Local",
        )
        return (root / "Cadiax" / "state").resolve()
    root = _expand_native_base(
        _get_env("XDG_STATE_HOME"),
        _get_user_home() / ".local" / "state",
    )
    return (root / "cadiax").resolve()


def get_workspace_root() -> Path:
    """Return the effective editable workspace root."""
    override = _get_env("CADIAX_WORKSPACE_ROOT", "OTONOMASSIST_WORKSPACE_ROOT").strip()
    if override:
        return Path(override).expanduser().resolve()
    if get_path_mode() == "project":
        return (get_project_root() / "workspace").resolve()
    if os.name == "nt":
        return (_get_user_home() / "Cadiax" / "workspace").resolve()
    return (_get_user_home() / "cadiax" / "workspace").resolve()


def get_app_install_root() -> Path:
    """Return the OS-native application install root for user installs."""
    override = _get_env("CADIAX_APP_DIR", "OTONOMASSIST_APP_DIR").strip()
    if override:
        return Path(override).expanduser().resolve()
    if get_path_mode() == "project":
        return get_project_root().resolve()
    executable = Path(sys.executable).resolve()
    if executable.parent.name.lower() in {"scripts", "bin"} and executable.parents[1].name.lower() == "venv":
        return executable.parents[2].resolve()
    if os.name == "nt":
        root = _expand_native_base(
            _get_env("LOCALAPPDATA"),
            _get_user_home() / "AppData" / "Local",
        )
        return (root / "Cadiax" / "app").resolve()
    root = _expand_native_base(
        _get_env("XDG_DATA_HOME"),
        _get_user_home() / ".local" / "share",
    )
    return (root / "cadiax" / "app").resolve()


def get_dashboard_root() -> Path:
    """Return the effective dashboard project root."""
    return (get_app_install_root() / "monitoring-dashboard").resolve()


def load_runtime_env(*, override: bool = True) -> Path:
    """Load the effective config env file into the process environment."""
    env_file = get_config_env_file()
    if env_file.exists():
        load_dotenv(env_file, override=override)
    apply_env_aliases()
    return env_file


def _get_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return ""


def _get_user_home() -> Path:
    for value in (_get_env("USERPROFILE"), _get_env("HOME")):
        if value:
            return Path(value).expanduser().resolve()
    return Path.home().resolve()


def _expand_native_base(raw: str, fallback: Path) -> Path:
    if raw.strip():
        return Path(raw).expanduser().resolve()
    return fallback.expanduser().resolve()


def _is_project_tree(root: Path) -> bool:
    return (root / "pyproject.toml").exists() and (root / "src" / "cadiax").exists()
