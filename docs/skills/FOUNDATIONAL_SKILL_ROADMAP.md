# Foundational Skill Roadmap

## Objective

Build a mature, standard, and validated foundational skill layer for an autonomous personal assistant.

## Principles

- capability-first naming
- backward-compatible migration
- clear skill boundaries
- measurable readiness
- validation before promotion

## Stage 1: Capability Definition

Goal:

- define the standard capability taxonomy
- map current skills to standard capability roles
- define missing capabilities and ownership

Outputs:

- approved capability taxonomy
- capability mapping table
- foundational readiness matrix draft

Deliverables:

- `docs/skills/CHANGE_REQUEST_FOUNDATIONAL_SKILLS.md`
- `docs/skills/FOUNDATIONAL_CAPABILITIES.md`
- `docs/skills/SKILL_READINESS_MATRIX.md`

## Stage 2: Skill Definition Hardening

Goal:

- define mature purpose and boundaries for each skill
- define stable inputs, outputs, and failure modes
- define state touchpoints and risk expectations

Priority skills:

1. `memory`
2. `planner`
3. `executor`
4. `agent-loop`
5. `workspace`
6. `research`

Outputs:

- mature skill definition per priority skill
- standard examples and command surface
- routing notes for orchestration

## Stage 3: Naming Standardization

Goal:

- expose standard capability names without breaking legacy commands

Approach:

1. add aliases for standard names
2. update help and audit output to show standard capability names
3. update routing prompts to prefer standard names
4. decide later whether physical folder renames are needed

Priority mapping:

- `ai-chat` -> `chat`
- `agent-loop` -> `reflect`
- `planner` -> `plan`
- `executor` -> `act`
- `workspace` -> `inspect`
- `profile` -> `persona`
- `self-review` -> `review`

## Stage 4: Missing Capability Introduction

Goal:

- add capabilities that are still implicit or missing

Priority additions:

1. `observe`
2. `decide`
3. `notify`
4. `identity`
5. `policy`
6. `schedule`
7. `monitor`

Definition expectation for each new capability:

- purpose
- command surface
- state touchpoints
- routing rule
- validation cases

## Stage 5: Functional Validation

Goal:

- prove each foundational skill works as a stable assistant capability

Validation layers:

- unit validation
- integration validation
- scope/privacy validation
- orchestration/routing validation
- operator/audit validation

Target outcome:

- each foundational capability classified as `draft`, `usable`, or `stable`

## Stage 6: Promotion To Baseline

Goal:

- promote the finalized foundational skill layer as the default assistant baseline

Outputs:

- updated help surface
- updated operator docs
- updated validation matrix
- release notes for capability naming and readiness

Current stage status:

- Stage 1: complete
- Stage 2: complete
- Stage 3: active
- Stage 4: complete
- Stage 5: active
- Stage 6: in progress

Interpretation:

- missing foundational capabilities have been introduced
- alias-first migration is active
- readiness promotion has started
- remaining work is concentrated on heuristic refinement and broader vocabulary adoption

## Recommended Implementation Order

1. capability taxonomy docs
2. readiness matrix docs
3. harden `memory`
4. harden `planner`
5. harden `executor`
6. harden `agent-loop`
7. harden `workspace`
8. harden `research`
9. standard aliases for key skills
10. add missing foundational capabilities
11. final validation and promotion

## Exit Criteria

- all foundational capabilities documented
- naming ambiguity removed
- major baseline capabilities validated
- readiness matrix published and current
