---
id: ADR-0002
date: 2026-09-29
status: active
agreed_by: [dmach]
---

# ADR-0002: Backend Stack with Django and django-bolt

## Context
The backend requires LTS stability, a mature ORM with migrations, server-rendered HTML, and high-throughput asynchronous (ASGI) execution.
Standard Django is predominantly synchronous, while async frameworks like FastAPI lack Django's ORM maturity and LTS guarantees.

## Decision
We chose Django for ORM, migrations, and templates, paired with `django-bolt` for the API routing layer under ASGI.

## Consequences

**Positive:**
- Combines Django's mature tooling with high-throughput routing.
- Serves both web UI and API endpoints from a single runtime.

**Negative:**
- Thread-pool bridging for synchronous ORM operations requires monitoring under load.
- `django-bolt` has a smaller community and shorter history than alternatives.

## Considered Options

- **FastAPI with SQLAlchemy** - Rejected due to lack of LTS releases and built-in migrations.
- **Django with Django REST Framework (DRF)** - Rejected due to synchronous overhead.
- **Django with Django Ninja** - Rejected due to lower throughput compared to `django-bolt`.

## Assumptions
- Dispatched ORM queries remain performant in ASGI thread pools.
- `django-bolt` remains maintained and stable.

Revisit this decision if Django ORM provides native async without thread-pool overhead.
