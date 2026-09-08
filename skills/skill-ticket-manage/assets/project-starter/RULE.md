# Project delivery rule

## Development

1. Implement the named spec strictly.
2. Do not change anything outside `In Scope`.
3. Do not touch anything in `Out of Scope`.
4. If a required change is outside the spec, record it in the ticket `outscope.md`; do not implement it.
5. Map every changed file to a spec item.
6. Add or update verification for every acceptance criterion.
7. After implementation, complete `diff-note.md`: implemented items, files changed and why, tests run, intentional deviations, and out-of-scope findings.
8. If the spec is ambiguous, make the safest minimal change and document the assumption. Write `none` when a section has no entry.

## Review

9. Treat an implementation plan as proposed. Validate every assumption against the current repository before editing while preserving the specification and acceptance criteria.

## Ticket and documentation layout

10. Before developing a feature, establish its SOT: what it does, how it works end to end, and its exact logic.
11. Use one `Issue/<ticket-id>/` folder per ticket. Resolve and mark DONE only after implementation, review, and all required verification pass.
12. Put architecture and feature documents in `document/`. Create a new document for a new feature; otherwise update the owning document.
13. Put deployment setup, guides, and runbooks in `deploy/`.

## Commit and push review gate

14. Complete one coherent fix in the working tree; do not commit every small edit.
15. Before asking for review, run targeted tests and provide a diff summary, evidence, assumptions, and remaining risks.
16. Keep reviewed changes uncommitted until explicit user approval. After approval, run required full-suite and deployment gates, then create one intentional commit and push it.
17. Amend the same uncommitted change set for review findings, rerun affected tests, and request review again.
18. Test uncommitted changes remotely only in an isolated review workspace. Only a reviewed, committed, exact-SHA artifact may become the active release.
