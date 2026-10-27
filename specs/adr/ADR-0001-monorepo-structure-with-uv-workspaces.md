---
id: ADR-0001
date: 2026-09-29
status: active
agreed_by: [dmach]
---

# ADR-0001: Monorepo Structure with uv Workspaces

## Context
The project consists of multiple interconnected components (client, CLI, server, shared models) that evolve closely together.
Separate repositories would add overhead to cross-repo versioning, pull requests, dependency pinning, and end-to-end testing.

## Decision
We chose a monorepo structure managed with `uv` workspaces.

## Consequences

**Positive:**
- Single source of truth with atomic commits across packages.
- Local dependency resolution without intermediate publishing.
- Unified CI, testing, and release tagging.

**Negative:**
- Shared tagging couples release cycles across all packages.

## Considered Options

- **Multi-Repository Setup** - Separate git repositories per package.
  Rejected due to cumbersome PR coordination and cross-repo testing.

## Assumptions
- `uv` remains maintained and supported by our CI/deployment targets.

Revisit this decision if team autonomy requires independent release lifecycles.
