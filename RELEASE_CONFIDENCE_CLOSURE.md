# Release Confidence Closure

## Objective

Push release confidence from `95%` toward `98-99%` by closing the remaining operational and deployment-specific risks that are not fully proven by repository tests alone.

Companion execution form:

- `RELEASE_CONFIDENCE_WORKSHEET.md`

## Exit Condition

Release confidence can be treated as `98-99%` only if all items below are completed and recorded.

## 1. Host Preflight

- Confirm target OS:
  - Windows
  - Linux
- Confirm Python runtime on target host is the intended version.
- Confirm Node.js and npm are available if the dashboard will be enabled.
- Confirm writable paths:
  - repo root
  - `.otonomassist/`
  - generated service wrapper directory
- Confirm no unexpected port conflicts for:
  - `8787` admin API
  - `8788` conversation API
  - `8795` dashboard

Evidence to record:

- exact host OS
- Python version
- Node.js version
- npm version
- port availability check result

## 2. Secrets And Environment Closure

- Review `.env` on target host.
- Confirm only intended channels are enabled.
- Confirm real credentials exist only for enabled channels.
- Confirm `OTONOMASSIST_WORKSPACE_ROOT` is correct.
- Confirm `OTONOMASSIST_STATE_DIR` points to the intended durable storage path.
- Confirm `OTONOMASSIST_ADMIN_TOKEN` policy is intentional.
- Confirm dashboard access mode is intentional:
  - local-only `127.0.0.1`
  - or explicitly exposed with network controls

Evidence to record:

- sanitized `.env` review completed
- enabled channel list
- admin token policy decision
- dashboard host binding decision

## 3. Service Supervisor Closure

### Linux

- Generate wrappers:
  - `otonomassist service write worker --runtime posix`
  - `otonomassist service write scheduler --runtime posix`
  - `otonomassist service write admin-api --runtime posix`
  - `otonomassist service write conversation-api --runtime posix`
  - `otonomassist service write dashboard --runtime posix` if dashboard is enabled
- Install and start actual `systemd` units on target host.
- Verify restart behavior:
  - stop service
  - start service
  - reboot persistence if required

### Windows

- Generate wrappers:
  - `otonomassist service write worker --runtime windows`
  - `otonomassist service write scheduler --runtime windows`
  - `otonomassist service write admin-api --runtime windows`
  - `otonomassist service write conversation-api --runtime windows`
  - `otonomassist service write dashboard --runtime windows` if dashboard is enabled
- Install via Scheduled Task or chosen Windows supervisor.
- Verify restart behavior:
  - stop task/service
  - start task/service
  - logon/startup persistence if required

Evidence to record:

- wrapper files generated
- supervisor install command used
- service status after install
- restart verification result

## 4. Core Runtime Smoke Closure

- Start `admin-api`.
- Start `conversation-api`.
- Start `worker`.
- Start `scheduler`.
- Verify:
  - `GET /health`
  - `GET /status`
  - `GET /metrics`
  - `GET /events`
- Submit one conversation message:
  - `POST /v1/messages`
- Confirm queue/job flow still works:
  - enqueue one task
  - process it
  - verify history/metrics update

Evidence to record:

- response from `/health`
- response from `/status`
- one successful conversation trace id
- one successful worker/scheduler trace id

## 5. Dashboard Closure

Only required if dashboard is part of the release target.

- Run:
  - `otonomassist dashboard status`
  - `otonomassist dashboard enable`
  - `otonomassist dashboard run`
- Verify local access:
  - `GET /api/dashboard`
  - open browser UI locally
- Verify dashboard shows expected sections:
  - overview
  - runtime
  - routing
  - channels
  - identity
  - privacy
  - events
- If dashboard is exposed beyond localhost:
  - verify reverse proxy or firewall restriction
  - verify admin API token flow if required

Evidence to record:

- dashboard enable output
- dashboard status output
- `/api/dashboard` success response
- screenshot or browser confirmation

## 6. Channel Integration Closure

Only required for channels that will actually be used.

### Telegram

- Start transport.
- Verify inbound command.
- Verify auth/pairing behavior.
- Verify one outbound reply.

### Email

- Verify one outbound send.
- Verify one inbound route if applicable.

### WhatsApp

- Verify one outbound send.
- Verify one inbound route if applicable.

### Notifications

- Verify `notify send`.
- Verify one multi-delivery batch if used.

Evidence to record:

- per-channel success/failure
- message id or delivery id
- any auth/policy issues observed

## 7. Privacy And Scope Closure

- Run `otonomassist privacy show --json`.
- If scoped usage exists, run scoped privacy checks.
- Run prune preview:
  - `otonomassist privacy prune --dry-run`
- Verify quiet hours behavior if enabled.
- Verify consent gating for proactive notifications.
- Verify scope filtering for:
  - memory
  - identity/session
  - notifications
  - admin status/history/events

Evidence to record:

- privacy diagnostics snapshot
- prune preview result
- one scoped check result

## 8. Audit And Observability Closure

- Verify execution history records:
  - command completion
  - skill completion
  - routing path
  - admin snapshot access
  - dashboard-related service actions if dashboard is enabled
- Verify metrics are updating:
  - routes
  - AI requests
  - queue depth
  - latency
- Verify `doctor` shows expected sections:
  - routing
  - dashboard
  - privacy
  - runtime

Evidence to record:

- recent history sample
- metrics sample
- doctor output sample

## 9. Soak Closure

Run at least one extended runtime check on the target host.

Minimum recommended:

- `worker`: 30-60 minutes
- `scheduler`: 30-60 minutes
- `dashboard`: 30 minutes if enabled

Observe:

- process stays alive
- no restart loop
- no port flapping
- no unbounded log/error growth
- no obvious memory or CPU spike

Evidence to record:

- soak duration
- process uptime
- resource observations
- issues found or `none`

## 10. Final Release Gate

Release can move from `95%` to `98-99%` only if:

- automated tests still pass
- host preflight is complete
- service supervisor install is validated
- core runtime smoke is complete
- dashboard smoke is complete if enabled
- enabled channels are live-tested
- privacy/scope checks are complete
- audit and metrics are verified
- soak check is complete

## Suggested Sign-Off Record

Use this compact sign-off block:

```text
Release target: v1.1.0
Host OS:
Python:
Node:
Dashboard enabled: yes/no
Supervisor validated: yes/no
Core smoke: pass/fail
Channel smoke: pass/fail
Privacy/scope: pass/fail
Audit/metrics: pass/fail
Soak check: pass/fail
Residual issues:
Confidence after closure: __%
Approved by:
Date:
```
