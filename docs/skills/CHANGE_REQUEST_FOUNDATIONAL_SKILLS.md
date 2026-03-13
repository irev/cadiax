# Change Request: Foundational Autonomous Skill Standardization

## Title

Standardize foundational autonomous personal assistant skills, naming, and capability coverage.

## Background

The current repository already has strong runtime architecture, durable state, privacy governance, scoped continuity, audit trail, and release-readiness foundations. However, the skill layer still reflects repository-specific naming and capability grouping.

This creates three practical problems:

1. foundational capabilities are present but not always expressed as clear, standard autonomous-agent skills
2. several skill names are implementation-oriented rather than capability-oriented
3. there is no explicit readiness matrix that proves each foundational capability is mature enough for a general autonomous personal assistant baseline

## Problem Statement

The current skill set is functionally strong, but it does not yet fully satisfy the following product goals:

- a clear and standard vocabulary for autonomous agent capabilities
- explicit coverage of all baseline personal assistant abilities
- stable definitions for what each skill should do, should not do, and how it should be validated

## Current State

Current core skills:

- `agent-loop`
- `ai-chat`
- `executor`
- `memory`
- `planner`
- `profile`
- `research`
- `runner`
- `secrets`
- `self-review`
- `worker`
- `workspace`

Current strengths:

- strong architectural separation
- durable execution/runtime model
- scoped privacy, continuity, and multichannel support
- skill metadata already includes risk, idempotency, timeout, and retry contract

Current gaps:

- capability taxonomy is not yet standardized
- some names are repo-specific rather than general-purpose autonomous-agent naming
- some foundational capabilities are implicit in services/runtime but not explicit as skill capabilities

## Requested Change

Introduce a standardized foundational capability model for autonomous personal assistant skills, including:

1. standardized capability taxonomy
2. stable naming map from current skills to standard capability names
3. explicit identification of missing foundational capabilities
4. clear maturity definition for each capability
5. roadmap and validation plan before implementation rollout

## Target Capability Taxonomy

Mandatory baseline capabilities:

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

## Proposed Naming Alignment

Current to target mapping:

- `ai-chat` -> `chat`
- `agent-loop` -> `reflect`
- `planner` -> `plan`
- `executor` -> `act`
- `workspace` -> `inspect`
- `profile` -> `persona`
- `self-review` -> `review`
- `runner` -> `autopilot`
- `worker` -> `dispatch`
- `memory` -> `memory`
- `research` -> `research`
- `secrets` -> `secrets`

New capabilities to add explicitly:

- `observe`
- `decide`
- `notify`
- `schedule`
- `monitor`
- `policy`
- `identity`

## Scope

Included:

- capability taxonomy definition
- naming standard definition
- readiness matrix definition
- implementation roadmap
- validation criteria

Not included in this change request:

- immediate destructive rename of all existing skill folders
- forced backward-incompatible command removal
- runtime architecture rewrite

## Constraints

- backward compatibility must be preserved during migration
- existing skill slugs should remain usable during transition
- aliases should be used before physical renames
- policy, privacy, and scope boundaries must remain intact
- audit trail and validation matrix must remain updateable during rollout

## Success Criteria

This change request is considered complete when:

1. foundational capability taxonomy is documented
2. every current skill is mapped to a standard capability role
3. missing foundational capabilities are explicitly identified
4. implementation roadmap is approved
5. validation plan is approved
6. follow-up implementation can proceed without naming ambiguity

## Risks

- naming churn may confuse existing operator workflows if migration is too abrupt
- duplicated capability concepts may emerge if standard names and legacy names coexist too long
- capability overlap can blur routing behavior if boundaries are not clearly defined

## Mitigation

- use alias-first migration
- publish readiness matrix before implementation
- define clear skill boundaries and routing precedence
- update docs and help surfaces in tandem with capability rollout
