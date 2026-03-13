# Cadiax v1.1.3 Release Notes

## Summary

`v1.1.3` is the installer and workspace bootstrap hardening release.

This release makes Cadiax seed active runtime workspace documents during first install and setup, adds a Windows `install.bat` entrypoint, and hardens installer behavior so failures stop the process instead of appearing as a successful install.

## Highlights

- first-run install now seeds active workspace docs into the workspace root
- `cadiax setup` now ensures the selected workspace root contains the active runtime docs
- Windows installer now includes:
  - `install.ps1`
  - `install.bat`
- installer behavior is now fail-fast on subprocess errors
- installer now bootstraps `pip` with `ensurepip`
- installers now support custom virtual environment paths for deployment and smoke testing
- bootstrap defaults now seed only active runtime docs by default
- optional templates remain available through explicit opt-in

## What Changed

### Installation

- `install.ps1` now:
  - validates subprocess success
  - runs `ensurepip --upgrade`
  - supports `-VenvPath`
- `install.sh` now:
  - runs `ensurepip --upgrade`
  - supports `--venv-path`
- `install.bat` was added as a Windows-friendly wrapper for `install.ps1`

### Workspace Bootstrap

The default bootstrap path now seeds only the runtime-active workspace documents:

- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `IDENTITY.md`
- `TOOLS.md`
- `HEARTBEAT.md`

Optional templates such as the following are no longer seeded by default:

- `BOOT.md`
- `BOOTSTRAP.md`
- `*.dev.md`

They remain available through:

```bash
cadiax bootstrap foundation --include-optional
```

### Setup Flow

`cadiax setup` now ensures the chosen workspace root gets the active runtime documents if they are missing, without overwriting existing user-edited files.

### Runtime Behavior

Cadiax continues to use:

- `.cadiax/` for internal machine state
- `workspace root` for editable human-facing runtime documents

The active workspace docs are now more explicitly guaranteed to exist before normal runtime use.

## Validation

- targeted setup/bootstrap regression:
  - `pytest -q tests/test_setup_wizard.py -k "setup_wizard_persists_env_and_encrypted_secrets or bootstrap_foundation or doctor_reports_bootstrap_status"`
  - result: `5 passed`
- Windows installer smoke test:
  - `cmd /c install.bat -SkipSetup -VenvPath .venv-installtest`
  - result: success
- compile validation:
  - `python -m compileall src/cadiax/core/workspace_bootstrap.py src/cadiax/core/setup_wizard.py src/cadiax/cli.py tests/test_setup_wizard.py`

## Upgrade Notes

If you already have an existing workspace:

1. your current workspace docs are not overwritten by default
2. missing active runtime docs can be added via:
   - `cadiax bootstrap foundation`
3. optional templates can be added later via:
   - `cadiax bootstrap foundation --include-optional`

If you are automating installs:

1. prefer `install.bat` on Windows `cmd`
2. use `-VenvPath` or `--venv-path` when you need isolated deployment paths
3. expect installer failures to stop immediately instead of silently continuing

## Recommended Next Actions

1. run one real Windows first-run install with `install.bat`
2. run one real Linux first-run install with `install.sh`
3. decide whether `v1.1.3` should be cut as a dedicated installer-hardening release or folded into the next broader release
