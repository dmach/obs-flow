---
id: ADR-0009
date: 2026-10-01
status: active
agreed_by: []
---

# ADR-0009: Creating Reviews from Review Configs

> **Status Update (Iterative Evolution):**
> While this record defines the baseline rule that reviews instantiate in a `PENDING` state on every revision, subsequent ADRs iteratively refine this behavior:
> - **ADR-0010** introduces path scoping (`SKIPPED` state) and decision inheritance.
> - **ADR-0011** defers review instantiation entirely while revisions are in draft mode.
> - **ADR-0012** introduces the `WAITING` state for reviews blocked on upstream dependencies.

## Context
Pull requests and staging batches require sign-offs from various roles (users, groups, or maintainers).
Per ADR-0008, every push or metadata change creates an immutable revision. When a revision is created,
the system must determine which reviews are required and instantiate concrete review records strictly bound to that snapshot.

## Decision
We use declarative review configurations (`ReviewConfig`) to instantiate review records on each revision:

1. **Review Configs:** Review configurations stored in the database (`ReviewConfig` model), mapped to projects.
   They specify type (`project`, `package`, or `staging`) that determine if the reviews apply to project PRs, package PRs or staging batches
   of the related project and assign reviewers (users, groups, or dynamic roles like maintainers).
2. **Per-Revision Instantiation:** When a revision is created, matching Review Configs are cloned into discrete review records
   bound to that specific revision with an initial `PENDING` state. Reviews are strictly revision-scoped and never shared across revisions.
3. **Actor Tracking:** Review Configs define policy (who *should* review), while review records capture execution (who *actually* reviewed).
   Recording the explicit `actor` allows group members to fulfill team reviews or authorized users to submit administrative overrides.

## Consequences

**Positive:**
- Declarative and reproducible: required reviews are transparently derived from configuration.
- Isolated audit trail: review decisions strictly tie to a specific revision without implicitly leaking across pushes.
- Consistent architecture: uses the same mechanism across project PRs, package PRs, and staging batches.

**Negative:**
- Creates multiple database records per revision on each push.
- Blindly cloning Review Configs resets reviews to `PENDING`, necessitating subsequent inheritance rules to avoid reviewer fatigue.

## Considered Options

- **Mutable PR-Level Reviews:** Attach reviews directly to the PR and reset states on push.
  Rejected because it violates revision immutability (ADR-0008) and destroys historical decisions.
- **Dynamic Calculation without Records:** Compute review statuses on-the-fly without database records until approved.
  Rejected because it prevents tracking review queues, locking reviews to assignees, or auditing state transitions.

## Assumptions
Assumes projects maintain a modest number of Review Configs (typically under 20), keeping per-revision instantiation lightweight.
