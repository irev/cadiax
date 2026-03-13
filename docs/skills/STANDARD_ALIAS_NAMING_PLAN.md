# Standard Alias Naming Plan

## Objective

Align current skill names with a more standard autonomous assistant capability vocabulary without breaking existing routing, docs, or user habits.

## Migration Principle

- Keep current skill slugs as implementation identifiers for now.
- Promote standard capability names as primary aliases, help labels, and operator vocabulary.
- Avoid destructive folder renames until routing, docs, telemetry, and tests are already stable on the new vocabulary.

## Target Vocabulary

| Current Skill | Current Primary Slug | Standard Capability Name | Migration Intent |
|---|---|---|---|
| AI Chat | `ai` | `chat` | Promote `chat` as primary conversational alias |
| Planner | `planner` | `plan` | Promote `plan` as primary capability name |
| Executor | `executor` | `act` | Promote `act` as primary action capability name |
| Agent Loop | `agent-loop` | `reflect` | Promote `reflect` as the standard reasoning/reflection surface |
| Workspace | `workspace` | `inspect` | Promote `inspect` as the standard local environment capability |
| Profile | `profile` | `persona` | Promote `persona` as the standard personalization capability |
| Self Review | `self-review` | `review` | Promote `review` as the standard evaluation capability |

## Naming Rules

- Use standard capability names in docs, readiness matrix, and roadmap language.
- Preserve current slugs in code and storage until compatibility risks are low.
- Prefer alias-first migration over slug renaming.
- Update help text and examples before changing routing priority.
- Do not remove legacy aliases until at least one full validation wave has passed.

## Rollout Stages

### Stage 1: Documentation Alignment

- Use standard names in planning, roadmap, and validation docs.
- Keep current implementation slugs visible as mappings.

### Stage 2: Help and Prompt Alignment

- Update skill help and orchestration hints to prefer `chat`, `plan`, `act`, `reflect`, `inspect`, `persona`, and `review`.
- Keep legacy commands valid.

### Stage 3: Routing Preference Alignment

- Prefer standard aliases in command examples and routing documentation.
- Ensure telemetry and audit surfaces can display both standard capability name and implementation slug if needed.

### Stage 4: Optional Slug Renaming

- Rename physical folders or internal slugs only if compatibility cost is acceptable.
- Treat this as optional cleanup, not as a prerequisite for functional maturity.

## Compatibility Risks

- Existing docs and user habits may still rely on legacy commands.
- Some tests may assert current skill names directly.
- Audit/history surfaces may become inconsistent if standard names and slugs are mixed without clear mapping.
- Folder renames would be the highest-risk step and should be deferred.

## Validation Requirements

- Command help must expose the standard capability names clearly.
- Legacy aliases must remain functional during migration.
- Routing should not become ambiguous between standard aliases and existing subcommands.
- Audit and status surfaces should remain understandable when both naming layers appear.

## Immediate Next Step

Implement alias-first standardization for:

- `chat`
- `plan`
- `act`
- `reflect`
- `inspect`
- `persona`
- `review`

Start with documentation and help surfaces before changing deeper runtime routing behavior.
