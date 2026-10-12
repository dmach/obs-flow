---
id: ADR-0004
date: 2026-09-30
status: active
agreed_by: []
---

# ADR-0004: Shared Domain Models Using msgspec

## Context
The server, client, and CLI must exchange structured payloads across API boundaries.
Because `django-bolt` uses `msgspec`, maintaining independent models in the client would cause duplication, schema drift, and contract mismatches.
The system also requires clear evolution rules to prevent backend changes from breaking older clients.

## Decision
We define all DTOs and API schemas once in a shared package using `msgspec`, reused directly by both server and client.

Evolution rules:
- New request fields must define default values.
- Unknown fields are ignored during decoding.
- Breaking changes require versioned endpoint paths or new RPC actions.

## Consequences

**Positive:**
- Eliminates schema duplication and drift across workspace packages.
- Supports additive schema evolution across client versions.
- High-performance encoding, decoding, and validation via `msgspec`.
- Uniform static typing across client and server.

**Negative:**
- Couples client and server to Python and `msgspec`.
- Schema breaking changes require coordinated releases or explicit path versioning.

## Considered Options

- **Independent Client Models (Pydantic / Dataclasses)** - Re-declared client schemas.
  Rejected due to duplication and drift without solving versioning.
- **Code Generation from OpenAPI/JSON Schema** - Exported schema generation.
  Rejected as redundant overhead within a unified Python monorepo.

## Assumptions
- Shared schemas retain tolerant decoding of unknown fields.
- The primary client remains a Python package in the monorepo.

Revisit this decision if multi-language client support requires language-neutral schema definitions.
