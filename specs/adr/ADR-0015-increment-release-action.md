---
id: ADR-0015
date: 2026-11-26
status: proposed
agreed_by: []
---

# ADR-0015: The Increment Release Action

## Context
A product increment (ADR-0013) reaches `PENDING_RELEASE` with a fully green increment revision (ADR-0014): unified-env builds OK, derived artifacts built, integration tests passed, all member batches mergeable. All member batches target the same project, whose Git repository pins packages via submodules.

The release must land exactly what was tested: released content must equal tested content, and the record of what was released must bind to a specific increment revision.

## Decision
We chose an explicit, guarded release action:

1. **Explicit decision:** releng releases from `PENDING_RELEASE`, bound to a specific green increment revision. No automatic release on green.
2. **Procedure:**
   1. Each changed package is merged individually into its mainline. This is conflict-free within the increment because of the package-uniqueness invariant (no two member batches touch the same package).
   2. The service generates a single commit in the project repository updating all package references (submodule pointers) atomically.
3. **Merge guard:** following ADR-0008, the base must still match the pinned ref of the released revision; otherwise the release is refused and a new revision must be created and re-tested.
4. **Postcondition:** the increment becomes `RELEASED`, archived read-only; the release record binds to the increment revision.
5. **DROPPED:** releng may drop an increment from any non-terminal state; member batches become unassigned (deferred, still open); no release record is created.

## Consequences

**Positive:**
- Released content equals tested content: the guard plus the atomic reference switch make this a hard invariant.
- Individual package merges preserve per-package history and attribution.
- The single reference commit leaves the project either fully old or fully new - never half-updated at the reference level.
- Complete audit trail: every release names the exact increment revision it shipped.

**Negative:**
- Package merges are not transactional across packages: a mid-sequence failure leaves some package mainlines merged while the reference commit is not yet applied; recovery is re-running the release after fixing the cause.
- Any base movement since pinning blocks the release until a fresh revision is built and tested.
- Adds a service-generated commit type that operators must understand.

## Considered Options
- **Single union merge** - Merge the entire tested union as one Git operation.
  Rejected because packages live in their own repositories pinned by submodules; per-package merges keep package histories linear and attributable, while the single reference commit still provides the atomic switch.
- **Automatic release on green** - Release as soon as the latest revision is fully green.
  Rejected because shipping is a business decision; a human gate is required at this boundary.
- **Sequential batch-level merges** - Merge each member batch as a unit, one after another.
  Rejected because the tested unit of an increment is the union of package states; per-package merges map 1:1 onto that unit and avoid interleaving unrelated packages in shared merge commits.

## Assumptions
- The package-uniqueness invariant (ADR-0013) holds for the released increment.
- The service can generate and push the reference-update commit to the project repository.
- Emergency update (EMU) fast-tracking interactions (invalidation of other open increments, forced rebuilds) are out of scope; revisit when EMU handling is specified.
- Revisit if release units ever need to span multiple projects.
