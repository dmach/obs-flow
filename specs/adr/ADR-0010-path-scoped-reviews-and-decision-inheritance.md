---
id: ADR-0010
date: 2026-10-01
status: proposed
agreed_by: []
---

# ADR-0010: Path-Scoped Reviews and Decision Inheritance

## Context
PRs touch diverse files (code, metadata), each needing different review teams.
Resetting all reviews to `PENDING` on push (ADR-0009) creates fatigue and re-reviews of untouched files,
but each revision still needs a complete audit trail.
Furthermore, we often need to review "everything except X" (e.g., ignoring changelogs or documentation), which requires negative matching capabilities.

## Decision
Implement path scoping and decision inheritance:
1. **Scopes:** Globally-defined categories, identified by their name (e.g., `code`, `patchinfo`), defined by a list of `include_globs` and `exclude_globs`.
   A file is considered in-scope if it matches at least one include glob AND does not match any exclude glob.
   A global scope (e.g., `include_globs=["**/*"]`, `exclude_globs=[]`) matches all files.
   Review configs reference scopes rather than globs directly.
2. **Evaluation States:**
   - **`SKIPPED`:** No files match the config's referenced scopes. Terminal - never inherited.
   - **`PENDING`:** Scoped file changed, touched for the first time, or scope of the review changed.
   - **Inherited:** Scoped file unchanged and its source (previous valid revision, same config + scope) is in-scope.
     The decision is copied from the source and stored on this revision; `is_inherited` marks it. Manual edits clear inheritance.
3. **Forward propagation (late arrivals):**
   Every revision stores its own decision (self-contained, per ADR-0008/0009).
   When a review is decided at revision N, the decision propagates forward to every later revision with `is_inherited = True`,
   storing it on each, and stops at the first revision where `is_inherited = False`.
4. **Scope changes:** Scope identity is stable; globs may change without being detected (no pattern versioning).
   Inheritance follows scope identity only - a changed identity yields a fresh `PENDING`.

## Consequences

**Positive:**
- Complete audit trail: every revision explicitly documents all review requirements.
- Eliminates fatigue: reviewers aren't notified for untouched files or carried-forward approvals.
- Smooth release workflow: metadata updates don't block on re-reviewing untouched code.
- Clear provenance: the `is_inherited` flag transparently distinguishes automated carry-overs from explicit reviews.
- Flexible matching: explicit exclude globs make it easy to ignore specific files (like changelogs) without writing complex positive globs.

**Negative:**
- Persists records even for skipped reviews (needed for audit integrity).
- Requires detecting file changes across revisions.
- Scopes are global; all projects share the same globs per scope.
- Forward propagation adds cascade logic: on each decision, walk forward and stop at the first non-inherited review.

## Considered Options
- **Omit Untouched Reviews:** Rejected because it leaves ambiguous audit gaps.
- **Unconditional Reset:** Rejected because it causes severe review fatigue.
- **Per-config globs:** Rejected because it duplicates globs across review configs; global scopes define them once.
- **Single glob list with negation (e.g., `!CHANGELOG.md`):** Rejected because explicit `include_globs` and `exclude_globs` fields are easier to validate, manage in the database, and present in a UI.

## Assumptions
Git backend provides reliable APIs to detect changed files across revisions.
