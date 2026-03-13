# Security Policy

## Supported Versions

Cadiax is currently maintained on the latest published baseline:

| Version | Supported |
| --- | --- |
| `1.1.x` | Yes |
| `< 1.1.0` | No |

## Reporting a Vulnerability

Please do not open public issues for credential leaks, auth bypasses, remote execution paths, or privacy-impacting bugs.

Preferred path:

1. Open a private GitHub security advisory for `irev/cadiax`.
2. Include a short summary, impact, reproduction steps, and affected version.
3. Remove secrets, tokens, and personal data from any shared logs.

What to include:

- affected version or commit
- deployment context
- exact trigger or request
- expected vs actual security boundary
- whether the issue affects local-only mode, service mode, or channel integrations

## Scope Notes

Cadiax keeps compatibility with legacy internal names such as `otonomassist`, `OTONOMASSIST_*`, and `.otonomassist/`. Security reports should reference the externally visible product name `Cadiax`, but may mention those compatibility surfaces when relevant.
