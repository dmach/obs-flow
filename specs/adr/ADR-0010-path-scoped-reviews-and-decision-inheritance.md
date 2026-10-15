---
id: ADR-0010
date: 2026-10-01
status: active
agreed_by: []
---

# ADR-0010: Path-Scoped Reviews and Decision Inheritance

## Context
Pull requests often touch both code and release metadata (e.g., `_patchinfo`), each requiring different review teams (maintainers, QA, security).
Blindly cloning all templates into `PENDING` on each revision (ADR-0009) creates two major issues:
1. It requests reviews from teams whose files weren't touched.
2. Minor metadata tweaks force code reviewers to re-review unchanged code, causing fatigue and delays.

Every revision still needs a complete, self-contained audit trail showing the status of all requirements.

## Decision
We implement path-scoped review evaluation and decision inheritance across revisions:

1. **Path Scopes:** Templates map to specific path patterns (e.g., `code`, `patchinfo`).
   Global templates (security, lead maintainers) match all files.
2. **Complete Snapshots:** Every applicable template is instantiated on every revision, but its initial state is evaluated dynamically:
   - **`SKIPPED`:** If the PR touches no files matching the template's scope.
   - **`PENDING`:** If the scope's files were modified in the new revision (or on first touch), the review requires an active decision.
   - **Inheritance:** If a scope's files haven't changed since the previous revision, the prior decision (state, actor, justification) is copied,
     and **`is_inherited`** is set to `True`. Subsequent manual actions reset this flag to `False`.

## Consequences

**Positive:**
- Complete audit trail: every revision explicitly documents all review requirements.
- Eliminates fatigue: reviewers aren't notified for untouched files or carried-forward approvals.
- Smooth release workflow: metadata updates don't block on re-reviewing untouched code.
- Clear provenance: the `is_inherited` flag transparently distinguishes automated carry-overs from active reviews.

**Negative:**
- Persists records even for skipped reviews (needed for audit integrity).
- Requires diffing files across branches and between consecutive revisions.

## Considered Options

- **Omit Reviews for Untouched Scopes:** Skip creating records entirely.
  Rejected because it leaves ambiguous gaps in the audit trail (unclear if a check was skipped or simply omitted).
- **Unconditional Reset on Push:** Mark all reviews `PENDING` on every revision.
  Rejected because it creates severe review fatigue and delays releases for trivial follow-ups.
- **Hardcoded Database Scopes:** Fix scopes in the database schema.
  Rejected because it's inflexible; scopes must dynamically accommodate docs, legal notices, and vendor paths.

## Assumptions
Assumes the Git backend provides reliable APIs to diff changed files across pull requests and individual commits.
