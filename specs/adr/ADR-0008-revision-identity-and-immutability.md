---
id: ADR-0008
date: 2026-10-01
status: proposed
agreed_by: []
---

# ADR-0008: Revision Identity and Immutability

## Context
PRs are mutable.
To ensure auditability and prevent tampering - test results, reviews, and build results must attach to an immutable snapshot.
Relying only on Git head SHAs misses base (target) branch changes and external metadata (e.g. justifications of changes in the changelog).

## Decision
Model PR and staging batch revisions as immutable, uniquely identified entities:

1. **PR Fingerprint:** Deterministic SHA-256 computed from head commit SHA, base commit SHA, base (target) branch, and canonical metadata digest.
2. **Batch Fingerprint:** Deterministic SHA-256 computed from sorted PR fingerprints and canonical metadata digest.
3. **Format & Stability:**
   - UTF-8 minified JSON, lexicographically sorted keys/values.
   - New fields must be optional and omitted when null/default to preserve historical hashes.
4. **Immutability:** Changes to inputs create a new revision; past revisions are immutable.
5. **Strict Binding:** Reviews, tests, and build results attach only to specific revisions.
6. **Merge Guard:** Server-side pre-receive hook ensures target commit matches latest approved revision.

## Consequences

**Positive:**
- Complete audit trail: approvals and test results cannot be associated with altered states.
- Tamper-proof: changing review-critical metadata invalidates the revision and requires re-evaluation.
- Deterministic staging: batches reliably test exact snapshots without silent code drift.
- Strong enforcement: server-side hooks prevent unapproved merges.

**Negative:**
- Non-code metadata updates create new revisions, requiring approval inheritance mechanisms.
- Storage increases as every push and metadata edit persists a new record.
- Requires server-side git hook support.

## Considered Options
- **Git Head SHA Only:** Rejected because it ignores base (target) branch changes and external metadata, allowing post-approval tampering.
- **Mutable PRs with Status Resets:** Rejected beacuse it destroys historical audit trails, making it impossible to see what was previously reviewed.
- **Metadata in Commits:** Pollutes Git history and complicates forks by inheriting irrelevant metadata.

## Assumptions
Git backend supports server-side pre-receive hooks or equivalent mechanism to allow merging only fully approved PRs.
