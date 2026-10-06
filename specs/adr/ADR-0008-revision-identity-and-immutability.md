---
id: ADR-0008
date: 2026-10-01
status: active
agreed_by: []
---

# ADR-0008: Revision Identity and Immutability

## Context
Pull requests are mutable, evolving proposals.
To ensure auditability and prevent post-approval tampering (e.g., changing target branches, justifications, or bug references after reviews pass),
all test results, review decisions, and staging memberships must attach to an exact, immutable snapshot of the change.

Relying solely on git head commit SHAs is insufficient, as it misses changes to the base branch (rebases) and critical external metadata
(like CVEs or business justifications). The release pipeline requires an absolute guarantee that what was approved is exactly what gets merged.

## Decision
We model pull request and staging batch revisions as immutable, uniquely identified entities:

1. **PR Revision Fingerprint:** A deterministic SHA-256 fingerprint computed from:
   - Head commit SHA (source tree).
   - Base commit SHA (merge base).
   - Canonical digest of review-critical metadata (e.g., target branch, justifications).
2. **Staging Batch Revision Fingerprint:** A deterministic SHA-256 fingerprinte computed from:
   - Sorted list of included PR revision fingerprints
   - Canonical digest of review-critical metadata (e.g. justifications).
3. **Revision Fingerprint Backwards Compatibility:** Revision Fingerprints MUST remain stable even if new fields are added to the hashed data.
   - **Format:** UTF-8 encoded, minified JSON (no whitespace outside string values, no newlines).
   - **Ordering:** All JSON object keys and list values MUST be sorted lexicographically.
   - **Default Omission:** Any new fields added to the schema in the future MUST be optional. When serializing for hashing, all fields with `null` or default values MUST be strictly omitted. This guarantees that older revisions lacking the new fields serialize to the exact same string and maintain an identical hash.
3. **Immutability:** Revisions are strictly immutable. Any change to the fingerprint inputs spawns a new revision; past revisions are never altered or deleted.
4. **Strict Binding:** Reviews, test runs, and batch memberships attach exclusively to a specific revision, never to the mutable pull request itself.
5. **Git-Hook Merge Guard:** A server-side pre-receive hook verifies that:
   - The commit being merged matches the head SHA of the latest revision.
   - The revision fingerprint matches current state.
   - All required reviews and checks for the revision (and its staging batch, if applicable) are satisfied.

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

- **Git Head SHA Only:** Track revisions using only commit hashes.
  Rejected because it ignores base branch changes and external metadata, allowing post-approval tampering.
- **Mutable PRs with Status Resets:** Standard Git hosting model where states reset on push.
  Rejected beacuse it destroys historical audit trails, making it impossible to see what was previously reviewed.
- **Tracking All Metadata in Commits:** Embed justifications and bug links purely in git commits.
  Rejected beacuse it tightly couples package payloads with PR metadata, polluting history upon forks and preventing API-driven metadata management.

## Assumptions
Assumes the Git backend supports server-side pre-receive hooks or equivalent blocking status checks.
