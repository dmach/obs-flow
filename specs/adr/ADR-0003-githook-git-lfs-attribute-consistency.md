---
id: ADR-0003
date: 2026-10-27
status: active
agreed_by: []
supersedes: 
superseded_by: 
---

# ADR-0003: Githook: Git LFS Attribute Consistency Verification

## Context
Git LFS relies on `.gitattributes` (`filter=lfs`) to store pointers in Git and binary payloads in LFS storage.
Developers may inadvertently commit raw binaries without `.gitattributes` (causing repository bloat) or create
mismatched/orphan pointer files. We need server-side validation to ensure consistency.

## Decision
Enforce a pre-receive hook verifying strict consistency between `.gitattributes` and blob contents for all new commits.

1. **Blob Inspection:** Parse all newly introduced or modified blobs.
2. **Attribute Check:** Query `git check-attr --source=<commit-sha>` to evaluate `filter=lfs` directly from the commit object, bypassing the need for a working tree.
3. **Validation:** Reject pushes if an LFS-configured file is not a valid pointer, or if a pointer file lacks `filter=lfs`.
4. **Allowlist:** Support an optional allowlist for historical revisions predating the policy.

## Consequences
**Positive:**
- **Prevents Bloat:** Blocks accidental binary commits.
- **Integrity:** Ensures all LFS pointers are properly tracked by `.gitattributes`.

**Negative:**
- **Push Latency:** Evaluating `git check-attr` and inspecting blobs adds overhead during large pushes.

## Considered Options
- **Native Git LFS Client Reliance:** Rejected; misconfigured environments or GUI clients easily bypass filters.
- **File Size Thresholds:** Rejected; misses small LFS-intended files and does not detect malformed pointers.

## Assumptions
- The Git server is running Git >= 2.43 to support the `--source` flag in `git check-attr`.
- LFS pointer format conforms to `version https://git-lfs.github.com/spec/v1`.
- Review if `git check-attr` significantly degrades push performance on large commit batches.
