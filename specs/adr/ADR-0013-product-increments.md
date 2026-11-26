---
id: ADR-0013
date: 2026-11-26
status: proposed
agreed_by: []
---

# ADR-0013: Product Increments as Release Units over Staging Batches

## Context
Staging batches (ADR-0007) group related packages of one project; without the grouping they cannot even be built together, and they serve as the basic testing ground for their packages. However, batches are silos: each lives in an isolated environment, while work proceeds across many batches at once.

A release combines multiple batches: derived artifacts (ISOs, installation images, containers) can only be built from the union of several batches, and integration tests must run against those combined artifacts. Today there is no way to express "these batches form one release", to track its readiness through defined phases, or to record what was released.

## Decision
We chose to introduce **Product Increments**: a named collection of staging batches representing one planned release or snapshot unit. No separate "product" entity is introduced.

1. **Scope:** exactly one project per increment. Multiple concurrent increments per project are allowed.
2. **Exclusive membership:** a staging batch belongs to at most one increment at a time.
3. **Package uniqueness:** at most one PR for a given package across all member batches of one increment.
4. **Entry precondition:** in `COLLECTING`, a batch may be added only while green - latest revision non-draft, all required reviews approved, mergeable. A batch that turns red after joining stays in the increment but blocks phase progression until recovered or deferred.
5. **States** (mirroring staging batches): `COLLECTING`, `IN_PROGRESS`, `PENDING_RELEASE`, `RELEASED` (terminal), `DROPPED` (terminal). All transitions are explicit manual releng actions:

   | From | To | Gate |
   |---|---|---|
   | `COLLECTING` | `IN_PROGRESS` | All member batches green |
   | `IN_PROGRESS` | `PENDING_RELEASE` | Latest increment revision fully green (see ADR-0014) |
   | `PENDING_RELEASE` | `IN_PROGRESS` | Rollback when something turns red |
   | `PENDING_RELEASE` | `RELEASED` | Release decision (see ADR-0015); archived read-only |
   | any non-terminal | `DROPPED` | Member batches become unassigned (deferred, still open) |

6. **Freeze:** `PENDING_RELEASE` is fully frozen - no changes except rollback or drop. In `IN_PROGRESS`, only removals and releng-approved PR changes are possible (see ADR-0014).
7. **Dates:** `collecting_until` (deadline for adding batches) and `release_date` (planned release).
8. **Ownership:** creation by releng or an automated tool (`author` recorded); releng owns all phase transitions, exception approval, and release.

## Consequences

**Positive:**
- One unit of release planning and tracking spanning many batches.
- Phase discipline with a human gate at every boundary.
- Deferring a batch preserves its work: it stays open and unassigned.
- Concurrent snapshots can be collected in parallel.

**Negative:**
- Adds another lifecycle layer above staging batches.
- Releng becomes the gatekeeper for every transition.
- Package uniqueness constrains how batches can be composed into one increment.
- The green entry precondition can delay admitting a batch.

## Considered Options
- **First-class "product" entity** - A distribution/codestream entity owning increments.
  Rejected because no product-level behavior is required; the increment alone captures the release-unit semantics.
- **Pure grouping label** - A stateless list of member batches.
  Rejected because release coordination needs phase discipline, freeze, and a terminal release record.
- **Independent state machine** - Increment states unrelated to batch states.
  Rejected because the semantics match the batch lifecycle; mirroring it avoids a second vocabulary.

## Assumptions
- Staging batches keep their full lifecycle (builds, tests, reviews, atomic merge) per ADR-0007.
- Releng is a distinct, identifiable role with authority over increments.
- Migration of `release_date` / `embargo_date` from staging batches (to the increment, and to package PRs respectively) is a follow-up decision.
- Emergency update (EMU) fast-tracking interactions are out of scope; revisit when EMU handling is specified.
