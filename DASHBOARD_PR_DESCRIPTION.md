# Title

Add optional monitoring dashboard service

## Why

This adds a modern local monitoring dashboard that is separated from the core autonomous runtime. The goal is to give operators a cleaner UI for runtime status, routing telemetry, channels, identity, privacy, and event activity without coupling the AI process to a web frontend.

## What

- added a separate TypeScript dashboard app under `monitoring-dashboard/`
- added optional dashboard lifecycle commands:
  - `dashboard status`
  - `dashboard install`
  - `dashboard enable`
  - `dashboard disable`
  - `dashboard build`
  - `dashboard run`
- added durable dashboard state and access configuration
- added dashboard visibility into `doctor`
- added `dashboard` as a generated service target for Linux and Windows wrappers
- added operator docs in `MONITORING_DASHBOARD.md`

## Architecture

- Python runtime stays separate from the web UI
- dashboard runs as a Node process
- dashboard reads telemetry from the local admin API
- local-only access is the default (`127.0.0.1`)
- enable/build/install are optional and explicit

## UI

- left sidebar navigation
- modern card-based overview
- sections for:
  - overview
  - runtime
  - routing
  - channels
  - identity
  - privacy
  - events

## How tested

- `pytest -q` -> `188 passed`
- `npm install`
- `npm run build`
- local smoke test for `admin API -> dashboard proxy`

## Notes

- dashboard depends on the admin API being available
- service wrappers are generated, but supervisor installation still needs target-OS validation
- exposing the dashboard beyond localhost should be treated as an operator/network decision, not the default
