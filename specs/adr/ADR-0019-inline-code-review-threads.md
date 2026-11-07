---
id: ADR-0019
date: 2026-11-07
status: accepted
agreed_by: []
---

# ADR-0019: Inline Code Review Threads and Revision Binding

## Context
Pull requests evolve across multiple revisions as authors push new commits or amend patchsets (ADR-0008). Reviewers inspect diffs and comment on specific file paths and line numbers. Two concurrency and lifecycle challenges exist:
1. **Concurrent revision updates:** A reviewer may spend minutes writing an inline comment on Revision 1 while the author simultaneously pushes Revision 2. If comment creation relies on implicit "latest revision", the comment attaches to unintended code or fails.
2. **Comment obsolescence vs. audit trail:** Discarding comments when a new revision arrives destroys the review trail, whereas naïvely anchoring comments only to the latest code breaks line references when lines shift.

## Decision
We chose to decouple the long-term conversational lifecycle from point-in-time code anchoring by introducing revision-bound review threads:

1. **Explicit Revision Context at Submission:**
   - Every request to add an inline code comment must explicitly provide the `revision_id` (or `revision_number`) being viewed.
   - The server validates that the specified file path and line number exist within that revision snapshot before persisting.

2. **Thread Anchoring & Structure:**
   - `ReviewThread` belongs to the `PullRequest` aggregate root (persisting across the entire PR lifecycle).
   - `ReviewThread` permanently records `original_revision`, `original_commit_sha`, `path`, and `line_number`.
   - Subsequent replies within the thread append to the thread without altering the original anchoring metadata.

3. **Multi-Revision Presentation Lifecycle:**
   - **Current:** If the commented hunk remains untouched between `original_revision` and the PR's latest revision, the thread ports forward and displays expanded inline on the latest diff.
   - **Outdated:** If subsequent revisions modified or deleted the target lines, the thread is classified as outdated. It renders collapsed under an `<details><summary>Outdated comment on Rev N</summary>...</details>` element in the diff view and remains prominently visible in the PR Overview activity timeline.
   - **Resolved:** A thread may be marked resolved by either the author or reviewer once addressed, hiding it from default active review blockers.

## Consequences

**Positive:**
- **Concurrency-safe:** Reviewers commenting on an older revision never corrupt newer revisions or attach comments to the wrong lines.
- **Zero comment loss:** All discussions, feedback, and replies remain accessible regardless of how many times a PR is rebased or updated.
- **Clear verification loop:** Reviewers can easily verify whether their comments on Rev 1 were addressed in Rev 2 by comparing the outdated thread with the new diff.

**Negative:**
- Determining whether an older thread is "Outdated" vs. "Current" requires computing a git diff between `original_revision` and the latest revision for the target path.

## Considered Options
- **Anchor only to latest revision (reject comments on old revisions):**
  Rejected because race conditions between a reviewer submitting feedback and an author pushing updates cause frustrating failed submissions.
- **Discard comments upon new revision:**
  Rejected because it erases review history and makes verification impossible.
- **Anchor strictly to revision without porting forward:**
  Rejected because reviewers on the latest revision would not see unresolved open comments unless they switched back to historical revision views.

## Assumptions
- `PullRequestRevision` models are immutable and retain valid `head_sha` and `base_sha` references.
- Git repository contains all commit objects corresponding to the PR revisions.
