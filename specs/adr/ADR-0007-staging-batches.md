---
id: ADR-0007
date: 2026-10-01
status: active
agreed_by: []
---

# ADR-0007: Staging Batches for Integration Testing

## Context
In Linux distribution workflows, packages are often tightly interdependent.
Merging pull requests individually into fast-moving targets (like `openSUSE:Factory`)
risks breaking builds if related packages aren't updated together.

We need a way to group interdependent PRs, test their combined integration, and merge them atomically once verified.

## Decision
We introduce **Staging Batches** to manage integration testing and atomic merges:

1. **Opt-in per Project:** Projects can require staging batches or allow direct PR merges.
   - *With Staging:* PRs must pass through a Staging Batch before merging.
   - *Without Staging:* PRs are evaluated and merged individually once their checks pass.
2. **Aggregation:** A Staging Batch groups multiple package- and project-level PRs targeting the same project.
3. **OBS Integration:** The batch creates a unified staging environment in OBS to test the aggregate changes.
4. **Lifecycle & Reviews:** Batches have their own lifecycle, including OBS builds, automated tests, and human reviews.
5. **Atomic Merge:** Once fully approved and verified, all PRs in the batch are merged simultaneously into their target branches.

## Consequences

**Positive:**
- Prevents target branch breakage by testing interdependent PRs together.
- Saves CI resources by consolidating integration runs.
- Gives release managers clear oversight of aggregate changes.
- Flexible: simpler projects can bypass staging entirely.

**Negative:**
- Adds an extra lifecycle layer above individual PRs.
- Requires conflict resolution for PRs within the same batch.

## Considered Options

- **Direct Merging with Reverts:** Merge PRs immediately and revert if tests fail.
  Rejected because it destabilizes the main branch and disrupts downstream consumers.

## Assumptions
Assumes OBS can build package changes from Git refs within an isolated staging project before merging into the target.
