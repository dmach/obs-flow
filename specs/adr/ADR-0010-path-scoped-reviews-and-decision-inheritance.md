---
id: ADR-0010
date: 2026-10-01
status: proposed
agreed_by: []
---

# ADR-0010: Path-Scoped Reviews and Decision Inheritance

## Context
Resetting all reviews to `PENDING` on push (ADR-0009) causes review fatigue for untouched files.
We need to scope reviews to specific paths (including negative matches like "ignore changelogs")
and inherit decisions for unchanged files to maintain a complete audit trail without redundant work.

## Decision
We chose to implement path scoping and decision inheritance:
1. **Scopes:** Define global categories (e.g., `code`) using `include_globs` and `exclude_globs`.
   A file matches if it hits an include glob and no exclude globs.
   Review configs reference these scopes.
   Staging batches evaluate the union of all changed files across included PR revisions.
2. **Evaluation States:**
   - **`SKIPPED`:** No files match the scope. Terminal.
   - **`PENDING`:** Scoped file changed, is new, or the scope identity changed.
   - **Inherited:** Scoped file unchanged. Decision is copied from the previous valid revision and marked `is_inherited`. Manual edits clear this.
3. **Forward Propagation:** Decisions propagate forward to subsequent revisions with `is_inherited = True`, stopping at the first non-inherited review (`is_inherited = False`).
4. **Scope Identity:** Inheritance relies on stable scope identity (name), not glob pattern versions. A changed identity yields a fresh `PENDING`.

## Consequences

**Positive:**
- Complete audit trail for every revision.
- Eliminates review fatigue for untouched files.
- Flexible matching via explicit exclude globs.

**Negative:**
- Persists records for skipped reviews.
- Requires detecting file changes across revisions.
- Scopes are global and shared across projects.
- Adds cascade logic for forward propagation.

## Considered Options
- **Omit Untouched Reviews** - Creates reviews only when matching files change.
  Rejected because it leaves audit gaps.
- **Unconditional Reset** - Resets all reviews to `PENDING` on every push.
  Rejected because it causes review fatigue.
- **Per-Config Globs** - Defines file matching rules directly on each review config.
  Rejected because it duplicates globs; global scopes are DRY.
- **Single Glob List with Negation** - Uses syntax prefixes like `!` in a single list instead of separate include/exclude fields.
  Rejected because explicit include/exclude fields are easier to manage.

## Assumptions
Git backend provides reliable APIs to detect changed files across revisions.
Revisit Decision #4 if glob changes frequently cause issues. Currently assuming that review instances remain valid even if globs of their review scopes changed.
