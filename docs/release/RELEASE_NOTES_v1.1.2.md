# Cadiax v1.1.2 Release Notes

## Summary

`v1.1.2` is the Cadiax namespace migration release.

This release promotes `cadiax` as the primary public package and CLI surface, adds first-run installers for Windows and Linux, and aligns public documentation and release packaging with the Cadiax name.

## Highlights

- main package namespace migrated from `otonomassist` to `cadiax`
- public CLI entrypoints now use:
  - `cadiax`
  - `cadiax-telegram`
- legacy compatibility remains available:
  - `otonomassist`
  - `autonomiq`
- first-run installers added:
  - `install.ps1`
  - `install.sh`
- official install guide added at [INSTALL.md](/d:/PROJECT/otonomAssist/docs/operations/INSTALL.md)
- public environment variable aliases added:
  - `CADIAX_*`
- public state directory aligned to:
  - `.cadiax/`

## What Changed

### Public Surface

- Cadiax is now the primary application name across README, release docs, dashboard UI, and service-facing documentation.
- The canonical Python package for new installs is now `cadiax`.
- The canonical executable names for new installs are now `cadiax` and `cadiax-telegram`.

### Compatibility

- `otonomassist` remains available as a compatibility shim for legacy imports.
- legacy CLI aliases remain functional so existing local automation does not break immediately.
- legacy environment variable names remain accepted through compatibility mapping.

### Installation

- Windows users can bootstrap with [install.ps1](/d:/PROJECT/otonomAssist/install.ps1).
- Linux users can bootstrap with [install.sh](/d:/PROJECT/otonomAssist/install.sh).
- the installer flow now handles dependency checks, virtual environment creation, package install, optional dashboard dependency install, and `cadiax setup`

## Validation

- `pytest -q tests/test_public_package.py tests/test_autonomous_stability.py tests/test_setup_wizard.py`
- result: `190 passed`
- `python -m compileall src skills tests`

## Operational Notes

- `pip` still prints standard install messages such as `Successfully installed cadiax-1.1.2`; this is normal `pip` behavior and not a branding issue in Cadiax itself.
- the recommended public install path is to use the provided installer scripts, which end with the public-facing message `Cadiax installed`
- legacy internal references still exist only for compatibility and migration safety

## Upgrade Notes

If you are upgrading from older local setups:

1. prefer `cadiax` and `cadiax-telegram` for new scripts and shell usage
2. migrate state and automation references toward `.cadiax/`
3. migrate environment usage toward `CADIAX_*`
4. keep legacy aliases only as temporary compatibility bridges

## Recommended Next Actions

1. publish this release as `v1.1.2`
2. verify installer behavior on one Windows host and one Linux host
3. update any external docs or examples that still reference `otonomassist` as the public app name
