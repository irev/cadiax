# Deployment Checklist

## Preflight

- Confirm active branch and target commit.
- Run `pytest -q`.
- Review `VALIDATION_MATRIX.md`.
- Review `RELEASE_NOTES.md`.

## Environment

- Verify `.env` contains the intended AI provider settings.
- Verify admin and conversation API tokens if required.
- Verify Telegram, email, and WhatsApp credentials only for channels that will be enabled.
- Verify `OTONOMASSIST_WORKSPACE_ROOT` and workspace access mode.
- Verify `OTONOMASSIST_STATE_DIR` and durable storage location.

## Runtime

- Run `otonomassist doctor --json`.
- Run `otonomassist service status`.
- Generate wrappers if needed with `otonomassist service write`.
- Validate target services:
  - `worker`
  - `scheduler`
  - `admin-api`
  - `conversation-api`
  - `dashboard` if enabled

## Privacy And Scope

- Review `otonomassist privacy show --json`.
- Review scoped privacy if used:
  - `otonomassist privacy show --json --scope <scope> --role <role>`
- Review prune preview before cleanup:
  - `otonomassist privacy prune --dry-run`
  - `otonomassist privacy prune --dry-run --scope <scope> --role <role>`

## Channel Smoke Tests

- Admin API:
  - `GET /health`
  - `GET /status`
- Conversation API:
  - `POST /v1/messages`
- Notifications:
  - `otonomassist notify send "test message"`
- Email if enabled:
  - `otonomassist email send "test" --to <address>`
- WhatsApp if enabled:
  - `otonomassist whatsapp send "test" --to <number>`
- Telegram if enabled:
  - run transport and verify inbound/outbound behavior
- Monitoring dashboard if enabled:
  - `otonomassist dashboard status`
  - `otonomassist dashboard enable --no-install --no-build` if already built
  - `otonomassist dashboard run`
  - verify `http://127.0.0.1:8795/api/dashboard`

## Audit Verification

- Check recent execution history after smoke tests.
- Check recent event bus output after smoke tests.
- Confirm admin snapshot requests and bootstrap/service actions appear in audit history.

## Release Decision

- Confirm tests passed.
- Confirm smoke tests passed.
- Confirm no unexpected `doctor` warnings remain.
- Confirm secrets and workspace permissions are correct.
- Proceed with tag or merge.
