---
id: ADR-0006
date: 2026-09-30
status: active
agreed_by: [dmach]
---

# ADR-0006: Server-Driven UI with HTMX

## Context
The web interface requires interactivity without full-page reloads.
Node.js/npm frontend stacks introduce dependency churn, security audit overhead, and a separate build pipeline.

## Decision
We chose HTMX to drive interactivity via server-rendered HTML fragments, avoiding npm and client-side JavaScript frameworks entirely.

## Consequences

**Positive:**
- Keeps repository tooling purely Python-focused.
- Eliminates npm dependency maintenance and reduces frontend attack surface.
- Unifies presentation and application logic within Django.

**Negative:**
- Complex client-side state and offline workflows are impractical to implement with HTMX.
- Interactivity depends on network round-trips and backend latency.

## Considered Options

- **SPA Frameworks (React, Vue, etc.)** - Rejected due to dependency rot and tooling complexity.
- **Vanilla JavaScript DOM Manipulation** - Rejected as unmaintainable across complex views.
- **Pure Multi-Page Application (MPA)** - Rejected due to poor UX during dialogs and inline filtering.

## Assumptions
- Interface requirements remain document- and workflow-driven.
- Client-to-server latency remains low.

Revisit this decision if offline workflows or complex client-side editing become necessary.
