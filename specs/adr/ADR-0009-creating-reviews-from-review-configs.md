---
id: ADR-0009
date: 2026-10-01
status: proposed
agreed_by: []
---

# ADR-0009: Creating Reviews from Review Configs

## Context
Revisions are immutable (ADR-0008).
The system must determine required reviews and instantiate concrete records bound to each revision snapshot.

## Decision
Use declarative configurations (`ReviewConfig`) to instantiate review records:
1. **Review Configs:** Stored in DB, mapped to projects. Define type (`project`, `package`, `staging`) and assign reviewers (users, groups, or dynamic roles like maintainers).
2. **Per-Revision Instantiation:** Cloned on revision creation into records starting in `PENDING`. Not shared across revisions.
3. **Actor Tracking:** Configs define policy; records capture execution; Recording `actor` supports group/role fulfillment and overrides.

## Consequences

**Positive:**
- Declarative and reproducible: required reviews are transparently derived from configuration.
- Isolated audit trail: review decisions strictly tie to a specific revision without implicitly leaking across pushes.
- Consistent architecture: uses the same mechanism across project PRs, package PRs, and staging batches.

**Negative:**
- Creates multiple database records per revision on each push.
- Blindly cloning Review Configs resets reviews to `PENDING`, necessitating subsequent inheritance rules to avoid reviewer fatigue.

## Considered Options
- **Mutable PR-Level Reviews:** Rejected because it violates ADR-0008 immutability.
- **Dynamic On-the-Fly Calculation:** Rejected because it prevents tracking review queues, locking reviews to assignees, or auditing state transitions.

## Assumptions
Projects maintain modest review configs (<20), keeping instantiation overhead low.
