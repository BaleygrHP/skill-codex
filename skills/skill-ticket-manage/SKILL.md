---
name: skill-ticket-manage
description: Initialize, create, review, audit, close, and coordinate repository-local spec-first work from final outcome Flow/Roadmap through milestones/current waves, tickets, independent review, and closeout, while preserving standalone ticket workflows. Use when a project manages Issue/TICKET folders, FLOW roadmaps, repository rules, named specs, ticket lifecycle transitions, dependency-gated implementation order, review debt, stale review fingerprint checks, or DONE/Flow DONE readiness.
---

# Manage outcome-driven spec-first work

Treat the repository rule and the named ticket spec as the implementation contract.

## Start

1. Inspect the active repository, branch, dirty files, repo-local agent instructions, rule file, ticket index, and ticket folder.
2. Preserve unrelated worktree changes.
3. If the workflow is absent, initialize it:

```powershell
python <skill>/scripts/ticket_tool.py init --project <project-path>
```

Use `--merge` only to add missing starter files to an existing workflow. It never overwrites existing files.

4. Open a ticket with:

```powershell
python <skill>/scripts/ticket_tool.py new --project <project-path> --title "<title>"
```

5. For multi-ticket outcomes, create a Flow with:

```powershell
python <skill>/scripts/ticket_tool.py flow-new --project <project-path> --title "<final outcome>"
```

Then link tickets with `flow-link` only after the relationship is explicit; never silently assign existing tickets to a Flow.
6. Read [workflow.md](references/workflow.md) before implementation, review, status transition, Flow planning, or closeout.
7. Read [source-analysis.md](references/source-analysis.md) only when comparing this portable workflow with the Binance project it came from.

## Execute a ticket

1. Establish the feature source of truth: what it does, end-to-end behavior, logic, edge cases, and rollback.
2. If the ticket belongs to a Flow, read `FLOW/<flow-id>/flow.md`, `current-wave.md`, and `review-queue.md`; work only on a next-executable ticket unless the user explicitly overrides the dependency gate.
3. Freeze `In Scope`, `Out of Scope`, and acceptance criteria before editing.
4. Validate assumptions against current code. Revise the proposed implementation approach when needed without weakening the accepted behavior.
5. Map every changed file to a spec item.
6. Add or update verification for every acceptance criterion.
7. Record unexpected required work outside scope in the ticket `outscope.md`; do not silently implement it.
8. Synchronize implementation, tests, SOT/architecture docs, `diff-note.md`, `review.md`, and ticket metadata.
9. Keep the coherent change set uncommitted for user review. Commit or push only after explicit approval.

## Manage a Flow

Use a Flow for one final multi-ticket result:

```powershell
python <skill>/scripts/ticket_tool.py flow-link --project <project-path> --flow FL000001 --ticket TD000104 --milestone M2 --depends-on TD000101,TD000103
python <skill>/scripts/ticket_tool.py flow-sync --project <project-path> --flow FL000001
python <skill>/scripts/ticket_tool.py flow-status --project <project-path> --flow FL000001
python <skill>/scripts/ticket_tool.py review-queue --project <project-path> --flow FL000001
python <skill>/scripts/ticket_tool.py flow-audit --project <project-path> --flow FL000001
```

`flow-sync` deterministically regenerates generated sections in `flow.md`, `current-wave.md`, `review-queue.md`, and the index. It must produce no diff when run twice without input changes.

Do not choose an arbitrary ticket from a Flow. A ticket is next executable only when its spec is ready, dependencies are DONE and reviewed, it has no blocker, and it is eligible in the current milestone.

## Audit and transition

Audit without modifying the project:

```powershell
python <skill>/scripts/ticket_tool.py audit --project <project-path>
python <skill>/scripts/ticket_tool.py audit --project <project-path> --ticket TD000001
```

Transition only through the canonical lifecycle:

```powershell
python <skill>/scripts/ticket_tool.py status --project <project-path> --ticket TD000001 --to SPEC-READY
```

The CLI refuses `DONE` unless the ticket passes the closeout audit. Do not bypass that refusal by editing the status manually.

Prefer the canonical close command for DONE:

```powershell
python <skill>/scripts/ticket_tool.py close --project <project-path> --ticket TD000001
```

For Flow closeout:

```powershell
python <skill>/scripts/ticket_tool.py flow-close --project <project-path> --flow FL000001
```

Flow DONE requires every required ticket DONE, no review debt, complete Flow-level evidence, synchronized architecture/SOT/rollback docs, and final closeout evidence. All generated queues are updated; no ticket folder or evidence file is physically deleted.

## Review debt and fingerprints

- After independent review approves the current change set, freeze its explicit
  reviewed-file manifest before commit:

```powershell
python <skill>/scripts/ticket_tool.py review-freeze --project <project-path> --ticket TD000001
```

  The default discovers current non-workflow Git additions, modifications,
  renames, and deletes. For an already committed historical review, use
  repeatable `--path` with `--no-discover`. Explicit paths may name another
  ticket/Flow artifact when governance metadata is intentionally in review
  scope; generated queues should normally remain excluded. Use `--allow-empty`
  only for a ticket-evidence-only review.
- Treat independent review as first-class evidence, not a note after implementation.
- A ticket has review debt when review is missing, not approved, has unresolved BLOCKER/HIGH findings, lacks evidence, or its reviewed change fingerprint no longer matches the current deterministic fingerprint.
- A frozen fingerprint hashes `reviewed-files.json`, the current state/content
  of exactly those reviewed paths, and normalized artifacts for the current
  ticket. It is stable when the approved change is committed and when unrelated
  files later change, but becomes stale if reviewed content or ticket evidence
  changes. Tickets without a manifest retain the legacy base/diff fingerprint
  until explicitly migrated and re-reviewed.
- `review-freeze` materializes every normalized lifecycle metadata line before
  hashing, so later `close` or dependency-derived `Unlocks` updates cannot make
  an unchanged review stale by inserting a new line.
- Normalized marker values are compatibility-sensitive. Do not rename them or
  expand normalization for explicitly reviewed governance files without an
  explicit migration and re-review of affected frozen tickets.
- Store the reviewed fingerprint in ticket metadata or `review.md`; if it differs after code/artifact changes, mark the review stale and refuse DONE.

## Safety

- Treat local targeted/full-suite results separately from guarded database, worker, canary, deployment, exact-SHA, and soak evidence.
- Do not claim an async accepted response is completion; verify terminal runtime state.
- Do not weaken readiness, auth, or security gates to make acceptance pass.
- Use the safest minimal assumption when the spec is ambiguous and record it in `diff-note.md`.
