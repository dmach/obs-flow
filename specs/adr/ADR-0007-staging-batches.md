---
id: ADR-0007
date: 2026-10-01
status: proposed
agreed_by: []
---

# ADR-0007: Staging Batches for Integration Testing

## Context
Merging interdependent PRs individually risks breaking builds. We need to group PRs, test integration, and merge atomically.

## Decision
Introduce **Staging Batches**:
1. **Opt-in:** Projects can require staging or allow direct PR merges.
2. **Aggregation:** Groups multiple PRs targeting the same project.
3. **OBS Integration:** Creates a unified staging environment in OBS.
4. **Lifecycle:** Batches have their own builds, tests, and reviews.
5. **Atomic Merge:** All PRs in the batch merge simultaneously.

## Consequences

**Positive:**
- Prevents breakage by testing interdependent PRs together.
- Saves CI resources by consolidating integration runs.
- Gives release managers clear oversight of aggregate changes.
- Flexible: simpler projects can bypass staging entirely.

**Negative:**
- Adds an extra lifecycle layer above individual PRs.

## Considered Options
- **Direct Merging with Reverts:** Rejected because it destabilizes main branch and reverts violate fast-forward policy.

## Assumptions
OBS can build package changes from Git refs in an isolated project before merging.
