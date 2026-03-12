# Release Notes

## Scope

This release closes the architecture checklist from `autonomous_ai_system_spec_extended.md` and the advanced maturity combination branch.

## Delivered

- Service boundaries for conversation, admin, worker, scheduler, and multichannel interfaces
- Durable runtime state on SQLite with legacy mirrors
- Unified trace and event bus coverage across runtime, policy, notifications, channels, bootstrap, and admin snapshots
- Personality, identity, soul, heartbeat, startup loader, and scoped continuity model
- Scoped privacy governance, export, retention preview, and consent controls
- Multichannel continuity and dispatch for Telegram, email, WhatsApp, webhook, and internal delivery
- Skill execution contracts with explicit schema, timeout behavior, and retry policy
- External skill isolation in subprocess runtime
- Validation matrix with `13/13` quick-check items marked complete

## Validation

- Automated verification: `pytest -q`
- Latest passing result on this branch: `158 passed`
- Validation matrix: `VALIDATION_MATRIX.md`

## Residual Risk

- Deployment still requires environment-specific smoke checks for active channels and credentials
- Generated service wrappers should be validated on the target OS/runtime before production rollout
- Operational secrets, token policies, and workspace permissions should be reviewed in the target environment

## Recommended Next Actions

1. Run deployment smoke tests on the intended host.
2. Review `.env` and service tokens.
3. Confirm workspace read/write policy and external skill approval policy.
4. Tag or merge the branch using your normal release process.
