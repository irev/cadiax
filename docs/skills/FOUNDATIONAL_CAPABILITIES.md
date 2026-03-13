# Foundational Capabilities

## Objective

Define the standard foundational capabilities required for an autonomous personal assistant, map them to the current skill layer, and identify the capabilities that still need explicit implementation.

## Capability Taxonomy

The foundational capability baseline for this repository is:

- `chat`
- `observe`
- `memory`
- `plan`
- `decide`
- `act`
- `reflect`
- `inspect`
- `research`
- `persona`
- `notify`
- `schedule`
- `monitor`
- `review`
- `policy`
- `secrets`
- `identity`

## Capability Definitions

### `chat`

Purpose:

- general conversation
- open reasoning
- clarification when no more specific skill should be used

### `observe`

Purpose:

- read the current local assistant state
- summarize active context, runtime condition, and operational status

Status:

- explicit foundational skill surface now exists via `observe`

### `memory`

Purpose:

- store, retrieve, summarize, curate, and consolidate memory

### `plan`

Purpose:

- manage goals, backlog, task status, and next actions

### `decide`

Purpose:

- choose the best action among available options based on goal, constraints, and current state

Status:

- explicit foundational skill surface now exists via `decide`

### `act`

Purpose:

- execute one approved internal action or planner task

### `reflect`

Purpose:

- inspect current state and infer next steps, risks, or corrections

### `inspect`

Purpose:

- inspect local workspace files, structure, content, and patterns

### `research`

Purpose:

- verify external facts, dates, schedules, and time-sensitive claims

### `persona`

Purpose:

- manage personality, preferences, constraints, communication style, and profile alignment

### `notify`

Purpose:

- deliver information outward to user/operator/channel targets

Status:

- explicit foundational skill surface now exists via `notify`

### `schedule`

Purpose:

- manage time-based execution, reminders, and deferred actions

Status:

- explicit foundational skill surface now exists via `schedule`

### `monitor`

Purpose:

- continuously watch important signals such as queue, failures, health, or status changes

Status:

- explicit foundational skill surface now exists via `monitor`

### `review`

Purpose:

- review outputs, plans, and actions to detect risk, quality issues, or missing steps

### `policy`

Purpose:

- inspect and manage allowed actions, boundaries, permissions, and operational safety rules

Status:

- explicit foundational skill surface now exists via `policy`

### `secrets`

Purpose:

- manage secrets and credentials without leaking them into general memory or prompts

### `identity`

Purpose:

- manage identity, session continuity, role mapping, and scoped user context

Status:

- explicit foundational skill surface now exists via `identity`

## Current Skill Mapping

| Current Skill | Standard Capability | Current Status | Notes |
|---|---|---|---|
| `ai-chat` | `chat` | Present | Naming should be standardized through alias-first migration |
| `memory` | `memory` | Present | Core baseline capability |
| `planner` | `plan` | Present | Naming should be standardized |
| `executor` | `act` | Present | Naming should be standardized |
| `agent-loop` | `reflect` | Present | Currently carries reflective reasoning role |
| `workspace` | `inspect` | Present | Naming should be standardized |
| `research` | `research` | Present | Already matches standard naming |
| `profile` | `persona` | Present | Naming should be standardized |
| `self-review` | `review` | Present | Naming should be standardized |
| `secrets` | `secrets` | Present | Already matches standard naming |
| `worker` | `dispatch` or execution support | Present but auxiliary | Runtime-oriented skill, not primary capability label |
| `runner` | `autopilot` or execution support | Present but auxiliary | Loop-oriented skill, not primary capability label |

## Missing Or Implicit Capabilities

These capabilities exist partially in services/runtime, but are not yet explicit foundational skills:

| Capability | Current Condition | Required Next Step |
|---|---|---|
| `observe` | Explicit through `observe` and backed by doctor/status/runtime snapshots | Broaden adoption and subcommand coverage |
| `decide` | Explicit through `decide` and backed by planner/runtime diagnostics | Stable baseline; continue minor tuning only if new decision classes appear |
| `notify` | Explicit through `notify` and backed by dispatcher/channel services | Broaden adoption and help/routing coverage |
| `schedule` | Explicit through `schedule` and backed by scheduler runtime | Broaden operations beyond show/run and clarify reminder-level scope |
| `monitor` | Explicit through `monitor` and backed by diagnostics/event surfaces | Stable baseline; continue incremental operator tuning only if new alert classes appear |
| `policy` | Explicit through `policy` and backed by policy service boundary | Broaden operations beyond show/check if needed |
| `identity` | Explicit through `identity` and backed by continuity service boundary | Broaden adoption and continuity operations coverage |

## Capability Groups

### Core Personal Assistant Loop

- `memory`
- `plan`
- `act`
- `reflect`
- `chat`

### Environment And Knowledge

- `inspect`
- `research`
- `observe`
- `monitor`

### Personalization And Continuity

- `persona`
- `identity`

### Governance And Safety

- `review`
- `policy`
- `secrets`

### Delivery And Time

- `notify`
- `schedule`

## Naming Strategy

Use a backward-compatible migration model:

1. keep existing current skill names working
2. introduce standard capability aliases
3. update help and audit output to expose standard names
4. validate routing behavior
5. only later decide whether physical folder renames are necessary

## Initial Recommended Alias Map

- `chat` -> `ai`
- `plan` -> `planner`
- `act` -> `executor`
- `reflect` -> `agent-loop`
- `inspect` -> `workspace`
- `persona` -> `profile`
- `review` -> `self-review`

## Readiness Interpretation

- `Present`
  capability exists now, even if naming still needs standardization

- `Implicit`
  capability exists in services/runtime but not yet as an explicit foundational skill

- `Missing`
  capability is not yet available in a meaningful baseline form

## Current Summary

- Explicitly present foundational capabilities: `11`
- Auxiliary/runtime support capabilities present: `2`
- Implicit capabilities still needing explicit skill surface: `0`
- Missing foundational architecture blockers: `0`

## Recommended Next Step

Create `docs/skills/SKILL_READINESS_MATRIX.md` to score each current skill and target capability using:

- definition maturity
- functional coverage
- boundary correctness
- audit coverage
- naming readiness
