# Issue / Ticket

Each issue is one folder under `Issue/`.
Flows live in the sibling `FLOW/` directory and group tickets toward a final
multi-ticket outcome. Standalone tickets remain valid.

<!-- NEXT_TICKET -->
**Next ticket:** `TD000001`
<!-- /NEXT_TICKET -->

## Identifier

- Format: `TD` plus six digits.
- The CLI derives the next ID from existing ticket folders.
- Each repository owns an independent counter.
- Cross-repository work uses one ticket per repository and cross-links them.

## Lifecycle

`OPEN` -> `SPEC-READY` -> `IN-PROGRESS` -> `IN-REVIEW` -> `DONE`

Only use `DONE` after implementation, review, required tests, documentation, external acceptance, and approval are complete.

## Ticket structure

Copy from `_TEMPLATE/` or use `ticket_tool.py new`.

<!-- FLOW_INDEX -->
## Flow index

_none_
<!-- /FLOW_INDEX -->
