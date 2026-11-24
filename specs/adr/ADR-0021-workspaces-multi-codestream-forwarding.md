---
id: ADR-0021
date: 2026-11-23
status: proposed
agreed_by: []
supersedes: 
superseded_by: 
---

# ADR-0021: Workspaces, Multi-Codestream Forwarding, and Embargoed Staging

## Context
Packagers frequently maintain fixes across multiple release codestreams (`openSUSE:Factory`, `SUSE:SLFO:Main`, `SUSE:SLFO:1.2`). In existing workflows, packagers must manually switch branches, maintain multiple worktrees, and juggle independent pull requests across repositories. Furthermore, opening PRs directly from mutable devel branches causes unintended modifications to open PRs when further commits are pushed (`REDESIGN.md`).

Additionally, security and maintenance fixes require embargoed development and testing. Git read access is all-or-nothing per repository (`ADR-0014`); sharing Git objects via mirrors or `objects/info/alternates` between public and private repositories risks catastrophic zero-day leaks.

## Decision
We chose to implement a first-class **Workspace** workflow supported by server-side fan-out, personal fork isolation, and tainted private staging.

1. **First-Class Workspace:**
   - Packagers create workspaces declaring target codestreams and workspace type:
     - `shared`: Single local branch for packages with identical sources across targets.
     - `divergent`: Coordinated local branches in a single repository for packages requiring target-specific backports.
   - Worktrees are rejected in favor of standard in-repo branches to facilitate seamless local cherry-picking.
   - Workspace metadata (targets, bug IDs, CVEs) is stored locally (`.flow/workspace.toml`) and kept out of Git commit trees.

2. **Server-Side Personal Forks:**
   - Workspace branches are pushed to personal fork repositories (`~<username>/<package>.git`) seeded via hardlinks (`git clone --bare -l`).
   - Pushes never touch official shared pool repositories directly, preventing ref pollution and preserving immutable PR revisions.

3. **Remote Test Provisioning:**
   - On the first push or remote test trigger, the Workflow Service lazily provisions a temporary OBS test project (`home:<username>:workspaces:<name>`) configured to build against the declared target distributions.
   - Workspace projects are automatically garbage-collected after submission merge or explicit deletion.

4. **Multi-Codestream Submission & Fan-Out:**
   - Executing `flow submit` pushes workspace branches and creates single-package PRs across all target codestreams simultaneously.
   - For `shared` workspaces, the server handles clean cherry-picks to downstream branches automatically; if a downstream branch conflicts, that target can be split into a divergent branch locally.
   - All PRs created in one submission share a `submission_group_id` for unified tracking and status reporting.

5. **Embargoed Isolation & Tainted Staging:**
   - Workspaces created with `--embargoed` strictly use isolated, private repositories within an authenticated security namespace.
   - Private repositories are seeded via hardlinks from public upstream, but public repositories never reference private repositories via alternates, and `--mirror` pushes are prohibited.
   - Temporary OBS test projects for embargoed workspaces are created with disabled public access.
   - **Taint Security Invariant:** If any pull request in a Staging Batch is embargoed, the **entire Staging Batch and its OBS staging project become private**. All artifacts, logs, and reviews are restricted strictly to authorized security and release personnel until the embargo lifts.

## Consequences

**Positive:**
- Eliminates manual multi-branch cherry-picking and worktree management for packagers.
- Prevents silent mutation of open PRs by isolating working branches in personal forks.
- Automates OBS test project configuration for multiple distribution targets.
- Prevents zero-day object leakage by enforcing strict repository-level isolation for embargoed fixes.
- Guarantees confidential integration testing by automatically elevating staging batches to private mode.

**Negative:**
- Requires the Workflow Service to coordinate OBS project lifecycle and Git fork management.
- Embargoed staging batches hold all contained PRs until the embargo date unless release managers split them.

## Considered Options

- **Git Worktrees for Multi-Target Development:**
  Rejected because worktrees lock branches from checkout across folders and complicate cross-branch cherry-picking and toolchain caching.
- **Direct Branches in Shared Pool Repositories:**
  Rejected because personal experimental branches pollute shared repositories and require granting broad write permissions to all contributors.
- **Sharing Private Git Objects via Alternates:**
  Rejected because Git does not enforce per-object read permissions; alternates allow unauthenticated readers of public repos to fetch private objects.
- **Public Staging with Redacted Logs for Embargoed Fixes:**
  Rejected because binary packages, spec files, and dependency trees in staging repositories can still leak the vulnerability.

## Assumptions
- Target distributions provide compatible build baseline repositories in OBS.
- Release and security team members have the necessary credentials to access private staging subprojects.

Revisit this decision if Git introduces native object-level encryption or if OBS deprecates subproject access control flags.
