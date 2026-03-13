# Monitoring Dashboard

## Purpose

The monitoring dashboard is an optional web application that runs as a separate Node.js process and reads telemetry from the local OtonomAssist admin API.

## Characteristics

- separate from the core autonomous runtime
- optional feature, disabled until explicitly enabled
- local-only by default via `127.0.0.1`
- TypeScript client and server
- service wrapper support for Windows and Linux

## Basic Commands

Enable and prepare the dashboard:

```powershell
otonomassist dashboard enable
```

Show dashboard status:

```powershell
otonomassist dashboard status
```

Run the dashboard foreground service:

```powershell
otonomassist dashboard run
```

Disable dashboard access:

```powershell
otonomassist dashboard disable
```

## Service Wrappers

Render generated wrapper artifacts:

```powershell
otonomassist service show dashboard --runtime posix
otonomassist service show dashboard --runtime windows
```

Write wrapper artifacts to disk:

```powershell
otonomassist service write dashboard
```

## Default Ports

- admin API: `8787`
- dashboard: `8795`

## Notes

- The dashboard build is stored under `monitoring-dashboard/dist/`.
- Dependencies are installed under `monitoring-dashboard/node_modules/`.
- The dashboard state file is stored in `.otonomassist/dashboard_state.json`.
