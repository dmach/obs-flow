---
id: ADR-0006
date: 2026-09-30
status: active
agreed_by: []
---

# ADR-0006: Server-Driven UI with HTMX

## Context
The web interface requires interactive modals, filtering, pagination, and status updates without full-page reloads.
Node.js/npm frontend stacks (e.g., React, Vue) introduce dependency churn, security audit overhead, and a separate JavaScript build pipeline.

## Decision
We chose HTMX to drive interactivity via server-rendered HTML fragments, avoiding npm and client-side JavaScript frameworks entirely.

## Consequences

**Positive:**
- Keeps repository tooling purely Python-focused with no Node.js build step.
- Eliminates npm dependency maintenance and reduces the frontend attack surface.
- Unifies presentation and application logic within Django templates and models.

**Negative:**
- Complex client-side state and offline workflows are impractical to implement with HTMX.
- Interactivity depends on network round-trips and backend latency.
- UI state remains coupled to server HTML generation rather than headless JSON APIs.

## Considered Options

- **SPA Frameworks (React, Angular, Vue, Svelte)** - Component-based client frameworks.
  Rejected due to dependency rot, security maintenance, and tooling complexity.
- **Vanilla JavaScript DOM Manipulation** - Custom native scripts.
  Rejected as unmaintainable across complex dynamic views.
- **Pure Multi-Page Application (MPA)** - Traditional full-page reloads.
  Rejected due to poor UX during dialogs and inline filtering.

## Assumptions
- Interface requirements remain document- and workflow-driven without heavy client-side computing.
- Client-to-server latency remains low.

Revisit this decision if offline workflows or complex canvas-based editing become necessary.
