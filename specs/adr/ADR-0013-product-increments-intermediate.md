---
id: INTERMEDIATE
date: 2026-11-26
status: draft-reference
agreed_by: []
note: Pre-split reference. Becomes ADR-0013, ADR-0014, ADR-0015, ADR-0016.
---

# Product Increments - Intermediate Design Reference

## Context
- Staging batches group related packages of one project; without the grouping they cannot even be built together. Batches also serve as the basic testing ground for their packages.
- Batches are silos: each lives in an isolated environment. Work proceeds across many batches at once.
- Derived artifacts (ISOs, installation images, containers) can only be built from the union of multiple batches, and integration tests must run against those combined artifacts. This is the release bottleneck: artifact builds must be serialized so every tested artifact contains all latest to-be-released packages and no unexpected side-effects reach released content.
- Projects pin packages via git submodules: package references are part of the project's Git repository.

## Part 1 - Entity, States, Membership (future ADR-0013)
- A **product increment** is a named collection of staging batches representing one planned release or snapshot unit. No separate "product" entity is introduced.
- **Merge policy mechanism** (future ADR-0016): each project sets two pointers on an ordered merge level chain - `merge_floor` (lowest permitted merge level = the discipline, default `push`) and `merge_ceiling` (highest enabled merge level, default `push`); a change may land on any level within `[floor .. ceiling]`; base levels `push` < `pr`; policy changes apply immediately, no per-object pinning, stranded objects resolved manually.
- **Compose merge level** (future ADR-0013): composes extend the chain with `compose` above `batch` (ADR-0007): PRs land only via compose release. Example: distribution project floor=`compose`, ceiling=`compose`.
- **Scope:** exactly one project per increment. Multiple concurrent increments per project are allowed; membership exclusivity prevents overlap.
- **Exclusive membership:** a staging batch belongs to at most one increment at a time.
- **Package uniqueness:** at most one PR for a given package across all member batches of one increment (enables individual package merges at release).
- **Entry precondition (COLLECTING):** a batch may be added only while green. Green = latest revision non-draft + all required reviews approved + mergeable. A batch that turns red after joining stays in the increment but blocks phase progression until recovered or deferred.
- **States** (mirroring staging batches): `COLLECTING`, `IN_PROGRESS`, `PENDING_RELEASE`, `RELEASED` (terminal), `DROPPED` (terminal).
- **Dates:** `collecting_until` (deadline for adding batches), `release_date` (planned release; used by datetime-targeted debouncing and future closest-increment automation).
- **Creation:** releng or an automated tool; `author` recorded.
- **Transitions** (all explicit manual releng actions):

| From | To | Gate |
|---|---|---|
| `COLLECTING` | `IN_PROGRESS` | All member batches green |
| `IN_PROGRESS` | `PENDING_RELEASE` | Latest increment revision fully green (unified-env builds OK, derived artifacts built, integration tests passed, all member batches mergeable) |
| `PENDING_RELEASE` | `IN_PROGRESS` | Rollback when something turns red |
| `PENDING_RELEASE` | `RELEASED` | Release decision (see Part 3); increment archived read-only |
| any non-terminal | `DROPPED` | Member batches become unassigned (deferred, still open) |

- `PENDING_RELEASE` is fully frozen: no changes at all, except rollback or drop.
- **Deferring** a batch = removing it from the increment (allowed in `COLLECTING` and, as an exception, in `IN_PROGRESS`); the batch itself stays open and unassigned.
- **Releng** (release engineers/managers) own all phase transitions, exception approval, and release.

## Part 2 - Revisions and Serialized Pipeline (future ADR-0014)
- **Unified environment:** base project content at a pinned ref (the submodule pointer set) plus member batch overrides. Image definitions are ordinary packages, captured by the fingerprint.
- **Fingerprint:** deterministic SHA-256 over sorted member batch fingerprints + pinned base project ref + increment name (ADR-0008 format rules). Revisions are immutable; any material change (membership edit, member batch advancing, base re-pin) creates a new revision. Each revision pins the base at its creation time.
- **Draft + debounce:** a new revision starts in draft with a debounce countdown. Expensive operations - unified-env package rebuilds, derived-artifact builds, integration tests, review instantiation - start only when the countdown elapses, on manual trigger, or at a targeted datetime. The countdown can be disabled (purely manual).
- **Serialized processing:** each increment processes one revision at a time; newer revisions queue behind the in-flight one. Superseded results are retained but marked stale. Different increments run concurrently.
- **Hard freeze:** in `IN_PROGRESS` and `PENDING_RELEASE`, any change that would create a new revision/fingerprint requires an explicit releng action (exception). No batch additions in `IN_PROGRESS`; only removals and releng-approved PR changes. An approved change creates a new queued revision and re-runs the pipeline.
- **Increment-level reviews:** the mechanism reuses the ADR-0009/0012 review-config machinery on increment revisions; whether configs are actually defined is TBD with QA.

## Part 3 - Release Action (future ADR-0015)
- **Explicit release decision** by releng, bound to a specific green increment revision, taken from `PENDING_RELEASE`.
- **Procedure:**
  1. Each changed package is merged into its mainline. Safe because of the package-uniqueness invariant (no two member batches touch the same package).
  2. The service generates a single commit in the project repository updating all package references (submodule pointers).
  3. The whole operation is atomic at compose scale (all package merges + reference commit land together or not at all). Mechanism out of scope here - dedicated follow-up ADR (direction: two-phase stage-then-commit).
- For projects whose merge floor reaches `compose`, the compose release is the only merge path (no PR or batch merges outside it).
- **Merge guard:** the base must still match the pinned ref of the released revision (ADR-0008); otherwise the release is refused.
- **Postcondition:** increment `RELEASED`, archived read-only; the release record binds to the increment revision.
- **DROPPED:** releng action from any non-terminal state; member batches unassigned; no release record.

## Open Items and Assumptions
- Compose lifecycle transitions (permitted transitions + gates): dedicated ADR to be written after ADR-0014/0015 settle.
- Compose-scale atomic release mechanism (direction: two-phase stage-then-commit): dedicated ADR to be written later.
- Emergency updates (EMUs): fast-tracked changes may invalidate other open increments - via merge conflicts with their member batches, or by forcing derived-artifact rebuilds when the EMU affects packages included in ISOs/containers. Handling (invalidation signaling, forced re-pinning, rebuild triggering) requires separate technical clarification; out of scope here.
- `release_date` migration: candidate to move from staging batch to product increment (verify whether batches released standalone still need their own).
- `embargo_date`: candidate to move from staging batch to individual package PRs; verify with security team.
- Increment-level human review configs: TBD with QA and other teams.
- Base-drift protection: a drifted image definition would most likely surface as a merge conflict; whether an additional guard layer is needed is undecided.
- Out of scope: automation that auto-assigns newly-green batches to the closest open increment (earliest `release_date`). The data model supports it (date fields + exclusive membership).
- Build backend can compose the unified environment from a pinned base plus batch overrides and build derived artifacts from it.
