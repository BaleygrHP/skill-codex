---
name: dispatching-parallel-agents
description: Review a task, ticket, or Flow for independent work, then route discovery, implementation, review, and architectural decisions with explicit dependencies and ownership.
---

# Dispatching Parallel Agents

Coordinate independent work with compact evidence and stable roles. Keep discovery and
scheduling inexpensive; request architectural decisions only when justified.
This is a local customization of [obra/superpowers](https://github.com/obra/superpowers)
and its `dispatching-parallel-agents` skill; preserve attribution.

## Authority, roles, and runtime

Explicit user overrides take precedence over this skill, including its routing and
role defaults. Respect higher-priority instructions and applicable project governance.
Read-only requests remain read-only. Inspect related work for context without expanding
the authorized implementation scope. Preserve unrelated changes.

Before dispatch, read [references/model-routing.md](references/model-routing.md)
for the approved model and effort mapping, and inspect the fresh runtime tool schema
for supported models, efforts, override fields, and capacity. Reuse the verified resolution
while runtime availability and user choices remain unchanged. The reference owns concrete
assignments; this workflow uses only these stable roles:

| Role | Responsibility |
| --- | --- |
| coordinator | Discover, classify, map dependencies, dispatch, aggregate, and assess final evidence. |
| explorer | Inspect a bounded domain read-only and return evidence and uncertainties. |
| executor | Implement, integrate, fix, update authorized records, and run required checks. |
| reviewer | Independently assess actual changes, tests, risks, and governing review gates. |
| architect | Resolve a difficult decision read-only from compact evidence; return a decision brief. |

The current main coordinates; follow the reference's mismatch disclosure and binding rules.
Never claim the skill switched the main or spawn a coordinator to pretend it changed.
Use only supported runtime fields and explicitly approved fallbacks.
If delegation or an effective binding is unavailable/unverified, block dependent dispatch;
report it and continue independent work with valid bindings and authority. Never substitute silently.

Delegation grants no authority to commit, push, deploy, publish, or close tickets/Flows.
Record changes and lifecycle operations require existing user authorization and the
project's governing workflow. Never manufacture approval, sign-off, or runtime proof.

## Classify and route

The coordinator establishes relevant contracts and evidence before routing:

- Simple read-only search, explanation, log inspection, or diff: handle directly;
  no architect and no worker unless independent discovery adds value.
- Independent read-only domains: dispatch disjoint explorers concurrently.
- Clear implementation: send a bounded brief directly to an executor, including
  single-file edits. A small score does not make implementation coordinator work.
- Unresolved difficult architecture, security, concurrency, consistency, or business
  decisions: gather evidence, obtain a compact architect decision when needed, then
  send the resolved implementation brief to an executor. A familiar, established
  solution in one of these domains does not automatically require an architect.
- Independent review: use a reviewer when requested, required by project governance,
  or warranted by risk. The reviewer uses the coordinator/explorer model family from
  the mapping in a separate agent; review does not require a different model family.
  Return ordinary findings to the executor. Escalate only a specific difficult decision
  or unresolved blocker, not review itself.

Use a lightweight score as a heuristic: start at zero; add `+3` for architecture or a
large refactor, `+2` each for cross-module impact, ambiguity, uncertain production root
cause, security, concurrency/consistency, or migration; subtract `2` each for a simple
single-file change and clear implementation. Scores `<=1` suggest simple handling,
`2-4` clear implementation, and `>=5` a check for unresolved decisions requiring an architect.
Risk triggers and actual dependencies override arithmetic. State the unresolved
decision and its risk before invoking an architect; a failing command or test alone
does not justify escalation.

An executor never self-approves. A reviewer must be independent of the implementation
it reviews. Independence concerns the agent and its work, not a requirement to switch
model families. The coordinator's aggregation is not a substitute for required review.

The default handoff is coordinator/explorers → executor → independent reviewer when
applicable → coordinator final assessment. Simple read-only work can finish with the
coordinator. A difficult unresolved decision branches to the architect, whose decision
returns to the executor; ordinary review findings loop to the executor for fixes/checks
and then to the reviewer. There is no mandatory architect approval at completion.

## Preflight: task, Flow, and tickets

Before implementation dispatch, the coordinator reviews the overall requested Flow,
its member tickets, full relevant specifications/source of truth, and linked
prerequisites or consumers needed to understand affected interfaces. Keep this overview
within authorized scope; neighboring tickets provide context, not permission to implement.
For standalone work, inspect its subtasks without inventing a ticket system.

Identify each ticket by repository plus ID because IDs can repeat across repositories.
Verify repository/worktree, branch, baseline commit, dirty state, active ownership,
available capacity, and affected source before trusting recorded status. Preserve existing
changes; mark any overlapping work and resolve ownership before edits.

For each dependency, retain the required artifact/condition, supporting evidence, and stage:

- Development prerequisite: an interface, decision, schema, or artifact needed to implement.
- Integration/runtime gate: development can use an established contract, but combined or
  real runtime verification must wait.
- Acceptance/release gate: review, sign-off, deployment, or closure must wait; development
  is blocked only if governing rules or actual prerequisites say so.
- Shared resource constraint: files, contracts, migrations, generated outputs, fixtures,
  databases, ports, or services require an explicit owner or exclusive schedule.

An open predecessor alone does not block all downstream development. Separate tickets
or directories alone do not prove independence. Inspect ambiguous dependency reasons
and governing specifications; keep uncertain dependent work pending while progressing
supported independent work. Never silently remove an explicit governance gate.

Split partially blocked tickets only where established contracts support bounded
deliverables with separable ownership. Pure modules, adapters, UI components, or contract
tests may proceed against those contracts. Do not invent contracts to create parallelism.
Fixtures, mocks, and offline tests are local evidence, not integration/runtime acceptance.

## Execution map and scheduling

Publish a compact execution map before implementation dispatch; group equivalent rows:

| Repo / ticket / deliverable | Evidence / baseline | Development prerequisites | Integration / acceptance gates | File / resource owner | Readiness / blocker |
| --- | --- | --- | --- | --- | --- |

Show ready work, dependency edges, shared-contract owners, and planned integration checks.
The map is reviewable coordination, not an extra approval gate for authorized work.
When useful independence is absent, explain the dependency and proceed sequentially.

Default to at most three concurrent workers, always within the global live-agent capacity
and project limits. Count explorers, executors, reviewers, architects, and nested workers
against shared capacity. Prefer peers; allow nested delegation only for an independent,
owned subtask whose scope and capacity are reported to the coordinator. Do not create
separate user-owned tasks for subtasks or duplicate work already assigned.

Submit ready independent work without waiting for unrelated workers. Prioritize work
that unlocks successors. Start newly unblocked work as soon as evidence confirms its
prerequisite and a slot opens; planned groups are not synchronization barriers.

Give shared contracts, migrations, generated outputs, and integration files one owner.
Serialize overlapping writes or use isolated worktrees with an integration owner.
Worktrees do not isolate shared runtime resources; schedule those separately.

On completion or a changed dependency, inspect actual results and evidence, update the
map, notify affected workers of interface changes, and revalidate assumptions. Release
only work whose prerequisites are now met. Close completed agents once their results
and evidence are retained; keep useful independent coordination moving meanwhile.

## Context and handoff contracts

Maintain three layers: L1 raw files/logs/diffs/command output; L2 coordinator working
summary of relevant findings, functions, dependencies, and uncertainties; L3 decision
context of critical facts, constraints, options, and unresolved questions for the architect.
Retain exact evidence references through every layer: repository/path and lines or symbols,
baseline/SHA, test/command and result, or precise log/event identity as appropriate.
Permit targeted source inspection when a decision needs it; avoid broad repeat scanning.

Construct self-contained prompts with role, objective, repository/worktree and baseline,
owned files/resources, interfaces, prerequisites, authorization boundaries, relevant
evidence, required checks, and expected output. Do not clone full session history or
send raw repository dumps. Handoff fields below are prompt content, not invented tool fields.

Keep worker results concise: up to roughly 1-3k tokens, not a minimum; exceed only for necessary evidence:

```yaml
summary:
files: # paths and relevance
findings: # each includes evidence and confidence
possible_issue:
recommended_next_step:
needs_architect: false
reason: # why escalation is or is not needed
```

Send an executor a resolved implementation brief:

```yaml
objective:
files: # owned paths
functions: # affected symbols/interfaces
changes:
do_not_change:
edge_cases:
tests_required: # commands, scope, prerequisites
acceptance: # observable criteria and remaining gates
```

Send an architect a compact escalation package:

```yaml
problem:
expected:
observed:
evidence: # exact references and bounded relevant excerpts
flow:
hypotheses:
options:
constraints:
questions: # specific decisions needed to unblock progress
```

The architect returns the selected option, rationale, constraints, risks, uncertainty, and required checks.
The coordinator incorporates this into the executor brief. Acceptance criteria are not proof of success.

## Retry and architect budget

The coordinator may retry a failed discovery/coordination attempt once with a narrower
scope justified by evidence. An executor self-debugs implementation/check failures for
one or two bounded rounds, then escalates unresolved decisions with evidence.
Do not invoke an architect for every test failure, environmental problem, or routine fix.
Report missing access/resources as blockers; avoid repeated unchanged attempts.

Allow at most two substantive architect requests per task, including follow-up questions
and requests to existing agents. Status polling does not count. Keep the task-wide count
across delegation and continuations; opening another agent does not reset it.
Follow-ups require an unresolved decision or new evidence/conflict. If exhausted,
report the blocker or obtain an explicit user-approved extension;
never skip required checks, review, or governance to fit the budget.

Use the mapped architect effort, normally medium. Raise to high only after medium was
insufficient; explain why. Higher effort requires explicit escalation and runtime support.
An effort increase or substantive follow-up still counts toward the same request budget.

## Integration, review, and final evidence

The coordinator checks returned claims against actual diffs and evidence. The executor
owns integration edits, review fixes, authorized documentation/ticket updates, and checks.
Run affected tests and required build/lint/documentation checks; run the full relevant
suite when the task or project requires it. Label scoped test evidence accurately.

When independent review applies, the reviewer examines the actual integrated changes
and check results. Route corrections to the executor. If subsequent changes affect
reviewed content, refresh affected checks and review; never reuse stale approval.
Authorized record updates must reproduce actual verdicts, evidence, and blockers.

Report implementation, tests/build, independent review, integration/runtime, deployment,
approval, and ticket/Flow closure separately. Worker completion, fixture success, or
a bounded review cannot prove runtime operation or satisfy remaining acceptance gates.

## Observability and rollout assessment

Keep a compact task record in the normal result/report channel, without requiring new
artifacts or an automated scheduler. Record role assignments, observed model/effort
requests and actual identity when exposed, spawn count, architect reasons/request count,
outcomes, tests/build results and scope, retries, and duration.
Record input/output tokens only when actually available; otherwise use null.
Distinguish requested configuration from observed execution; never estimate missing telemetry.

After about twenty real tasks or one week, assess routing using observed data.
Targets: architect below 20% of total weighted usage and at least 70% of discovery calls
on the low-cost coordinator/explorer mapping. Define the weighting from available usage
and cost data; if unavailable, report weighted usage as null, not inferred from spawn count.
Compare quality, missed impacts, retries, regressions, and duration against available baseline.
These are observational targets, not promised savings or claims of achieved acceptance.
Adjust routing, effort, or capacity only with evidence and authority; persist mapping changes only when authorized.
