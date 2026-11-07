---
id: ADR-0015
date: 2026-11-06
status: proposed
agreed_by: []
---

# ADR-0015: Hierarchical Entity URLs and Scoped Pull Request Numbers

## Context
ADR-0013 established an org-based native git forge where projects and packages are first-class domain entities.
Previously, web routes and pull requests used flat, global database identifiers (e.g., `/pull-requests/<id>/`).
This had two significant drawbacks:
1. URLs were non-descriptive and disconnected from the owning project or package context.
2. Pull requests exposed internal auto-incrementing database primary keys rather than familiar, repository-scoped sequence numbers (e.g., `#1`, `#2`).
ADR-0013 explicitly flagged pull request identity scoping as an unresolved decision.

## Decision
We chose hierarchical, entity-scoped URL routing and scoped pull request numbering:

1. **Hierarchical entity URLs:**
   All web routes for projects and packages follow semantic, hierarchical paths based on human-readable entity names:
   - Projects: `/projects/<project_name>/...`
   - Packages: `/packages/<project_name>/<package_name>/...`

2. **Scoped pull request routes:**
   Pull requests are routed directly under their target project or package:
   - Project pull requests: `/projects/<project_name>/pull-requests/<number>/...`
   - Package pull requests: `/packages/<project_name>/<package_name>/pull-requests/<number>/...`

3. **Per-entity sequential numbers:**
   Pull request identity is scoped to the target entity via a sequential integer `number` field starting at 1 for each project or package. Internal database primary keys are no longer exposed in user-facing URLs or formatted references (`target_owner/target_repo#number`).

4. **Global pull request views:**
   Cross-project aggregation views remain available at `/pull-requests/` for global dashboards, filtering, and bulk operations.

## Consequences

**Positive:**
- **Intuitive URLs:** URLs mirror the domain structure and match user expectations established by modern git forges.
- **Human-readable references:** Issues, changelogs, and discussions reference pull requests via clean, scoped identifiers like `curl#12`.
- **Contextual navigation:** Users browsing a pull request remain situated within the navigation and sub-navbar of the target project or package.

**Negative:**
- **Composite key routing:** Resolving a pull request route requires looking up both the target entity and the scoped number rather than a single primary key lookup.
- **Sequence coordination:** Generating sequential numbers per entity requires atomic counter incrementing or database row locking during pull request creation.

## Considered Options

- **Global pull request numbers across the entire instance:**
  Rejected because global IDs appear disjointed from individual repositories and leak total system activity.
- **Flat unnested URLs (`/pull-requests/<id>`):**
  Rejected because it strips away project context from the browser address bar and breadcrumbs.
- **Per-repository counter stored in git refnotes:**
  Rejected because the database is authoritative for domain entities per ADR-0013.

## Assumptions
- Project and package names are URL-safe or properly percent-encoded in routes.
- The volume of pull requests per project or package does not cause concurrency bottlenecks during sequential number assignment.

Revisit this decision if multi-tenant partitioning requires different URL prefixing schemes or if distributed non-blocking ID generation (e.g., UUIDv7) is adopted.
