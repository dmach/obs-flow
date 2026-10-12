---
id: ADR-0001
date: 2026-09-29
status: active
agreed_by: []
---

# ADR-0001: Monorepo Structure with uv Workspaces

## Context
The `obs-flow` project consists of multiple interconnected components:
- `obs-flow-common`: Shared domain models and DTOs.
- `obs-flow-client`: Python client library.
- `obs-flow-cli`: CLI tool.
- `obs-flow-server`: Django orchestration server, API, WebUI.

These components evolve closely together, particularly during schema changes and API additions.
Separate repositories would add overhead to cross-repo versioning, pull requests, dependency pinning, and end-to-end testing.

## Decision
We chose a monorepo structure managed with `uv` workspaces.
Components reside under `packages/`, with inter-dependencies resolved locally via workspace sources.

## Consequences

**Positive:**
- Single source of truth for all components.
- Atomic commits across packages and shared schemas.
- Local dependency resolution without intermediate publishing.
- Unified CI, testing, and single repository-wide release tagging.

**Negative:**
- Shared tagging couples release cycles, requiring synchronized version bumps across all packages even for single-component changes.

## Considered Options

- **Multi-Repository Setup** - Separate git repositories per package.
  Rejected due to cumbersome PR coordination and complex cross-repo testing.

## Assumptions
- `uv` remains maintained and adheres to PEP 517/621.
- All deployment and CI targets support `uv`.

Revisit this decision if repo size or team autonomy requires independent release lifecycles.
