# Foundational Skill Definitions

## Purpose

This document hardens the first six priority foundational capabilities before implementation changes are applied to the live skill surface.

Priority capabilities in this phase:

- `memory`
- `plan`
- `act`
- `reflect`
- `inspect`
- `research`

## Definition Template

Each capability definition includes:

- purpose
- boundaries
- primary inputs
- expected outputs
- state touchpoints
- failure modes
- success criteria

---

## `memory`

### Purpose

- persist useful user and agent context
- retrieve relevant prior context
- summarize recent memory state
- consolidate operational lessons into durable long-term context

### Boundaries

Use `memory` when:

- storing facts, decisions, preferences, or contextual notes
- searching or reviewing prior memory
- consolidating memory or lessons
- curating stable memory from main session

Do not use `memory` when:

- the intent is task planning
- the content is secret material or credential data
- the user wants workspace file inspection
- the answer requires real-world fact verification from the web

### Primary Inputs

- `memory add <text>`
- `memory search <query>`
- `memory summarize`
- `memory consolidate`
- `memory list`
- `memory curate <text>`
- `memory journal <text>`

### Expected Outputs

- stable confirmation for writes
- relevant match list for search
- structured summary for summarize/consolidate flows
- clear boundary error on invalid session/scope writes

### State Touchpoints

- operational memory journal
- curated memory
- daily journal
- lessons
- memory summary state

### Failure Modes

- denied from shared session for curated writes
- denied on scope mismatch
- empty search results
- malformed command or missing text

### Success Criteria

- memory writes persist with correct scope and session metadata
- memory reads respect scope and role boundaries
- consolidate/summarize does not corrupt existing memory state
- no secret material is routed into memory by mistake

---

## `plan`

### Purpose

- manage agent goals, backlog, and task state
- expose the next actionable unit of work
- support controlled autonomous progression

### Boundaries

Use `plan` when:

- creating or changing agent goals
- adding, updating, blocking, or completing tasks
- querying next task or task list

Do not use `plan` when:

- the user wants general-purpose non-agent planning such as travel itineraries
- the user wants to execute a task immediately
- the request is only to store contextual memory

### Primary Inputs

- `planner set-goal <goal>`
- `planner add <task>`
- `planner list`
- `planner next`
- `planner done <id>`
- `planner block <id> <reason>`
- `planner update <id> ...`

### Expected Outputs

- stable task/goal confirmation
- readable task list and next-step output
- explicit failure when task id is invalid

### State Touchpoints

- planner state
- retry metadata
- planner notes

### Failure Modes

- invalid task id
- empty goal/task text
- scope mismatch during automated follow-up
- malformed planner mutation command

### Success Criteria

- task lifecycle is stable and observable
- next task is resolvable when todo items exist
- planner state remains consistent after repeated updates
- planner respects scope-aware visibility

---

## `act`

### Purpose

- execute one planner task or one internal command safely
- connect planning with observable action
- record outcome back into planner and memory

### Boundaries

Use `act` when:

- running the next planner task
- executing a planner-derived internal command
- following through on an approved internal action

Do not use `act` when:

- defining goals or backlog
- performing broad autonomous looping
- mutating high-risk governance surfaces without allowed path

### Primary Inputs

- `executor next`
- `executor run <command>`

### Expected Outputs

- command result
- completion, retry, or blocked status for planner-linked tasks
- explicit error for recursive or forbidden task execution

### State Touchpoints

- planner task state
- planner notes
- execution history
- execution metrics
- operational memory
- lessons

### Failure Modes

- timeout
- transient execution error
- blocked command
- recursive executor task
- command resolution failure

### Success Criteria

- execution result is observable in trace and planner state
- retry policy is applied correctly for transient failures
- high-risk actions are not silently bypassed
- planner-linked execution leaves consistent task state

---

## `reflect`

### Purpose

- infer next best step from current assistant state
- review planner, memory, lessons, and profile together
- recommend priorities without directly becoming a full executor

### Boundaries

Use `reflect` when:

- asking what should happen next
- requesting reflective analysis of assistant state
- asking for prioritized recommendations

Do not use `reflect` when:

- the user explicitly wants direct execution
- the user only wants a factual external answer
- the user only wants file inspection

### Primary Inputs

- `agent-loop next`
- `agent-loop reflect`

### Expected Outputs

- prioritized recommendation
- next-step suggestion
- state-aware reflection summary

### State Touchpoints

- planner state
- memory
- lessons
- profile/personality context
- context budgeted prompt assembly

### Failure Modes

- missing provider for reasoning path
- weak recommendation due to sparse state
- ambiguous result when planner is empty

### Success Criteria

- recommendations are grounded in current state
- reflection does not violate policy or scope boundaries
- output remains useful when state is incomplete

---

## `inspect`

### Purpose

- inspect local workspace files and structure
- read file content
- search text in repository/workspace
- summarize directories or file groups

### Boundaries

Use `inspect` when:

- listing files
- reading a file
- searching text in workspace
- summarizing local code or directories

Do not use `inspect` when:

- the user wants memory retrieval
- the user wants real-world research
- the user wants task planning or execution

### Primary Inputs

- `workspace tree <path>`
- `workspace read <path>`
- `workspace find <pattern>`
- `workspace summary <path>`

### Expected Outputs

- readable tree output
- file contents or controlled summary
- search hits with enough context to act on
- clear access error if workspace access is restricted

### State Touchpoints

- workspace filesystem
- workspace access policy

### Failure Modes

- path not found
- denied read due to workspace policy
- invalid command shape

### Success Criteria

- reads are accurate and non-destructive
- file inspection remains within workspace boundary
- outputs are useful for follow-up planning or reasoning

---

## `research`

### Purpose

- verify time-sensitive or real-world claims
- anchor answers to current date/time context
- produce source-backed structured results

### Boundaries

Use `research` when:

- facts may have changed over time
- the answer depends on dates, schedules, people, prices, or recent status
- the user explicitly asks to verify, browse, or check sources

Do not use `research` when:

- the answer is purely local to workspace or memory
- the user only wants brainstorming or opinion without factual lookup

### Primary Inputs

- `research <query>`
- examples:
  - `research kapan idul fitri 2026 di indonesia`
  - `research siapa presiden saat ini`

### Expected Outputs

- structured verified answer
- explicit verification status
- source list
- notes and gaps when confidence is limited

### State Touchpoints

- web lookup path
- provider reasoning path
- execution trace and metrics

### Failure Modes

- provider unavailable
- no web search capability
- low-confidence source set
- malformed structured response from provider

### Success Criteria

- answer is temporally anchored
- sources are present when verification is possible
- uncertainty is explicit when verification is weak
- result is clearly distinguishable from local-only reasoning

---

## Next Definition Wave

After these six are approved, harden:

- `chat`
- `persona`
- `review`
- `dispatch`
- `autopilot`
- `secrets`

Then define explicit new foundational capability surfaces for:

- `observe`
- `decide`
- `notify`
- `schedule`
- `monitor`
- `policy`
- `identity`
