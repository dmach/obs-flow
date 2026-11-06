---
id: ADR-0014
date: 2026-11-05
status: proposed
agreed_by: []
---

# ADR-0014: Git Transport and Authorization

## Context
ADR-0013 defines a native git forge with org-owned package repositories where each project is a branch. This ADR defines how git clients reach those repositories and how access is controlled.

Constraints:
- HTTP(S) transport is needed first; SSH is planned. Authorization must not be implemented twice.
- `git-upload-pack` (clone, fetch) runs no server-side hooks, so hooks cannot enforce read access.
- An org repository is shared by all projects in the org, each owning one branch. Write access must be decided per ref.
- Git cannot reliably hide individual branches from a reader: `uploadpack.hideRefs` hides ref names, but reachable objects can still be fetched.

## Decision
We will control git access as follows:

1. **Transport:** HTTP(S) through our Django stack first, SSH later. Both wrap the standard `git-upload-pack` and `git-receive-pack` executables.
2. **Single authorization service:** One domain authorization service decides all git access.
   - Transport front-ends (HTTP now, SSH later) enforce repository-level read and write access. Read access (`git-upload-pack`) is allowed anonymously. Write access (`git-receive-pack`) requires authentication via HTTP Basic Auth (supporting user passwords and API tokens).
   - The `pre-receive` hook enforces per-ref write policy.
3. **Hook communication:** Hooks communicate with the Django application over a Unix socket. `post-receive` notifies the domain about accepted pushes over the same socket; failed notifications are recovered by reconciliation (ADR-0013).
4. **Ref policy:**
   - A project's branch is governed by the owning project. The project defines who may change it and whether changes require a pull request or allow direct pushes.
   - `private/<username>/...` branches can be created and pushed only by that user, who must be a maintainer of a project in the org.
   - All other refs are rejected.
5. **Protection:** Force-push and deletion of a project branch are rejected by default. A project can allow them (e.g., devel projects). A force-push to a branch targeted by open pull requests creates a new pull request revision.
6. **Read isolation (security constraint):** Read access is granted per repository, all or nothing. Public repositories allow anonymous clone and fetch operations. Per-branch read restrictions are not supported. Embargoed or private work must be done in a separate org.

## Consequences

**Positive:**
- **Single source of truth:** HTTP, SSH, and hooks all ask the same service, so ACLs are not duplicated.
- **Safe shared repositories:** Per-ref write policy lets multiple projects share an org repository without stepping on each other's branches.
- **No branch collisions:** User-scoped `private/` branches cannot collide and are unambiguous next to release branches.
- **No deadlock on push:** Hooks use a Unix socket instead of calling the public HTTP endpoint that is serving the push.
- **Honest confidentiality:** Per-repository read access does not promise confidentiality that git cannot provide.

**Negative:**
- **Two enforcement points:** Repository-level checks live in transport front-ends and per-ref checks in hooks, even though both delegate to one service.
- **Restricted branching:** Contributors cannot push arbitrary branches; outside `private/<username>/...` they need forks, which are not yet designed.
- **Coarse read access:** Embargoed work cannot live in a public org repository.
- **Configurable protection:** Projects that allow force-push accept history rewrites on a source of truth.

## Considered Options

- **Authorization only in the HTTP routing layer:**
  Rejected because it cannot check individual refs inside a push and would be duplicated for SSH.
- **Authorization only in hooks:**
  Rejected because `git-upload-pack` runs no hooks, so reads would be unrestricted.
- **Hooks calling the public HTTP endpoint:**
  Rejected because a push holds a worker while the hook calls back into the same worker pool, risking deadlock, and it requires a long-lived shared secret.
- **Hooks bootstrapping Django directly:**
  Rejected because it adds Django startup latency to every push.
- **Per-branch read ACLs with hidden refs:**
  Rejected because hidden refs do not prevent object leaks and would give a false sense of confidentiality.
- **Flat `private/` or `private/<project>/` prefixes:**
  Rejected because flat prefixes collide and project prefixes do not identify the owning user.

## Assumptions
- All repositories and hooks run on the shared filesystem assumed in ADR-0013.
- The ref policy may change once forks or additional workflows are designed.
- **TODO (role model, future ADR):** Roles that grant these permissions (e.g., global admin, project admin for settings such as protection and push policy, project maintainer for content, reader for non-public projects, package-level overrides) are not defined yet. The current code has no per-project role model.
- Revisit this decision when SSH transport is implemented, when forks are designed, or when the role model ADR is accepted.
