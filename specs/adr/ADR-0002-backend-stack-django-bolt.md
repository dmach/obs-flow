---
id: ADR-0002
date: 2026-09-29
status: active
agreed_by: []
---

# ADR-0002: Backend Stack with Django and django-bolt

## Context
The backend (`obs-flow-server`) orchestrates packaging workflows and provides API + WebUI. This requires:
- LTS stability and predictable upgrade cycles.
- A mature relational ORM with transactional integrity and migrations.
- Co-located server-rendered HTML views and API endpoints.
- High-throughput asynchronous (ASGI) execution.

Standard Django is predominantly synchronous with heavy REST framework serialization.
Async frameworks like FastAPI lack Django's ORM maturity, migrations, and LTS guarantees.

## Decision
We chose Django for ORM modeling, migrations, and template rendering, paired with `django-bolt` for the API routing layer.
The service runs under ASGI, bridging synchronous ORM calls asynchronously into the event loop and leveraging `msgspec` for serialization.

## Consequences

**Positive:**
- Combines Django's ORM, migration tooling, and template engine with high-throughput routing.
- Minimizes serialization overhead via `django-bolt` and `msgspec`.
- Serves both web WebUI and API endpoints from a single runtime.

**Negative:**
- Thread-pool bridging for synchronous ORM operations requires careful monitoring under load.
- `django-bolt` has a smaller community and shorter history than Django Rest Framework or Django Ninja.

## Considered Options

- **FastAPI with SQLAlchemy** - Async framework with SQLAlchemy.
  Rejected due to lack of LTS releases, built-in migrations, and native template tooling.
- **Django with Django REST Framework (DRF)** - Standard Django REST stack.
  Rejected due to synchronous overhead and lower throughput.
- **Django with Django Ninja** - Async Django API framework.
  Rejected due to lower throughput compared to `django-bolt`.

## Assumptions
- `django-bolt` maintains compatibility with supported Django and Python versions.
- Dispatched ORM queries remain performant in ASGI thread pools.

Revisit this decision if Django ORM provides native async without thread-pool overhead or if pool contention creates a bottleneck.
