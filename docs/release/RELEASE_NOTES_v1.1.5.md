# Cadiax v1.1.5 Release Notes

## Summary

`v1.1.5` is the installer preflight validation release.

This release makes Cadiax verify application requirements at the start of installation on both Windows and Linux before the real runtime install begins. The goal is to fail early and clearly when Python, version compatibility, or `venv` support are not actually ready on the target system.

## Highlights

- installer now runs dependency preflight checks before runtime installation starts
- Windows installer now verifies:
  - Python command availability
  - Python version compatibility
  - working `venv` support
- Linux installer now verifies:
  - Python command availability
  - Python version compatibility
  - working `venv` support
  - non-interactive sudo requirements for missing dependencies
- install no longer waits until mid-process to discover that Python exists but cannot create a virtual environment

## What Changed

### Windows Installer

- `install.ps1` now validates Python readiness before app-root creation and package install
- if Python is missing, the installer still attempts to install it via `winget`
- if Python exists but is too old or lacks `venv` support, the installer now stops immediately with a clear error

### Linux Installer

- `install.sh` now checks `python -m venv` up front
- when dependencies are missing and sudo would require interactive input, the installer now exits with a clear message instead of hanging

### Documentation

- install documentation now explicitly states that preflight dependency checks happen first
- native OS layout for app, dashboard, config, state, and workspace remains unchanged from `v1.1.4`

## Validation

- Windows native install smoke:
  - `cmd /c install.bat -SkipSetup`
  - result: success
- Linux native install smoke in WSL:
  - `./install.sh --skip-setup`
  - result: success
- regression suite:
  - `pytest -q tests/test_setup_wizard.py tests/test_public_package.py`
  - result: `82 passed`

## Recommended Next Actions

1. keep using the native user-install layout from `v1.1.4`
2. prefer the official installers for first-time user installs
3. rely on the new preflight stage to catch unsupported Python environments before runtime install begins
