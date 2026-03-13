# Deployment Checklist

## Preflight

- Confirm active branch and target commit.
- Run `pytest -q`.
- Review `docs/release/VALIDATION_MATRIX.md`.
- Review `docs/release/RELEASE_NOTES.md`.
- Review `docs/release/RELEASE_CONFIDENCE_CLOSURE.md`.

## Environment

- Verify `.env` contains the intended AI provider settings.
- Verify admin and conversation API tokens if required.
- Verify Telegram, email, and WhatsApp credentials only for channels that will be enabled.
- Verify `OTONOMASSIST_WORKSPACE_ROOT` and workspace access mode.
- Verify `OTONOMASSIST_STATE_DIR` and durable storage location.

## Runtime

- Run `autonomiq doctor --json`.
- Run `autonomiq service status`.
- Generate wrappers if needed with `autonomiq service write`.
- Validate target services:
  - `worker`
  - `scheduler`
  - `admin-api`
  - `conversation-api`
  - `dashboard` if enabled

## Privacy And Scope

- Review `autonomiq privacy show --json`.
- Review scoped privacy if used:
  - `autonomiq privacy show --json --scope <scope> --role <role>`
- Review prune preview before cleanup:
  - `autonomiq privacy prune --dry-run`
  - `autonomiq privacy prune --dry-run --scope <scope> --role <role>`

## Channel Smoke Tests

- Admin API:
  - `GET /health`
  - `GET /status`
- Conversation API:
  - `POST /v1/messages`
- Notifications:
  - `autonomiq notify send "test message"`
- Email if enabled:
  - `autonomiq email send "test" --to <address>`
- WhatsApp if enabled:
  - `autonomiq whatsapp send "test" --to <number>`
- Telegram if enabled:
  - run transport and verify inbound/outbound behavior
- Monitoring dashboard if enabled:
  - `autonomiq dashboard status`
  - `autonomiq dashboard enable --no-install --no-build` if already built
  - `autonomiq dashboard run`
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
