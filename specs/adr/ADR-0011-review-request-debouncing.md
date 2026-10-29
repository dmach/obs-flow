---
id: ADR-0011
date: 2026-10-01
status: proposed
agreed_by: []
---

# ADR-0011: Review Request Debouncing and Draft Revisions

## Context
Rapid pushes create review spam and notification fatigue.
We need to debounce requests until the author finishes, while retaining immutable revisions (ADR-0008) for CI.

## Decision
Use revision-level draft states:
1. **Draft Flag:** `is_draft` is a mutable field attached to the Revision. Revisions remain immutable.
2. **Deferred Provisioning:** No reviews are created while `is_draft = True`. Reviews provision upon publishing (applying ADR-0010).
3. **Lifecycle:**
   - **Manual Draft:** `is_draft = True`, `draft_expires_at = null`. Stays draft across pushes.
   - **Auto-Debounce:** Pushes set `is_draft = True` with a timeout (e.g., 15 mins), reset by subsequent pushes.
   - **Publishing:** Background worker publishes on timeout, or author clicks "Ready for Review", triggering provisioning.

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
- **Immediate Dispatch:** Rejected because it spams reviewers with notifications.
- **Mutable Drafts:** Rejected because it violates ADR-0008 and races with CI.
- **Garbage-Collecting Drafts:** Loses useful history.

## Assumptions
Backend supports background job scheduling for timeouts.
