---
id: ADR-0003
date: 2026-09-30
status: active
agreed_by: [dmach]
---

# ADR-0003: RPC-Style API Design

## Context
Backend operations orchestrate multi-step workflows that do not map cleanly to standard CRUD operations.
Forcing them into HTTP verbs creates ambiguous endpoints and complicates multi-model atomic transactions.

## Decision
We adopted an RPC-style API over HTTP POST for all API endpoints.
Each endpoint represents an explicit action with typed request and response payloads.

## Consequences

**Positive:**
- Explicit operation contracts without ambiguous verb mappings.
- Simplifies client integration and schema evolution.
- Eases wrapping multi-model operations in atomic transactions.

**Negative:**
- Deviates from standard REST conventions.
- Prevents standard HTTP GET caching.

## Considered Options

- **RESTful API Design** - Rejected due to friction mapping non-CRUD actions.
- **JSON-RPC 2.0** - Rejected because multiplexing requests through a single URL complicates routing and observability.
- **GraphQL** - Rejected due to unnecessary complexity for fixed operational actions.

## Assumptions
- HTTP-level response caching is not a current requirement.

Revisit this decision if read-heavy operations justify dedicated GET endpoints.
