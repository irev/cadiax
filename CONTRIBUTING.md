# Contributing

## Scope

This repository contains the OtonomAssist runtime, foundational capability layer, and optional monitoring dashboard.

## Before You Change Code

1. read [README.md](/d:/PROJECT/otonomAssist/README.md)
2. read [docs/README.md](/d:/PROJECT/otonomAssist/docs/README.md)
3. review the relevant architecture or skill document before making structural changes

## Development Expectations

- keep changes scoped and explicit
- preserve service boundaries and scoped privacy rules
- do not bypass policy or audit layers for convenience
- keep dashboard changes separate from Python runtime concerns unless integration is required

## Validation

Minimum expected validation:

- `pytest -q`
- `python -m compileall src tests`

If dashboard files are changed:

- `npm install`
- `npm run build`

## Documentation

When behavior or architecture changes:

- update the relevant file under `docs/`
- update `README.md` if public setup or usage changed
- update release docs if the change affects deployment or merge handoff

## Pull Request Notes

- describe why the change exists
- summarize behavior impact
- include test/build results
- call out operational risks if any
