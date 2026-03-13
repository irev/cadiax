# Foundational Skill Validation Plan

## Objective

Define how foundational autonomous personal assistant skills will be validated before and during implementation.

## Validation Categories

### 1. Capability Coverage Validation

Questions:

- does each mandatory foundational capability exist?
- is each capability mapped to a concrete skill or planned new skill?
- are missing capabilities explicitly tracked?

Pass condition:

- no foundational capability is ambiguous or unowned

### 2. Skill Definition Validation

Each skill must define:

- purpose
- boundaries
- inputs
- outputs
- state touchpoints
- failure modes
- success criteria

Pass condition:

- every foundational skill has a mature written definition

### 3. Functional Validation

For each foundational skill:

- valid input works
- invalid input fails clearly
- output shape is stable
- side effects are expected
- timeout and retry behavior are correct

Pass condition:

- core commands work consistently and predictably

### 4. Boundary Validation

Check:

- policy boundary
- privacy boundary
- session boundary
- scope boundary
- memory write/read boundary

Pass condition:

- no foundational skill violates scope, privacy, or policy constraints

### 5. Orchestration Validation

Check:

- routing chooses the correct foundational skill
- ambiguous prompts resolve predictably
- legacy names and standard aliases both work during migration

Pass condition:

- routing behavior matches the documented capability taxonomy

### 6. Audit Validation

Check:

- each foundational skill produces execution history
- important side effects appear in event/audit surfaces
- operator paths remain observable

Pass condition:

- no foundational skill executes as a black box

## Readiness Status Levels

- `draft`
  definition exists, but capability is not yet reliable

- `usable`
  core function works and is testable, but boundaries or UX still need refinement

- `stable`
  capability is well-defined, validated, and safe to treat as foundational baseline

## Validation Matrix Format

Each foundational capability should be tracked with:

- capability name
- current implementation skill
- target standard name
- status
- definition maturity
- test coverage status
- boundary validation status
- audit validation status
- notes

## Immediate Validation Priorities

Priority wave 1:

- `memory`
- `plan`
- `act`
- `reflect`
- `inspect`
- `research`

Priority wave 2:

- `chat`
- `persona`
- `review`
- `dispatch`
- `autopilot`
- `secrets`

Priority wave 3:

- `observe`
- `decide`
- `notify`
- `schedule`
- `monitor`
- `policy`
- `identity`

Current promotion snapshot:

- promoted to `stable`: `observe`, `notify`, `schedule`, `policy`, `identity`
- remaining `usable`: none

Reason:

- the promoted capabilities now have direct command coverage, assistant routing coverage, and regression validation across their expanded surfaces
- all foundational capabilities now meet the stable baseline; further work is incremental tuning, not readiness closure

## Approval Gate Before Implementation

Implementation should begin only after:

1. change request is approved
2. roadmap is approved
3. validation plan is approved
4. foundational capability taxonomy is accepted
5. migration strategy is accepted

## Final Success Condition

The foundational skill layer is considered mature when:

- capability coverage is complete
- naming is standardized
- definitions are mature
- validation status is visible
- implementation can proceed in ordered waves without ambiguity

Current state:

- capability coverage is complete
- validation status is visible
- expanded foundational capability surfaces are regression-tested
- final maturity work is concentrated on heuristic-heavy capabilities rather than missing architecture
