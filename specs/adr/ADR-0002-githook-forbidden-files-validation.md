---
id: ADR-0002
date: 2026-10-27
status: active
agreed_by: []
supersedes: 
superseded_by: 
---

# ADR-0002: Githook: Forbidden Files Validation

## Context
Build tooling creates local state files and directories (`.osc`, `_scmsync.obsinfo`, `build.specials.obscpio`).
Committing these files pollutes history, causes merge conflicts, and breaks automated build workers.
We need automated server-side enforcement to block them.

## Decision
Enforce a pre-receive hook rejecting commits containing forbidden paths.

1. **Commit Inspection:** Inspect all new commits relative to `merge-base`.
2. **Rejection:** Immediately reject any push modifying or introducing forbidden paths.
3. **Branch Creation:** Validate the entire tip tree on new branch creation.

## Consequences
**Positive:**
- **Clean Repository:** Prevents tool metadata from entering Git history.
- **Fail-Fast:** Provides immediate feedback during push.

**Negative:**
- **Push Overhead:** Requires diff/tree inspection on each push.
- **Rigidity:** Valid exceptions require updating policy or allowlists.

## Considered Options
- **Post-Push CI Validation:** Rejected because bad commits already enter history, requiring reverts or force pushes.

## Assumptions
- Forbidden paths are never valid source assets.
- Legitimate workflows never require these files.
