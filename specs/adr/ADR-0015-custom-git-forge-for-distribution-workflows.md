---
id: ADR-0015
date: 2026-11-23
status: proposed
agreed_by: []
supersedes: 
superseded_by: 
---

# ADR-0015: Custom Git Forge for Distribution Workflows

## Context
The Open Build Service (OBS) ecosystem is transitioning its source control management to Git. Initial prototypes evaluated using general-purpose Git forges (such as Gitea) augmented with external bots and webhooks.

However, Linux distribution engineering fundamentally conflicts with general-purpose forge design:
1. **Uncustomizable PR Views:** Generic forges hardcode pull request interfaces. Displaying OBS build results, CVE/PED links, and staging batch progress requires posting automated comments, turning timelines into unreadable bot spam.
2. **Merge-Base Blindspot:** Generic forges compute diffs strictly against the merge-base (`git diff target...source`). In fast-moving distribution branches with backports, this hides changes that already exist on the target branch.
3. **Silent Mutability:** Pushing changes to a source branch silently mutates open pull requests, invalidating running staging builds and breaking auditability.
4. **Coarse Permissions:** Generic forges require repository maintainer permissions to open PRs across branches within the same repository (e.g., forwarding fixes from Factory to SLFO maintenance branches).
5. **Fragile Bot Workarounds:** Package lifecycle operations (new package requests, deletions) are handled via free-text issue parsing bots that drop webhooks and create split-brain states between the forge and OBS.

## Decision
We chose to implement a dedicated, distribution-specific Git forge ("The Workflow Service") built on bare Git repositories.

1. **Bare Git Backend:** Host standard bare repositories directly on disk, utilizing standard `git-upload-pack` and `git-receive-pack` executables wrapped by native authentication and hooks.
2. **Authoritative Database:** The Workflow Service database is the strict single source of truth for projects, packages, pull requests, reviews, and staging batches.
3. **Distribution-Tailored PR Interface:** Build a purpose-built server-driven UI (Django + HTMX) where build status, CVE/PED tracking, and staging batch status are native UI components rather than bot comments.
4. **Accurate Diff Semantics:** Support both revision diffs and target-tip merge diffs to eliminate merge-base blindspots.
5. **Immutable Revisions:** Every submission update generates an explicit, immutable revision (similar to legacy OBS submit requests), preserving build and review audit history.
6. **First-Class Lifecycle APIs:** Handle package creation, deletion, and cross-branch forwarding via dedicated RPC endpoints rather than parsing free-text issues or pull request descriptions.

## Consequences

**Positive:**
- Eliminates the asynchronous bot ecosystem, comment scraping, and webhook synchronization failures.
- Provides a unified web interface showing real-time build and staging batch statuses directly.
- Prevents silent code drift during reviews through immutable revisions.
- Allows fine-grained permission control for cross-branch forwarding without granting full repository write access.
- Provides accurate diffs that reflect the real state of target distribution branches.

**Negative:**
- Requires building and maintaining our own HTTP/SSH Git transport, authentication, and web UI.
- Does not provide general-purpose forge features (generic wikis, social feeds, or Kanban boards).
- Requires maintaining custom server-side Git hook policies and repository reconciliation routines.

## Considered Options

- **Extending Gitea with Bots and Webhooks:**
  Rejected because Gitea assumes one repository equals one application, cannot customize pull request views, hardcodes merge-base diffs, silently mutates PRs on push, and creates an unmaintainable web of asynchronous bots.
- **Extending GitLab or GitHub via Plugins:**
  Rejected due to high operational overhead, licensing and deployment constraints, inability to natively replace core PR diffing and immutability semantics, and lack of native OBS staging integration.
- **Modifying the Legacy OBS Rails Monolith:**
  Rejected because embedding Git deeply into the intertwined legacy frontend/backend architecture risks widespread regressions and exacerbates historical technical debt.

## Assumptions
- Repositories can reside on a shared POSIX filesystem accessible to the service and Git hook executables.
- Git operations wrap standard `git` executables rather than custom Git protocol implementations.

Revisit this decision if an open-source Git forge emerges with native support for multi-package distribution workflows, customizable PR interfaces, and immutable revision semantics.
