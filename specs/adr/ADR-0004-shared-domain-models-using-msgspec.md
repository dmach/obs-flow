---
id: ADR-0004
date: 2026-09-30
status: active
agreed_by: [dmach]
---

# ADR-0004: Shared Domain Models Using msgspec

## Context
The server, client, and CLI must exchange structured payloads.
Maintaining independent models across components causes duplication and schema drift.

## Decision
We define all DTOs and API schemas once in a shared package using `msgspec`, reused directly by both server and client.

## Consequences

**Positive:**
- Eliminates schema duplication and drift.
- High-performance encoding, decoding, and validation.
- Uniform static typing across client and server.

**Negative:**
- Couples client and server to Python and `msgspec`.
- Schema breaking changes require coordinated releases or explicit path versioning.

## Considered Options

- **Independent Client Models** - Rejected due to duplication and drift.
- **Code Generation from OpenAPI/JSON Schema** - Rejected as redundant overhead within a unified Python monorepo.

## Assumptions
- The primary client remains a Python package in the monorepo.
- Shared schemas retain tolerant to decoding unknown fields to support old clients.

Revisit this decision if multi-language client support requires language-neutral schema definitions.
