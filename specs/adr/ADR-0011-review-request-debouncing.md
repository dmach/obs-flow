---
id: ADR-0011
date: 2026-10-01
status: active
agreed_by: []
---

# ADR-0011: Review Request Debouncing and Draft Revisions

## Context
Rapid pushes (e.g., fixing typos, minor reworks, or rebases) occur frequently during PR development.
If every push immediately spins up reviews and notifications, it creates significant reviewer fatigue.
We need a way to debounce review requests until the author finishes their updates, while still persisting
immutable revisions (ADR-0008) so CI pipelines have stable anchors for test results.

## Decision
We implement debouncing using revision-level draft states:

1. **Revision-Level Draft State:** The `is_draft` flag is tracked on the `PullRequestRevision`. Every push creates an immutable revision.
2. **Deferred Review Instantiation:**
   - While a revision is in draft mode (`is_draft = True`), **no review records are created**.
   - When transitioning out of draft mode, the system checks if reviews exist.
     If none do, it provisions them (applying ADR-0010 rules).
     Existing reviews are never re-provisioned if a revision toggles draft status.
3. **Debounce Lifecycle & Data Model:** Revisions track an optional `draft_expires_at` timestamp:
   - **Manual Draft:** Created or marked as draft explicitly (`is_draft = True`, `draft_expires_at = null`).
     Stays draft indefinitely across subsequent pushes.
   - **Automatic Debounce:** A new push to a published PR sets `is_draft = True` and `draft_expires_at = now() + timeout` (e.g., 15 mins).
     Subsequent pushes reset this countdown on each new revision.
   - **Auto-Publish:** A background worker monitors for expired timeouts (`draft_expires_at <= now()`)
     and transitions the latest revision to published (`is_draft = False`), provisioning reviews.
     Authors can also manually click "Ready for Review" to publish immediately.

## Consequences

**Positive:**
- Eliminates notification noise during rapid iterations.
- Gives authors clear control over when changes are reviewed.
- Keeps databases lean by avoiding empty `PENDING` records on intermediate pushes.
- Clear history: transparently records which revisions were drafts versus formally published.

**Negative:**
- Adds complexity to revision state and expiration tracking.
- Requires reliable background worker scheduling for timeout expirations.

## Considered Options

- **Immediate Dispatch on Push:** Standard behavior of naive systems.
  Rejected because it causes high notification fatigue for reviewers.
- **Mutable Draft Revisions:** Overwrite draft revisions in place.
  Rejected because it violates ADR-0008 immutability and races with CI test reporters.
- **Garbage-Collecting Drafts:** Delete draft revisions asynchronously.
  Rejected because retaining drafts provides valuable historical context without significant storage overhead.

## Assumptions
Assumes the backend supports reliable background job scheduling or delayed tasks to handle idle timeouts.
