# Cadiax v1.1.4 Release Notes

## Summary

`v1.1.4` is the native user-install layout and service unification release.

This release moves Cadiax closer to a standard end-user application install on Windows and Linux. Runtime binaries, dashboard assets, configuration, state, and workspace are now separated into OS-native locations, and the main `cadiax` service now owns the optional Telegram runtime instead of treating it as a separate primary service.

## Highlights

- user install no longer depends on the downloaded git/source folder after installation
- native application install roots are now explicit on both Windows and Linux
- monitoring dashboard placement is now explicit and consistent with the native app root
- installer output now shows:
  - app root
  - config path
  - state path
  - workspace path
  - dashboard path
- Linux installer now checks `venv` support up front and fails clearly in non-interactive shells if sudo is required
- service deployment is now centered on one main target:
  - `cadiax`
- Telegram is now treated as an optional integrated runtime inside the main service, controlled by user settings

## Native User Install Layout

### Windows

- app: `%LOCALAPPDATA%\Cadiax\app\`
- dashboard: `%LOCALAPPDATA%\Cadiax\app\monitoring-dashboard\`
- config: `%APPDATA%\Cadiax\config.env`
- state: `%LOCALAPPDATA%\Cadiax\state\`
- workspace: `%USERPROFILE%\Cadiax\workspace\`

### Linux

- app: `~/.local/share/cadiax/app/`
- dashboard: `~/.local/share/cadiax/app/monitoring-dashboard/`
- config: `~/.config/cadiax/config.env`
- state: `~/.local/state/cadiax/`
- workspace: `~/cadiax/workspace/`

## What Changed

### Install Runtime

- install scripts now install Cadiax into native OS application directories
- installed executables now live under the native app venv instead of the source checkout
- source checkouts are only used as install input and can be removed after installation

### Dashboard Placement

- dashboard assets now live under the native application root
- documentation and installer output now state the dashboard location explicitly

### Linux Installer Hardening

- `install.sh` now probes whether `python -m venv` actually works before continuing
- when running non-interactively and sudo is required, the installer now exits with a clear message instead of hanging

### Service Model

- the recommended service target remains:

```bash
cadiax service run cadiax
```

- Telegram polling is no longer treated as a separate top-level deployment service for normal installs
- Telegram is enabled or disabled by user configuration:
  - `TELEGRAM_ENABLED=true|false`

## Validation

- Windows native install smoke:
  - `cmd /c install.bat -SkipSetup`
  - result: success
- Windows native CLI verification:
  - `%LOCALAPPDATA%\Cadiax\app\venv\Scripts\cadiax.exe --help`
  - result: success
- Windows user shim verification:
  - `%USERPROFILE%\.cadiax\bin\cadiax.cmd --help`
  - result: success
- Linux native install smoke in WSL:
  - `./install.sh --skip-setup`
  - result: success
- Linux native CLI verification:
  - `~/.local/share/cadiax/app/venv/bin/cadiax --help`
  - result: success
- Linux user shim verification:
  - `~/.local/bin/cadiax --help`
  - result: success
- dashboard asset placement verification:
  - Windows: `%LOCALAPPDATA%\Cadiax\app\monitoring-dashboard\`
  - Linux: `~/.local/share/cadiax/app/monitoring-dashboard/`
  - result: present on both platforms
- regression suite:
  - `pytest -q tests/test_setup_wizard.py tests/test_public_package.py`
  - result: `82 passed`

## Upgrade Notes

If you previously relied on repo-local installs:

1. new installs should use the native app runtime directories
2. project mode remains available for contributors working from the source tree
3. `.cadiax/` remains the project-mode state location, but user installs should now rely on OS-native config/state/workspace paths

If you deploy Cadiax as a service:

1. use `cadiax service run cadiax`
2. treat Telegram as an integrated optional component of that service
3. enable or disable Telegram through user configuration, not by splitting the main runtime into separate primary services
