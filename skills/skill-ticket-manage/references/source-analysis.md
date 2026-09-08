# Source analysis: Binance API project

This portable package was derived from the active repository state on 2026-07-30.

## Rules found

The source `trading-binance-api/docs/RULE.md` contains four groups:

- Development rules 1-8: strict scope, no out-of-scope edits, file-to-spec mapping, acceptance tests, diff note, and documented minimal assumptions.
- Review rule 9: validate the proposed plan against the current repository before editing.
- Initialization/layout rules 10-13: establish the feature SOT; one folder per ticket; architecture docs in `document/`; deployment material in `deploy/`.
- Commit/push rules 14-18: coherent uncommitted review unit, targeted evidence before review, explicit approval before commit/push, and isolated remote testing for uncommitted code.

The source lifecycle is:

```text
OPEN -> SPEC-READY -> IN-PROGRESS -> IN-REVIEW -> DONE
```

Backend and frontend ticket IDs are independent. Cross-repository work opens one ticket in each repository and cross-links them.

## Existing strengths

- Ticket-local spec, discussion, diff, review, and out-of-scope evidence.
- Clear separation of product SOT, architecture documents, ticket work, and deployment runbooks.
- Acceptance criteria are expected to name their tests.
- Review evidence can distinguish local gates from exact-SHA runtime/VPS acceptance.
- A ticket is not DONE merely because code exists.

## Drift risks observed

- The next ticket number is maintained manually in `Issue/README.md`.
- The source `_TEMPLATE` has no `review.md` or `outscope.md`, although most mature tickets use them.
- Ticket folder shapes are inconsistent across history.
- No repository script currently validates lifecycle transitions or DONE prerequisites.
- Status summaries in the index are free-form and can diverge from ticket README metadata.

## Portability decisions

- Preserve the source rule semantics, but use neutral project paths.
- Include all six ticket artifacts in the starter template.
- Derive the next ID from existing ticket directories rather than a manual counter.
- Add a read-only audit and guarded status transition.
- Keep external gates configurable in the spec instead of assuming Binance, PostgreSQL, worker, canary, or VPS infrastructure.
- Add a portable Flow layer above tickets for outcome/roadmap/milestone/current-wave management while preserving standalone ticket behavior and repository-local `Issue/` roots.
- Use deterministic change fingerprints for uncommitted review validity instead of relying only on commit SHAs.
