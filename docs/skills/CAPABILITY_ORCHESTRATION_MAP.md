# Capability Orchestration Map

## Purpose

Document the canonical cross-skill chains that define the baseline behavior of the autonomous personal assistant.

This map is intentionally pragmatic:

- only include chains that are valid with the current runtime
- distinguish between `semi_auto` and `operator_assisted`
- avoid claiming automatic chaining where the runtime still expects an explicit follow-up command

## Chain Status

- `semi_auto`
  the chain is naturally supported by current runtime behavior and can be continued with low-friction follow-up

- `operator_assisted`
  the chain is valid, but one or more transitions are still explicit user/operator actions

## Canonical Chains

| Chain | Status | Purpose | Notes |
|---|---|---|---|
| `observe -> decide -> act` | `semi_auto` | Observe current runtime state, choose the best next action, then execute it | `decide` may choose `executor next`, `monitor alerts`, `observe jobs`, or `schedule show` depending on state |
| `review -> plan` | `semi_auto` | Turn review findings into explicit follow-up tasks | `self-review` already persists follow-up planner tasks when heuristic findings are significant |
| `research -> memory` | `operator_assisted` | Convert verified external findings into durable memory when still relevant | Research stays read-only; persistence should remain explicit through `memory add` or `memory curate` |
| `inspect -> plan` | `operator_assisted` | Inspect local workspace, then capture follow-up work in planner | Useful for codebase exploration and implementation backlog creation |
| `monitor -> decide -> act` | `semi_auto` | Escalate from warning detection to best next action, then execute if appropriate | This is the warning-first variant of the observation chain |
| `persona -> reflect -> plan` | `operator_assisted` | Use persona/preference state to inform reflective prioritization and planner changes | Valuable for personal assistant tuning, but not yet automatic |

## Transition Rules

### `observe -> decide`

- prefer this when the user asks what should happen next after looking at status or health
- `decide` should remain read-only and produce a command recommendation, not execute it directly

### `decide -> act`

- `decide next` should prefer:
  - `monitor alerts` when operational warnings exist
  - `executor next` when a planner task is ready
  - `observe jobs` when queue activity deserves inspection
  - `schedule show` when quiet-hours or scheduler state dominates
  - `agent-loop next` when the system is quiet and needs a reflective suggestion

### `review -> plan`

- `review` may create follow-up tasks automatically when findings justify it
- planner remains the durable source of truth for follow-up work

### `research -> memory`

- research output must stay distinguishable from memory
- persistence should be explicit so stale external facts are not silently promoted into long-term memory

### `inspect -> plan`

- inspection should stay read-only
- any backlog item derived from inspection should be created explicitly in `planner`

## Validation Targets

The repository should maintain regression coverage for:

- `observe -> decide -> act`
- `review -> plan`
- `research -> memory`
- `inspect -> plan`
- `monitor -> decide -> act`
- `persona -> reflect -> plan`

## Next Hardening Targets

- add more explicit chain hints in help and operator docs
- consider structured chain traces so cross-skill orchestration becomes easier to audit
- continue validating standard aliases in operator-facing help and routing surfaces
