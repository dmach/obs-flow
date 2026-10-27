---
id: ADR-0004
date: 2026-10-27
status: active
agreed_by: []
supersedes: 
superseded_by: 
---

# ADR-0004: Githook: Git LFS Object Availability Verification

## Context
Git push and LFS upload are distinct operations. If a Git push succeeds while the LFS upload fails or is bypassed,
commits point to nonexistent objects, causing smudge and checkout failures for downstream clients.

## Decision
Enforce a pre-receive hook verifying that all Git LFS objects referenced by incoming commits exist and are valid in server storage before updating references.

1. **Pointer Identification:** During centralized commit enumeration (ADR-0001), identify new blobs that conform to the LFS pointer specification.
2. **OID Extraction:** Extract the `oid` (SHA-256) and `size` from the identified pointer blobs in memory.
3. **Backend Verification:** Query the server's LFS storage backend directly to verify that objects with the extracted OIDs exist and match the expected sizes.
4. **Validation:** Reject the push if any referenced LFS objects are missing from the storage backend.

## Consequences
**Positive:**
- **Zero Dangling Pointers:** Guarantees all accepted commits can be checked out.
- **Early Feedback:** Prevents broken commits from entering repository history.

**Negative:**
- **Push Latency:** Querying the LFS storage backend adds overhead to pushes with new LFS pointers.

## Considered Options
- **Asynchronous Server Reconciliation:** Rejected; users/CI could fetch broken commits before reconciliation completes.
- **Client-Side `pre-push` Hook:** Rejected; network issues or `--no-verify` can bypass client checks.

## Assumptions
- The Go multicall binary has a mechanism to query the LFS storage backend directly.
- Review if backend query performance degrades when validating large batches of new LFS pointers.
