---
id: ADR-0003
date: 2026-09-30
status: active
agreed_by: []
---

# ADR-0003: RPC-Style API Design

## Context
Backend operations orchestrate multi-step packaging workflows.
These actions do not map cleanly to standard CRUD operations on REST resources.
Forcing them into HTTP verbs creates ambiguous endpoints and artificial resources.
Additionally, operations frequently modify multiple database models within a single atomic transaction.

## Decision
We adopted an RPC-style API over HTTP POST for all API endpoints.
Each endpoint represents an explicit action taking a typed request payload and returning a typed response payload.

## Consequences

**Positive:**
- Explicit operation contracts without ambiguous verb mappings.
- Simplifies client integration to uniform POST requests.
- Eases schema evolution through additive action endpoints.
- Simplifies wrapping multi-model operations in atomic database transactions.

**Negative:**
- Deviates from standard REST conventions.
- Prevents the use of standard HTTP GET caching.

## Considered Options

- **RESTful API Design** - Resource-oriented verbs.
  Rejected due to friction mapping non-CRUD actions and managing multi-entity transactions.
- **JSON-RPC 2.0** - Single-endpoint RPC protocol.
  Rejected because multiplexing requests through a single URL complicates edge routing, WAF inspection, access logging, and `django-bolt` status code handling.
- **GraphQL** - Flexible query interface.
  Rejected due to client/server complexity when only fixed operational actions are required.

## Assumptions
- HTTP-level response caching is not a current requirement.

Revisit this decision if read-heavy operations justify dedicated GET endpoints.
