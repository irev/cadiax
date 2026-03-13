# Skill Readiness Matrix

## Objective

Measure the readiness of the current and target foundational skill layer before implementation changes are started.

## Readiness Scale

- `draft`
  capability exists conceptually or partially, but is not yet mature enough as a foundational baseline

- `usable`
  capability works in practice and has meaningful coverage, but still needs standardization or hardening

- `stable`
  capability is well-defined, validated, and suitable as a foundational baseline

## Evaluation Dimensions

Each capability is assessed using:

- `definition_maturity`
- `functional_coverage`
- `boundary_correctness`
- `audit_coverage`
- `naming_readiness`

Values:

- `low`
- `medium`
- `high`

## Matrix

| Capability | Current Skill / Surface | Status | Definition | Functional | Boundary | Audit | Naming | Notes |
|---|---|---|---|---|---|---|---|---|
| `chat` | `ai-chat` | stable | high | high | high | high | medium | Fallback chat capability is now formally bounded; naming should converge toward `chat` |
| `observe` | `observe` + doctor/status/runtime surfaces | stable | high | high | high | high | high | Observation surface now covers runtime, identity, notifications, events, history, jobs, and scheduler with direct regression coverage |
| `memory` | `memory` | stable | high | high | high | high | high | Strong core capability with scoped boundaries and durable state |
| `plan` | `planner` | stable | high | high | high | high | medium | Capability is mature; naming should align to `plan` |
| `decide` | `decide` + planner/runtime diagnostics | stable | high | high | high | high | high | Decision surface now prioritizes dominant runtime signals, quiet hours, and capability aliases with direct regression coverage |
| `act` | `executor` | stable | high | high | high | high | medium | Execution path is mature; naming should align to `act` |
| `reflect` | `agent-loop` | stable | high | high | high | high | medium | Reflective reasoning is now formally defined; naming should converge toward `reflect` |
| `inspect` | `workspace` | stable | high | high | high | high | medium | Functionally mature; naming should align to `inspect` |
| `research` | `research` | stable | high | high | high | high | high | Already fits standard naming and behavior |
| `persona` | `profile` | stable | high | high | high | high | medium | Persona/profile behavior is mature; naming should align to `persona` |
| `notify` | `notify` + notification dispatcher + channel interfaces | stable | high | high | high | high | high | Notification surface now covers single send, batch fanout, history inspection, and assistant-level routing |
| `schedule` | `schedule` + scheduler runtime | stable | high | high | high | high | high | Scheduling surface now covers show, run, and queue priming with direct regression coverage |
| `monitor` | `monitor` + metrics/events/doctor surfaces | stable | high | high | high | high | high | Monitoring surface now prioritizes dominant alerts, queue pressure, latency warnings, and recommended next checks with direct regression coverage |
| `review` | `self-review` | stable | high | high | high | high | medium | Review capability is now explicitly bounded; naming should align to `review` |
| `policy` | `policy` + policy service + diagnostics | stable | high | high | high | high | high | Policy surface now covers diagnostics, prefix inspection, and simulated authorization with direct regression coverage |
| `secrets` | `secrets` | stable | high | high | high | high | high | Mature governance capability with clear boundary |
| `identity` | `identity` + identity/session continuity service | stable | high | high | high | high | high | Identity surface now covers show, sessions, resolve, and continuity inspection through direct regression coverage |

## Summary

- `stable`: `17`
- `usable`: `0`
- `draft`: `0`

## Immediate Focus Areas

Priority wave 1:

- none

Reason:

- all foundational capabilities now qualify as stable; the next work is naming convergence and continued operator refinement

Priority wave 2:

- standard alias migration for `chat`, `plan`, `act`, `reflect`, `inspect`, `persona`, and `review`

Reason:

- capability definitions are now mature enough that the remaining work is naming convergence and routing/help alignment

## Key Findings

1. The repository is already strong in runtime architecture, boundaries, privacy, continuity, and auditability.
2. The main remaining gap is not infrastructure, but capability standardization and explicit foundational skill expression.
3. The main remaining readiness gap is now heuristic quality, not missing capability surface.
4. Naming standardization should continue using alias-first migration, not immediate destructive renaming.

## Implementation Gate

Implementation should start with:

1. promoting standard alias naming across help, routing, and operator surfaces
2. validating orchestration routing against the standard capability taxonomy
3. continuing operator-level refinements without changing the stable capability baseline

## Recommended Next Step

Focus heuristic hardening for:

- none

Then continue alias and adoption work for:

- `chat`
- `plan`
- `act`
- `reflect`
- `inspect`
- `persona`
- `review`
