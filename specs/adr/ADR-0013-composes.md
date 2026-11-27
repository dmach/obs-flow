---
id: ADR-0013
date: 2026-11-26
status: proposed
agreed_by: []
---

# ADR-0013: Composes as Release Units

## Context
Staging batches (ADR-0007) group related packages of one project.
Without the grouping they cannot even be built together,
and they serve as the basic testing ground for their packages.
However, batches are silos: each lives in an isolated environment, while work proceeds across many batches at once.

A release combines multiple batches: derived artifacts (repositories, ISOs, installation images, containers)
can only be built from the union of several batches, and integration tests must run against those combined artifacts.
Today there is no way to express "these batches form one release", to track its readiness through defined phases.

## Decision
We chose to introduce **composes**.
They are collections of staging batches, each representing one planned release unit.
They consist of RPMs and derived artifacts in a form that that can be released.

1. **Compose merge level:** composes define the `compose` merge level, extending the chain of ADR-0016 above the `batch` level (ADR-0007):
   PRs land only via compose release (ADR-0015). For projects whose floor or ceiling reaches `compose`, this supersedes ADR-0007's batch-release landing. Example: a distribution project with floor=`compose`, ceiling=`compose` accepts changes only via compose release.
2. **Scope:** compose maps to exactly one project. Multiple concurrent composes per project are allowed.
3. **Exclusive membership:** a staging batch belongs to at most one compose at a time.
4. **Package uniqueness:** compose MUST NOT contain multiple PRs of the same package.
5. **Entry precondition:** in `COLLECTING`, a batch may be added only while green - latest revision non-draft, all required reviews approved, mergeable. A batch that turns red after joining stays in the compose but blocks phase progression until recovered or deferred.
6. **States** (mirroring staging batches): `COLLECTING`, `IN_PROGRESS`, `PENDING_RELEASE`, `RELEASED` (terminal), `DROPPED` (terminal). All transitions are explicit manual releng actions; the permitted transitions and their gates are specified in a dedicated follow-up ADR.
7. **Freeze:** `PENDING_RELEASE` is fully frozen - no changes except rollback or drop. In `IN_PROGRESS`, only removals and releng-approved PR changes are possible (see ADR-0014).
8. **Dates:** `collecting_until` (deadline for adding batches) and `release_date` (planned release).
9. **Ownership:** creation by releng or an automated tool (`author` recorded); releng owns all phase transitions, exception approval, and release.

## Consequences

**Positive:**
- One unit of release planning and tracking that spans across multiple batches.
- Phase discipline with a human gate at every boundary.
- Deferring a batch preserves its work: it stays open and unassigned.
- Concurrent snapshots can be collected in parallel.

**Negative:**
- Adds another lifecycle layer above pull requests and staging batches.
- Releng becomes the gatekeeper for every transition.
- Package uniqueness constrains how batches can be grouped into one compose.
- The green entry precondition can delay including a batch in a compose.

## Considered Options
- **First-class "product" entity** - A distribution/codestream entity owning composes.
  Rejected because no product-level behavior is required; the compose alone captures the release-unit semantics.
- **Pure grouping label** - A stateless list of member batches.
  Rejected because release coordination needs phase discipline, freeze, and a terminal release record.
- **Independent state machine** - Compose states unrelated to batch states.
  Rejected because the semantics match the batch lifecycle; mirroring it avoids a second vocabulary.

## Assumptions
- Staging batches keep their full lifecycle (builds, tests, reviews) per ADR-0007. For projects whose merge floor reaches `compose` (ADR-0016), a batch's PRs merge only via its compose release (ADR-0015).
- Releng is a distinct, identifiable role with authority over composes.
- Migration of `release_date` / `embargo_date` from staging batches (to the compose, and to package PRs respectively) is a follow-up decision.
- Emergency update (EMU) fast-tracking interactions are out of scope; revisit when EMU handling is specified.
