---
id: ADR-0013
date: 2026-11-05
status: proposed
agreed_by: []
supersedes: ADR-0007
superseded_by: 
---

# ADR-0013: Org-based Native Git Forge

## Context
We are building a next-generation Open Build Service that requires a lightweight, native git source backend.
The primary entities in this system are "projects" and "packages".
We need to define how these domain entities map to git repositories and how those repositories are laid out on disk and in URLs.

Two workflows must be supported:
- Distribution workflows, where one shared repository per package holds branches for multiple product releases.
- Custom projects, where a project maintains its own package sources.

Supporting both with separate models (single-branch project repositories and shared pool repositories) would mean two layouts, two source resolution rules, and two authorization paths.
Transport and authorization of git operations are decided separately in a different ADR.

## Decision
We will implement a native git forge where every project is a branch in repositories owned by an org:

1. **Native forge:** Repositories are bare git repositories served with the standard `git-upload-pack` and `git-receive-pack` executables.
2. **The database is authoritative:** It defines which orgs, projects, and packages **exist**. Git state follows it.
3. **Orgs:** An org is a first-class domain entity and the only repository namespace.
   - Shared orgs are created by administrators only.
   - Every user has an implicit personal org named `~<username>`.
4. **Layout:**
   - Each org contains one repository per package and one `_project.git` repository for project configuration.
   - URLs use semantic prefixes (`/project/` and `/package/`) and map project/package identifiers to the on-disk org repositories.
   - Examples:
     -  `https://obs.example.com/project/<project>.git` -> `/var/lib/obs/repos/<org>/_project.git`
     -  `https://obs.example.com/package/<project>/<package>.git` -> `/var/lib/obs/repos/<org>/<package>.git`
5. **Projects are branches:**
   - A project belongs to exactly one org and owns exactly one branch name in that org across all repos.
   - The branch name:
     - Chosen explicitly at project creation (e.g., `factory` branch for `openSUSE:Factory` project).
     - Fixed at project creation, immutable.
     - It must be a valid git ref name, must not contain `/`.
     - It must be unique within the org, so each branch maps to exactly one project.
   - A project's package sources live on its branch in the org's package repositories.
   - A project's configuration lives on its branch in the org's `_project.git`.
   - A project uses only packages from its own branch in its own org. (Inheritance or linking across branches or orgs is out of scope of this ADR.)
6. **Names:**
   - Org, project, and package names must match `^[A-Za-z0-9][A-Za-z0-9._+:-]{0,199}$`, must not end with `.git`, and must not contain `..`.
   - Uniqueness is case-insensitive.
   - Because names must start with an alphanumeric character, `_project.git` never collides with a package and `~<username>` never collides with a shared org.
7. **Explicit membership:**
   - A package belongs to a project only when it exists in the database.
   - Creating a package creates a repository in package's org if it is missing.
   - The branch starts as a copy of a named existing branch, or may not be created at all (to be created via the first pull request).
   - A pushed branch never creates a package or project.
9. **Forks:** Long-lived personal or devel work on a package from another org is a fork into the user's personal org: a local bare clone with hardlinked objects plus a recorded fork relationship. Sharing objects via `objects/info/alternates` is forbidden, because deleting the source repository would corrupt every repository that borrows from it.
10. **Lifecycle:**
    - Renaming orgs, projects, and packages is forbidden.
    - Deletion follows a per-org policy. In personal orgs, deleting a project deletes its branches, a repository is removed when no project branches remain, dependent records are deleted, and names can be reused. In shared orgs, projects and packages are retired per branch by a normal commit that removes all files and adds a `dead.package` file containing the reason.
    - History rewrites are an admin-only exception outside this decision.
11. **Consistency:** Repository and branch creation runs after the database transaction commits and is idempotent. A reconciliation operation detects and repairs drift between the database and git.

## Consequences

**Positive:**
- **One model:** A single layout, source resolution rule `(org, package, branch)`, and authorization path for all projects.
- **Familiar:** Matches the org/repository model of common git forges and existing distribution workflows.
- **Admin discoverability:** The human-readable layout lets administrators locate repositories without lookup tools.
- **No admin bottleneck:** Personal orgs let users create projects without administrator action.
- **Predictable state:** Since the database is authoritative, stray pushes cannot silently change domain state.

**Negative:**
- **Blast radius:** One repository carries every project in the org; corruption, maintenance, or lock contention affects all of them.
- **Coarse isolation:** Read access is per repository, so private or embargoed projects need their own org and lose shared history.
- **Ref growth:** Orgs with many projects accumulate many branches per repository; default clones fetch all of them.
- **Second identifier:** Each project has a name and a separate branch name that users must learn.
- **Weaker identity guarantee in personal orgs:** After delete and recreate, old URLs and clones point at unrelated history.
- **Inflexible naming:** Typos cannot be corrected; in personal orgs the entity must be deleted and recreated, in shared orgs not at all.
- **Migration:** Existing Gitea-backed mappings and pull request data must be migrated to the native forge.

## Considered Options

- **Strictly single-branch project repositories (ADR-0007):**
  Rejected because it cannot host distribution workflows with shared package history.
- **Hybrid of single-branch project repositories and pool repositories:**
  Rejected because two layouts, resolution rules, and authorization paths add complexity without a capability the org model lacks.
- **Branch name equal to project name:**
  Rejected because git ref names forbid characters used in existing project names (e.g., `:`) and cannot nest.
- **Branch name derived from the project name (slug):**
  Rejected because distributions need short, meaningful branch names (e.g., `factory`) that are independent of project names.
- **Forks as branches in the source repository:**
  Rejected for long-lived work because it grows ref counts in shared repositories without bound; short-lived branches are covered by the transport and authorization ADR.
- **Hiding Gitea behind our service:**
  Rejected because it means running a second application with its own user, ACL, storage, and repository model that must be kept in sync.
- **UUID-based storage (e.g., `/repos/<uuid>.git`):**
  Rejected because renames are forbidden, so UUID indirection only destroys admin discoverability.
- **Python git library (e.g., Dulwich) for the server:**
  Rejected because the standard executables are simpler, more robust, and fully protocol compatible.

## Assumptions
- All processes that serve git or execute hooks share one POSIX filesystem.
  High availability and replication are out of scope. NFS requires correct locking for git ref updates.
- Usernames are immutable; otherwise personal org paths would change.
- **TODO (pull request identity scope, needs stakeholder decision):** Because names in personal orgs can be reused and dependents are deleted with their entity, per-repository pull request numbers that restart from 1 would make references like `org/pkg#5` in changelogs, bug trackers, and commit messages silently point at a different pull request. Options: (a) a global pull request ID; (b) per-repository numbers backed by a counter keyed by repository path that is never deleted. Per-repository numbers are shared by all projects in the org.
- **TODO (audit trail):** A permanent record of deleted entities and their dependents is a future extension.
- Revisit this decision when high availability or multi-node git storage becomes a requirement, when per-repository ref counts cause performance problems, or when the pull request identity TODO is resolved.
