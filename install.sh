#!/usr/bin/env bash
set -euo pipefail

INSTALL_NODE=0
SKIP_SETUP=0
REUSE_VENV=0
SKIP_USER_SHIM=0
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PATH="${VENV_PATH:-.venv}"

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
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

step() {
  echo "[Cadiax] $1"
}

show_next_steps() {
  local venv_path="$1"
  local shim_dir="${2:-}"
  local resolved=""
  local config_path=""
  local state_path=""
  local workspace_path=""
  local layout_info
  if command -v cadiax >/dev/null 2>&1; then
    resolved="$(command -v cadiax)"
  fi
  if layout_info="$("$venv_path/bin/python" -c 'from cadiax.core.path_layout import get_config_env_file, get_state_dir, get_workspace_root; print(get_config_env_file()); print(get_state_dir()); print(get_workspace_root())' 2>/dev/null)"; then
    config_path="$(printf '%s\n' "$layout_info" | sed -n '1p')"
    state_path="$(printf '%s\n' "$layout_info" | sed -n '2p')"
    workspace_path="$(printf '%s\n' "$layout_info" | sed -n '3p')"
  fi

  echo
  echo "Cadiax installed"
  echo "CLI: $venv_path/bin/cadiax"
  echo "Telegram CLI: $venv_path/bin/cadiax-telegram"
  if [[ -n "$config_path" ]]; then
    echo "Config: $config_path"
    echo "State: $state_path"
    echo "Workspace: $workspace_path"
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
  local project_root="$1"
  local venv_path="$2"
  local shim_dir="${HOME}/.local/bin"
  mkdir -p "$shim_dir"

  cat > "$shim_dir/cadiax" <<EOF
#!/usr/bin/env bash
"$project_root/$venv_path/bin/cadiax" "\$@"
EOF
  cat > "$shim_dir/cadiax-telegram" <<EOF
#!/usr/bin/env bash
"$project_root/$venv_path/bin/cadiax-telegram" "\$@"
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

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_pkg() {
  local label="$1"
  shift
  if need_cmd apt-get; then
    sudo apt-get update
    sudo apt-get install -y "$@"
    return
  fi
  if need_cmd dnf; then
    sudo dnf install -y "$@"
    return
  fi
  if need_cmd pacman; then
    sudo pacman -Sy --noconfirm "$@"
    return
  fi
  echo "Package manager tidak dikenali. Install $label secara manual lalu jalankan script ini lagi." >&2
  exit 1
}

if ! need_cmd "$PYTHON_BIN"; then
  install_pkg "Python" python3 python3-venv python3-pip
fi

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

if [[ -d "$VENV_PATH" && "$REUSE_VENV" -eq 0 ]]; then
  step "Menghapus virtual environment lama di $VENV_PATH"
  rm -rf "$VENV_PATH"
fi

step "Menyiapkan virtual environment $VENV_PATH"
"$PYTHON_BIN" -m venv "$VENV_PATH"

VENV_PY="$VENV_PATH/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Virtual environment gagal dibuat." >&2
  exit 1
fi

step "Menyiapkan pip"
"$VENV_PY" -m ensurepip --upgrade

step "Mengupgrade pip"
"$VENV_PY" -m pip install --upgrade pip

step "Menginstall Cadiax"
"$VENV_PY" -m pip install .

step "Menyiapkan dokumen workspace aktif"
"$VENV_PY" -m cadiax.cli bootstrap foundation

SHIM_DIR=""
if [[ "$SKIP_USER_SHIM" -eq 0 ]]; then
  step "Mendaftarkan command Cadiax ke user PATH"
  SHIM_DIR="$(register_user_shims "$(pwd)" "$VENV_PATH")"
fi

if [[ "$INSTALL_NODE" -eq 1 ]]; then
  step "Menyiapkan dashboard dependency"
  "$VENV_PY" -m cadiax.cli dashboard install
fi

if [[ "$SKIP_SETUP" -eq 0 ]]; then
  step "Menjalankan Cadiax setup"
  "$VENV_PY" -m cadiax.cli setup
fi

show_next_steps "$VENV_PATH" "$SHIM_DIR"
