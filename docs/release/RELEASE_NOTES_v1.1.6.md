# Cadiax v1.1.6

`v1.1.6` is the installer lifecycle and diagnostic hardening release.

This release makes the install flow easier to understand for end users by separating `install`, `reinstall`, and `uninstall` behaviors more explicitly, adds first-run dashboard configuration to the setup wizard, and fixes a security issue where `doctor --json` could expose API keys in plaintext.

## Highlights

- installer lifecycle is now explicit:
  - `install`
  - `reinstall`
  - `uninstall`
- running `install` over an existing runtime now asks for `Y/n` confirmation before continuing as `reinstall`
- setup wizard now configures optional monitoring dashboard settings during first-run
- provider diagnostics and `doctor --json` now mask API key values

## What Changed

### Installer Lifecycle

- `install` remains the first-run mode
- if an existing runtime is detected, the installer now prompts:
  - `Lanjutkan sebagai reinstall? [Y/n]`
- `reinstall` rebuilds or updates the runtime application without deleting user config, state, or workspace by default
- `uninstall` removes:
  - native app runtime
  - user command shims
- `uninstall` keeps user data by default:
  - config
  - state
  - workspace
- `purge` remains the explicit destructive path when full removal is intended

### Setup Wizard

The first-run setup wizard now also asks about monitoring dashboard settings:

- enabled or disabled
- access mode:
  - `local`
  - `public`
- dashboard port
- dashboard admin API URL

These values are stored in the dashboard state used by runtime diagnostics and dashboard control commands.

### Diagnostics and Security

- `doctor --json` no longer returns plaintext API keys
- provider config diagnostics now return masked values such as:
  - `********...7890`

## Validation

- Windows smoke passed:
  - install
  - implicit reinstall confirmation
  - uninstall
- Linux smoke passed in WSL:
  - install
  - implicit reinstall confirmation
  - uninstall
- targeted regression:
  - `doctor --json` secret masking
  - setup wizard dashboard persistence
  - setup wizard secret persistence
- `pytest -q tests/test_setup_wizard.py tests/test_public_package.py` -> `83 passed`

## Upgrade Notes

If you already have a Cadiax runtime installed:

1. running the installer in `install` mode will no longer hard-fail immediately
2. the installer will ask whether to continue as `reinstall`
3. use `uninstall` when you want to remove the app runtime cleanly
4. use purge only when you intentionally want to remove user data as well

## Recommended Next Actions

1. continue using `install` for first-run user documentation
2. use `reinstall` explicitly in operator/deployment docs when updating an existing runtime
3. verify any automation that previously depended on the old install-fails-fast behavior
