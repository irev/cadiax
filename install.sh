#!/usr/bin/env bash
set -euo pipefail

INSTALL_NODE=0
SKIP_SETUP=0
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
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

step() {
  echo "[Cadiax] $1"
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

if [[ "$INSTALL_NODE" -eq 1 ]]; then
  step "Menyiapkan dashboard dependency"
  "$VENV_PY" -m cadiax.cli dashboard install
fi

if [[ "$SKIP_SETUP" -eq 0 ]]; then
  step "Menjalankan Cadiax setup"
  "$VENV_PY" -m cadiax.cli setup
fi

echo
echo "Cadiax installed"
echo "CLI: $VENV_PATH/bin/cadiax"
echo "Telegram CLI: $VENV_PATH/bin/cadiax-telegram"
