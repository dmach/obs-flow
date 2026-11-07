---
id: ADR-0016
date: 2026-11-06
status: proposed
agreed_by: []
---

# ADR-0016: Embedded Git Repository and History Browser

## Context
With the adoption of the native org-based git forge (ADR-0013) and direct HTTP transport (ADR-0014), repository sources are stored directly on the server filesystem as bare git repositories.
Developers and maintainers need to inspect source code trees, view file contents, download raw packaging files (e.g., RPM spec files), and view commit history directly within the OBS Flow web UI without relying on external forge services like Gitea or cgit.

## Decision
We chose to embed a server-rendered git repository and history browser directly into OBS Flow Server:

1. **Subprocess execution of standard git CLI:**
   The server queries bare repositories on disk by invoking standard `git` CLI subcommands (`ls-tree`, `show`, `log`) via subprocesses, avoiding external git daemon dependencies or native C-extension libraries.

2. **Entity-integrated code and commit browsing:**
   Code and commit views are exposed as first-class tabs in project and package sub-navigation:
   - Tree and blob browser: `/projects/<project>/code/[<path>]` and `/packages/<project>/<pkg>/code/[<path>]`
   - Commits log: `/projects/<project>/commits/` and `/packages/<project>/<pkg>/commits/`
   - Raw file access: `/projects/<project>/raw/<path>` and `/packages/<project>/<pkg>/raw/<path>`

3. **Point-in-time ref navigation:**
   The code browser supports browsing historical repository states at specific commits or tags via an optional `?ref=<commit_sha>` query parameter. Directory navigation, breadcrumb navigation, and raw downloads preserve the active ref parameter across requests.

4. **Directory commit metadata:**
   Tree listings display the last commit message and timestamp for each entry, fetched via targeted `git log -1` queries.

## Consequences

**Positive:**
- **Zero additional server daemons:** Avoids maintaining a separate web service or reverse proxy for source browsing.
- **Minimal dependencies:** Relies exclusively on standard git binaries already required by the forge runtime.
- **Consistent UI:** Source browsing seamlessly shares typography, Primer Octicon icons, and themes with the rest of OBS Flow.

**Negative:**
- **Process spawning overhead:** Each tree and file view executes `git` subprocesses; large directories with many entries incur multiple `git log` calls unless optimized or cached.
- **Filesystem locality constraint:** The web application server must have direct read access to the repository storage directory on the local POSIX filesystem.

## Considered Options

- **Proxying an external forge UI (e.g., cgit or Gitea web):**
  Rejected because it introduces duplicate authentication, conflicting navigation frames, and additional operational overhead.
- **Using Python C-extension libraries (pygit2 / libgit2):**
  Rejected to avoid compilation dependencies, ABI compatibility issues, and memory safety risks in the Python application runtime.
- **Pure Python git implementations (e.g., Dulwich):**
  Rejected because standard git executables are faster, universally available, and guaranteed to be 100% format-compatible with bare repositories.

## Assumptions
- Bare repositories are accessible via the local POSIX filesystem (shared with git transport per ADR-0013 and ADR-0014).
- Repository directory tree sizes are moderate, keeping subprocess response latencies well under user-noticeable thresholds.

Revisit this decision if repository browsing traffic causes CPU or I/O bottlenecks that warrant in-process caching (e.g., Redis commit caching) or dedicated source-browser microservices.
