# Release Confidence Worksheet

Use this worksheet during real deployment and release verification.

## Release Header

```text
Release target:
Branch:
Commit:
Host OS:
Hostname:
Python version:
Node version:
npm version:
Operator:
Date:
```

## 1. Host Preflight

| Check | Result | Notes |
|---|---|---|
| Python version matches target | [ ] Pass / [ ] Fail | |
| Node.js available if dashboard enabled | [ ] Pass / [ ] Fail | |
| npm available if dashboard enabled | [ ] Pass / [ ] Fail | |
| `.cadiax/` writable | [ ] Pass / [ ] Fail | |
| workspace root writable as intended | [ ] Pass / [ ] Fail | |
| port `8787` available | [ ] Pass / [ ] Fail | |
| port `8788` available | [ ] Pass / [ ] Fail | |
| port `8795` available if dashboard enabled | [ ] Pass / [ ] Fail | |

## 2. Environment And Secrets

| Check | Result | Notes |
|---|---|---|
| `.env` reviewed | [ ] Pass / [ ] Fail | |
| AI provider config valid | [ ] Pass / [ ] Fail | |
| admin token policy reviewed | [ ] Pass / [ ] Fail | |
| workspace root correct | [ ] Pass / [ ] Fail | |
| state dir correct | [ ] Pass / [ ] Fail | |
| only intended channels enabled | [ ] Pass / [ ] Fail | |
| dashboard host binding reviewed | [ ] Pass / [ ] Fail | |

## 3. Automated Verification

| Command | Result | Notes |
|---|---|---|
| `pytest -q` | [ ] Pass / [ ] Fail | |
| `cadiax doctor --json` | [ ] Pass / [ ] Fail | |
| `cadiax service status` | [ ] Pass / [ ] Fail | |
| `npm install` if dashboard enabled | [ ] Pass / [ ] Fail | |
| `npm run build` if dashboard enabled | [ ] Pass / [ ] Fail | |

## 4. Service Supervisor Validation

### Linux

| Check | Result | Notes |
|---|---|---|
| worker wrapper generated | [ ] Pass / [ ] Fail | |
| scheduler wrapper generated | [ ] Pass / [ ] Fail | |
| admin-api wrapper generated | [ ] Pass / [ ] Fail | |
| conversation-api wrapper generated | [ ] Pass / [ ] Fail | |
| dashboard wrapper generated if enabled | [ ] Pass / [ ] Fail | |
| systemd install verified | [ ] Pass / [ ] Fail | |
| restart behavior verified | [ ] Pass / [ ] Fail | |

### Windows

| Check | Result | Notes |
|---|---|---|
| worker wrapper generated | [ ] Pass / [ ] Fail | |
| scheduler wrapper generated | [ ] Pass / [ ] Fail | |
| admin-api wrapper generated | [ ] Pass / [ ] Fail | |
| conversation-api wrapper generated | [ ] Pass / [ ] Fail | |
| dashboard wrapper generated if enabled | [ ] Pass / [ ] Fail | |
| Scheduled Task or service install verified | [ ] Pass / [ ] Fail | |
| restart behavior verified | [ ] Pass / [ ] Fail | |

## 5. Core Runtime Smoke

| Check | Result | Notes |
|---|---|---|
| admin API `/health` | [ ] Pass / [ ] Fail | |
| admin API `/status` | [ ] Pass / [ ] Fail | |
| admin API `/metrics` | [ ] Pass / [ ] Fail | |
| admin API `/events` | [ ] Pass / [ ] Fail | |
| conversation API message flow | [ ] Pass / [ ] Fail | |
| worker processed one task | [ ] Pass / [ ] Fail | |
| scheduler processed one cycle | [ ] Pass / [ ] Fail | |
| execution history updated | [ ] Pass / [ ] Fail | |

## 6. Dashboard Smoke

Only complete if dashboard is enabled.

| Check | Result | Notes |
|---|---|---|
| `cadiax dashboard status` | [ ] Pass / [ ] Fail | |
| `cadiax dashboard enable` | [ ] Pass / [ ] Fail | |
| `cadiax dashboard run` | [ ] Pass / [ ] Fail | |
| `/api/dashboard` reachable | [ ] Pass / [ ] Fail | |
| browser UI reachable locally | [ ] Pass / [ ] Fail | |
| sidebar navigation renders | [ ] Pass / [ ] Fail | |
| routing/runtime/privacy panels render | [ ] Pass / [ ] Fail | |

## 7. Channel Smoke

Only complete channels that are actually enabled.

| Channel | Check | Result | Notes |
|---|---|---|---|
| Telegram | inbound command | [ ] Pass / [ ] Fail | |
| Telegram | outbound reply | [ ] Pass / [ ] Fail | |
| Email | outbound send | [ ] Pass / [ ] Fail | |
| Email | inbound route | [ ] Pass / [ ] Fail | |
| WhatsApp | outbound send | [ ] Pass / [ ] Fail | |
| WhatsApp | inbound route | [ ] Pass / [ ] Fail | |
| Notifications | single send | [ ] Pass / [ ] Fail | |
| Notifications | multi-delivery batch | [ ] Pass / [ ] Fail | |

## 8. Privacy And Scope

| Check | Result | Notes |
|---|---|---|
| `privacy show --json` reviewed | [ ] Pass / [ ] Fail | |
| prune preview reviewed | [ ] Pass / [ ] Fail | |
| quiet hours behavior checked | [ ] Pass / [ ] Fail | |
| proactive consent gating checked | [ ] Pass / [ ] Fail | |
| scoped admin/history/events checked | [ ] Pass / [ ] Fail | |
| scoped memory/identity/notification checks complete | [ ] Pass / [ ] Fail | |

## 9. Audit And Observability

| Check | Result | Notes |
|---|---|---|
| command history recorded | [ ] Pass / [ ] Fail | |
| skill history recorded | [ ] Pass / [ ] Fail | |
| routing telemetry recorded | [ ] Pass / [ ] Fail | |
| admin snapshot audit recorded | [ ] Pass / [ ] Fail | |
| doctor shows routing section | [ ] Pass / [ ] Fail | |
| doctor shows dashboard section if enabled | [ ] Pass / [ ] Fail | |
| metrics reflect runtime activity | [ ] Pass / [ ] Fail | |

## 10. Soak Check

```text
Worker soak duration:
Scheduler soak duration:
Dashboard soak duration:
Observed CPU trend:
Observed memory trend:
Restart loops seen:
Port instability seen:
Unexpected errors:
```

| Check | Result | Notes |
|---|---|---|
| worker soak acceptable | [ ] Pass / [ ] Fail | |
| scheduler soak acceptable | [ ] Pass / [ ] Fail | |
| dashboard soak acceptable if enabled | [ ] Pass / [ ] Fail | |

## 11. Final Gate

| Gate | Result | Notes |
|---|---|---|
| automated verification complete | [ ] Pass / [ ] Fail | |
| supervisor validation complete | [ ] Pass / [ ] Fail | |
| runtime smoke complete | [ ] Pass / [ ] Fail | |
| dashboard smoke complete if enabled | [ ] Pass / [ ] Fail | |
| channel smoke complete for enabled channels | [ ] Pass / [ ] Fail | |
| privacy and scope checks complete | [ ] Pass / [ ] Fail | |
| audit and observability checks complete | [ ] Pass / [ ] Fail | |
| soak check complete | [ ] Pass / [ ] Fail | |

## Final Sign-Off

```text
Residual issues:

Confidence after closure:

Approved for merge/release:

Approved by:

Date:
```
