#!/usr/bin/env bash
set -euo pipefail

INSTALL_NODE=0
SKIP_SETUP=0
REUSE_VENV=0
SKIP_USER_SHIM=0
MODE="${MODE:-install}"
PURGE_DATA=0
PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_ROOT="${APP_ROOT:-}"
VENV_PATH="${VENV_PATH:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-node)
      INSTALL_NODE=1
      shift
      ;;
    --skip-setup)
      SKIP_SETUP=1
      shift
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --app-root)
      APP_ROOT="$2"
      shift 2
      ;;
    --venv-path)
      VENV_PATH="$2"
      shift 2
      ;;
    --reuse-venv)
      REUSE_VENV=1
      shift
      ;;
    --skip-user-shim)
      SKIP_USER_SHIM=1
      shift
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    --purge-data)
      PURGE_DATA=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "$MODE" != "install" && "$MODE" != "reinstall" && "$MODE" != "uninstall" ]]; then
  echo "Invalid mode: $MODE (expected install, reinstall, or uninstall)" >&2
  exit 1
fi

step() {
  echo "[Cadiax] $1"
}

python_is_usable() {
  "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

show_preflight_summary() {
  step "Preflight dependency check"
  echo "- python command: $PYTHON_BIN"
  echo "- python ready: yes"
  if need_cmd git; then
    echo "- git ready: yes"
  else
    echo "- git ready: no"
  fi
  if [[ "$INSTALL_NODE" -eq 1 ]]; then
    echo "- node requested: yes"
    if need_cmd node; then
      echo "- node ready: yes"
    else
      echo "- node ready: no"
    fi
  else
    echo "- node requested: no"
  fi
}

default_app_root() {
  if [[ -n "${XDG_DATA_HOME:-}" ]]; then
    printf '%s\n' "${XDG_DATA_HOME}/cadiax/app"
    return
  fi
  printf '%s\n' "${HOME}/.local/share/cadiax/app"
}

show_next_steps() {
  local venv_path="$1"
  local app_root="$2"
  local shim_dir="${3:-}"
  local resolved=""
  local config_path=""
  local state_path=""
  local workspace_path=""
  local dashboard_path=""
  local layout_info
  if command -v cadiax >/dev/null 2>&1; then
    resolved="$(command -v cadiax)"
  fi
  if layout_info="$("$venv_path/bin/python" -c 'from cadiax.core.path_layout import get_config_env_file, get_state_dir, get_workspace_root, get_dashboard_root; print(get_config_env_file()); print(get_state_dir()); print(get_workspace_root()); print(get_dashboard_root())' 2>/dev/null)"; then
    config_path="$(printf '%s\n' "$layout_info" | sed -n '1p')"
    state_path="$(printf '%s\n' "$layout_info" | sed -n '2p')"
    workspace_path="$(printf '%s\n' "$layout_info" | sed -n '3p')"
    dashboard_path="$(printf '%s\n' "$layout_info" | sed -n '4p')"
  fi

  echo
  echo "Cadiax installed"
  echo "App root: $app_root"
  echo "CLI: $venv_path/bin/cadiax"
  echo "Telegram CLI: $venv_path/bin/cadiax-telegram"
  if [[ -n "$config_path" ]]; then
    echo "Config: $config_path"
    echo "State: $state_path"
    echo "Workspace: $workspace_path"
    echo "Dashboard: $dashboard_path"
  fi
  echo
  echo "Use one of these:"
  echo "1. Run directly: $venv_path/bin/cadiax"
  echo "2. Activate the virtual environment first:"
  echo "   source $venv_path/bin/activate"
  echo "   cadiax"

  if [[ -n "$shim_dir" ]]; then
    echo "3. Open a new shell and use the registered user command from: $shim_dir"
  fi

  if [[ -n "$resolved" && "$resolved" != "$(pwd)/$venv_path/bin/cadiax" ]]; then
    echo
    echo "[Cadiax] Warning: 'cadiax' in this shell still resolves to: $resolved" >&2
    echo "[Cadiax] Activate the virtual environment or use the CLI path shown above." >&2
  fi
}

register_user_shims() {
  local venv_path="$1"
  local shim_dir="${HOME}/.local/bin"
  mkdir -p "$shim_dir"

  cat > "$shim_dir/cadiax" <<EOF
#!/usr/bin/env bash
"$venv_path/bin/cadiax" "\$@"
EOF
  cat > "$shim_dir/cadiax-telegram" <<EOF
#!/usr/bin/env bash
"$venv_path/bin/cadiax-telegram" "\$@"
EOF
  chmod +x "$shim_dir/cadiax" "$shim_dir/cadiax-telegram"

  if [[ -f "${HOME}/.profile" ]]; then
    if ! grep -Fq 'export PATH="$HOME/.local/bin:$PATH"' "${HOME}/.profile"; then
      printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "${HOME}/.profile"
    fi
  fi

  export PATH="$shim_dir:$PATH"
  echo "$shim_dir"
}

remove_user_shims() {
  local shim_dir="${HOME}/.local/bin"
  rm -f "$shim_dir/cadiax" "$shim_dir/cadiax-telegram"
  echo "$shim_dir"
}

uninstall_cadiax() {
  local app_root="$1"
  local config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/cadiax"
  local state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/cadiax"
  local workspace_dir="$HOME/cadiax/workspace"

  step "Menjalankan uninstall Cadiax"
  if [[ -d "$app_root" ]]; then
    rm -rf "$app_root"
    echo "- app removed: $app_root"
  else
    echo "- app removed: already-absent"
  fi
  local shim_dir
  shim_dir="$(remove_user_shims)"
  echo "- user shims removed: $shim_dir"

  if [[ "$PURGE_DATA" -eq 1 ]]; then
    rm -rf "$config_dir" "$state_dir" "$workspace_dir"
    echo "- config/state/workspace purged: yes"
  else
    echo "- config kept: $config_dir/config.env"
    echo "- state kept: $state_dir"
    echo "- workspace kept: $workspace_dir"
  fi
  echo
  echo "Cadiax uninstalled"
}

sync_app_assets() {
  local source_root="$1"
  local app_root="$2"
  if [[ -d "$source_root/monitoring-dashboard" ]]; then
    rm -rf "$app_root/monitoring-dashboard"
    mkdir -p "$app_root"
    cp -R "$source_root/monitoring-dashboard" "$app_root/monitoring-dashboard"
  fi
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_pkg() {
  local label="$1"
  shift
  local sudo_prefix=()
  if [[ "$(id -u)" -ne 0 ]]; then
    if ! need_cmd sudo; then
      echo "sudo tidak tersedia. Install $label secara manual lalu jalankan script ini lagi." >&2
      exit 1
    fi
    if [[ ! -t 0 ]] && ! sudo -n true >/dev/null 2>&1; then
      echo "Installer butuh hak sudo untuk menginstall $label, tetapi shell ini non-interaktif dan sudo meminta password." >&2
      echo "Install dependency tersebut secara manual, atau jalankan installer dari terminal interaktif." >&2
      exit 1
    fi
    sudo_prefix=(sudo)
  fi
  if need_cmd apt-get; then
    "${sudo_prefix[@]}" apt-get update
    "${sudo_prefix[@]}" apt-get install -y "$@"
    return
  fi
  if need_cmd dnf; then
    "${sudo_prefix[@]}" dnf install -y "$@"
    return
  fi
  if need_cmd pacman; then
    "${sudo_prefix[@]}" pacman -Sy --noconfirm "$@"
    return
  fi
  echo "Package manager tidak dikenali. Install $label secara manual lalu jalankan script ini lagi." >&2
  exit 1
}

ensure_python_venv_support() {
  local probe_dir=""
  probe_dir="$(mktemp -d 2>/dev/null || mktemp -d -t cadiax-venv)"
  if "$PYTHON_BIN" -m venv "$probe_dir" >/dev/null 2>&1; then
    rm -rf "$probe_dir"
    return
  fi
  rm -rf "$probe_dir"

  step "Menyiapkan dukungan virtual environment Python"
  if need_cmd apt-get; then
    install_pkg "Python virtual environment support" python3-venv python3-pip
  elif need_cmd dnf; then
    install_pkg "Python virtual environment support" python3
  elif need_cmd pacman; then
    install_pkg "Python virtual environment support" python
  else
    echo "Python tersedia tetapi modul venv/ensurepip belum siap. Install dukungan venv secara manual lalu jalankan script ini lagi." >&2
    exit 1
  fi

  probe_dir="$(mktemp -d 2>/dev/null || mktemp -d -t cadiax-venv)"
  if ! "$PYTHON_BIN" -m venv "$probe_dir" >/dev/null 2>&1; then
    rm -rf "$probe_dir"
    echo "Gagal menyiapkan virtual environment Python setelah instalasi dependency. Pastikan paket venv untuk Python aktif di sistem ini." >&2
    exit 1
  fi
  rm -rf "$probe_dir"
}

if [[ -z "$APP_ROOT" ]]; then
  APP_ROOT="$(default_app_root)"
fi

if [[ "$MODE" == "uninstall" ]]; then
  uninstall_cadiax "$APP_ROOT"
  exit 0
fi

if ! need_cmd "$PYTHON_BIN"; then
  install_pkg "Python" python3 python3-venv python3-pip
fi

if ! python_is_usable; then
  echo "Cadiax membutuhkan Python >= 3.10. Command '$PYTHON_BIN' pada sistem ini tidak memenuhi syarat." >&2
  exit 1
fi

ensure_python_venv_support

if ! need_cmd git; then
  install_pkg "Git" git
fi

if [[ "$INSTALL_NODE" -eq 1 ]] && ! need_cmd node; then
  if need_cmd apt-get; then
    install_pkg "Node.js and npm" nodejs npm
  elif need_cmd dnf; then
    install_pkg "Node.js and npm" nodejs npm
  elif need_cmd pacman; then
    install_pkg "Node.js and npm" nodejs npm
  fi
fi

show_preflight_summary

APP_ROOT="$("$PYTHON_BIN" - <<'PY' "$APP_ROOT"
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
)"
if [[ -z "$VENV_PATH" ]]; then
  VENV_PATH="$APP_ROOT/venv"
fi
VENV_PATH="$("$PYTHON_BIN" - <<'PY' "$VENV_PATH"
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
)"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$APP_ROOT"
sync_app_assets "$SOURCE_ROOT" "$APP_ROOT"

if [[ "$MODE" == "install" && -d "$VENV_PATH" ]]; then
  echo "Cadiax sudah terinstall di $APP_ROOT. Gunakan --mode reinstall untuk memperbarui instalasi, atau --mode uninstall untuk menghapusnya." >&2
  exit 1
fi

if [[ "$MODE" == "reinstall" && -d "$VENV_PATH" && "$REUSE_VENV" -eq 0 ]]; then
  step "Menghapus virtual environment lama di $VENV_PATH"
  rm -rf "$VENV_PATH"
fi

if [[ -d "$VENV_PATH" && "$REUSE_VENV" -eq 1 ]]; then
  step "Menggunakan virtual environment yang sudah ada di $VENV_PATH"
else
  step "Menyiapkan virtual environment $VENV_PATH"
  "$PYTHON_BIN" -m venv "$VENV_PATH"
fi

VENV_PY="$VENV_PATH/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Virtual environment gagal dibuat." >&2
  exit 1
fi

step "Menyiapkan pip"
"$VENV_PY" -m ensurepip --upgrade

step "Mengupgrade pip"
"$VENV_PY" -m pip install --upgrade pip

if [[ "$MODE" == "reinstall" ]]; then
  step "Memperbarui Cadiax"
else
  step "Menginstall Cadiax"
fi
"$VENV_PY" -m pip install "$SOURCE_ROOT"

step "Menyiapkan dokumen workspace aktif"
"$VENV_PY" -m cadiax.cli bootstrap foundation

SHIM_DIR=""
if [[ "$SKIP_USER_SHIM" -eq 0 ]]; then
  step "Mendaftarkan command Cadiax ke user PATH"
  SHIM_DIR="$(register_user_shims "$VENV_PATH")"
fi

if [[ "$INSTALL_NODE" -eq 1 ]]; then
  step "Menyiapkan dashboard dependency"
  "$VENV_PY" -m cadiax.cli dashboard install
fi

if [[ "$SKIP_SETUP" -eq 0 ]]; then
  step "Menjalankan Cadiax setup"
  "$VENV_PY" -m cadiax.cli setup
fi

show_next_steps "$VENV_PATH" "$APP_ROOT" "$SHIM_DIR"
