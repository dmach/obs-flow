---
id: ADR-0014
date: 2026-11-26
status: proposed
agreed_by: []
---

# ADR-0014: Increment Revisions and the Serialized Derived-Artifact Pipeline

## Context
A product increment (ADR-0013) unifies the contents of its member staging batches into a single environment where derived artifacts (ISOs, installation images, containers) are built and cross-batch integration tests run. Projects pin packages via git submodules, so the unified environment consists of base project content plus member batch overrides; image definitions are ordinary packages within it.

The content changes constantly: member batches advance, membership is edited, and the base moves. The expensive operations - unified-env package rebuilds, derived-artifact builds, integration tests - must not be triggered on every change, and artifact builds must be serialized so that every tested artifact corresponds to one consistent set of contents.

## Decision
We chose to model increment revisions as immutable snapshots processed through a debounced, serialized pipeline:

1. **Fingerprint:** following ADR-0008, an increment revision is identified by a deterministic SHA-256 over the sorted member batch fingerprints, the pinned base project ref (the submodule pointer set), and the increment name. Each revision pins the base at its creation time.
2. **Immutability:** any material change - membership edit, member batch advancing, base re-pin - creates a new revision; past revisions are immutable.
3. **Draft + debounce:** a new revision starts in draft with a debounce countdown. Expensive operations (unified-env package rebuilds, derived-artifact builds, integration tests, review instantiation) start only when the countdown elapses, on manual trigger, or at a targeted datetime. The countdown can be disabled, making the revision purely manual.
4. **Serialized processing:** each increment processes one revision at a time; newer revisions queue behind the in-flight one. Results of superseded revisions are retained but marked stale. Different increments run concurrently.
5. **Hard freeze:** in `IN_PROGRESS` and `PENDING_RELEASE`, any change that would create a new revision requires an explicit releng action (exception). No batch additions in `IN_PROGRESS`; only removals and releng-approved PR changes. An approved change creates a new queued revision and re-runs the pipeline.
6. **Increment-level reviews:** the mechanism reuses the ADR-0009/0012 review-config machinery on increment revisions; whether configs are actually defined is decided with QA.

## Consequences

**Positive:**
- Deterministic snapshots including base-sourced content such as image definitions.
- Debouncing prevents churn from triggering expensive CI.
- Serialization guarantees every tested artifact matches one consistent content set.
- Audit trail: build, test, and review results attach to specific immutable revisions (ADR-0008).

**Negative:**
- Superseded cycles still consume some CI resources before being marked stale.
- Changes wait behind the in-flight cycle, adding latency near release.
- The hard freeze adds friction for developers whose batches are inside a frozen increment.
- Base re-pinning invalidates the current revision, which can surprise contributors.

## Considered Options
- **Dynamic "live" view** - The increment always reflects current member heads; no revision identity.
  Rejected because test results and releases could not be bound to a snapshot, breaking auditability.
- **Global serialization lock** - Only one increment in the system may build artifacts at a time.
  Rejected because unrelated increments would block each other; per-increment queues give the required coherence where it matters - inside one artifact.
- **Immediate triggering** - Every change immediately rebuilds and retests.
  Rejected because the operations are very expensive and batch churn would dominate CI capacity.
- **Manual refresh only** - New revisions only on explicit request, no automatic pickup.
  Rejected because "artifact contains all latest to-be-released packages" becomes a habit instead of an invariant.

## Assumptions
- The build backend can compose the unified environment from a pinned base plus batch overrides and build derived artifacts from it.
- Derived artifact definitions exist as packages in the project.
- Increment-level human review configs: TBD with QA and other teams.
- Base-drift protection beyond merge conflicts (e.g., a drifted image definition) is undecided; revisit if drift causes undetected bad artifacts.
- Emergency update (EMU) invalidation of open increments is out of scope; revisit when EMU handling is specified.
