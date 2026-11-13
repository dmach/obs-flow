---
id: ADR-0012
date: 2026-10-01
status: proposed
agreed_by: []
---

# ADR-0012: Review Dependencies and Workflow Orchestration

## Context
Reviews follow hierarchies (e.g., automated checks before human review).
Without dependencies, all reviews instantiate as `PENDING` (ADR-0009), wasting human effort on unverified changes.

## Decision
We chose to implement a directed acyclic graph (DAG) of review dependencies:
1. **`WAITING` State:** Reviews with unmet prerequisites enter `WAITING`.
2. **Resolution:** Reviews start as `WAITING` if upstream dependencies are unresolved; otherwise `PENDING`.
3. **Queue Visibility:** `WAITING` reviews do not notify or show in primary backlogs, but can be manually unblocked/approved early.
4. **Cascading Transitions:** Satisfying an upstream review transitions downstream dependents from `WAITING` to `PENDING`.

## Consequences

**Positive:**
- Protects reviewer bandwidth: prevents humans from evaluating broken or unverified packages.
- Automates handoffs across sequential review stages.
- Flexible: allows authorized users to review out of order for urgent fixes.

**Negative:**
- Adds cascading transition logic to the backend service.

## Considered Options
- **Immediate `PENDING`** - Sets all instantiated reviews to `PENDING` without dependency ordering.
  Rejected because it causes unnecessary notification volume and wastes review effort on failing builds.
- **Strictly Blocking** - Enforces rigid prerequisites with no ability to bypass or review out of order.
  Rejected because waiting until all dependencies are resolved prevents fast-tracking hotfixes when necessary.

## Assumptions
Dependency graph is an acyclic DAG validated on review config.
