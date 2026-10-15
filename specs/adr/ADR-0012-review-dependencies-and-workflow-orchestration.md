---
id: ADR-0012
date: 2026-10-01
status: active
agreed_by: []
---

# ADR-0012: Review Dependencies and Workflow Orchestration

## Context
Reviews often follow a strict hierarchy: automated checks (builds, lints, security scans) must pass before maintainers review code,
and maintainer sign-off should precede QA or release manager approval. Without dependency orchestration,
all reviews immediately instantiate as `PENDING` (ADR-0009), cluttering queues and wasting human time on changes that aren't technically ready.

## Decision
We implement a directed acyclic graph (DAG) of review dependencies:

1. **`WAITING` State:** Instantiated reviews whose upstream prerequisites are unresolved enter the `WAITING` state.
2. **Dependency Resolution:**
   - Templates define dependencies via `depends_on`.
   - On instantiation, reviews with pending prerequisites start as `WAITING`.
     Reviews with no dependencies (or whose dependencies are `SKIPPED`/inherited) start as `PENDING`.
3. **Queue Visibility & Early Actions:** By default, `WAITING` reviews do not notify reviewers or appear in primary queues.
   However, reviewers can still view and proactively approve a `WAITING` review if needed (e.g., for hotfixes), unblocking that gate immediately.
4. **Cascading Unblocking:** When an upstream review resolves (approved, skipped, or inherited), the system checks downstream dependencies.
   If all prerequisites are satisfied, the downstream review transitions from `WAITING` to `PENDING`, notifying reviewers and appearing in active backlogs.

## Consequences

**Positive:**
- Protects reviewer bandwidth: prevents humans from evaluating broken or unverified packages.
- Automates handoffs across sequential review stages.
- Flexible: allows authorized users to review out of order for urgent fixes.

**Negative:**
- Adds cascading transition logic to the backend state machine.

## Considered Options

- **Immediate `PENDING` with Informal Rules:** Rely on humans to manually check build statuses first.
  Rejected because it causes high backlog noise and wasted review effort on failing builds.
- **Strictly Blocking Actions:** Forbid reviewers from acting on `WAITING` reviews entirely.
  Rejected because it's too rigid; prevents teams from fast-tracking hotfixes when necessary.

## Assumptions
Assumes review dependency structures form a valid DAG without circular dependencies, enforced during template configuration.
