# OBS Flow - Git Forge Feature Roadmap & TODO

This document tracks missing features and planned enhancements for the OBS Flow native git forge, specifically tailored for distribution package maintenance workflows.

---

## 1. Distribution & OBS-Specific Features
- [ ] **Build Status & CI Integration:**
  - API endpoint for external build workers (OBS backend / dispatchers) to report build status (`pending`, `building`, `succeeded`, `failed`, `unresolvable`) per architecture (`x86_64`, `aarch64`, `riscv64`) and repository target.
  - UI build matrix widget on Pull Request Overview and Staging Batch views.
- [ ] **Artifact & Build Log Browsing:**
  - Direct links to streaming/archived build logs for failed package builds.
  - Downloadable built `.rpm` / `.deb` package artifacts for testing and local verification.
- [ ] **Automated Spec & Changelog Validation:**
  - Server-side pre-receive / hook checks validating RPM `.spec` syntax, `rpmlint` checks, and `.changes` format consistency.
  - Enforce changelog entry requirement when packaging sources change.
- [ ] **Submit Request (SR) Emulation & Cross-Project Workflows:**
  - Workflow mimicking OBS Submit Requests, linking source packages across projects (e.g., `home:tux/python3` -> `openSUSE:Factory/python3`).
  - Automatic source branch cleanup or archiving upon acceptance.
- [ ] **Release Management & Distribution Tagging:**
  - View git tags associated with package releases and distribution milestones.
  - Automated changelog generator from commit history between tags.

---

## 2. Advanced Code Review & Pull Request Features
- [x] **Inline Code Comments:**
  - Comment on specific lines in the "Files Changed" diff view with explicit revision context.
  - Multi-line / hunk comment threads attached to revisions.
- [x] **Review Threads & Resolutions:**
  - Conversation threads attached to code diff lines with multi-revision lifecycle (current vs outdated).
  - Ability to mark review threads as "Resolved" or reopen them.
- [x] **Shared Discussion Comments (PRs & Staging Batches):**
  - Polymorphic Comment model in `core` using `GenericForeignKey` and `GenericRelation`.
  - HTMX in-place commenting and deletion for both Pull Requests and Staging Batches.
  - RPC API endpoints (`/api/v1/comment/add`, `/api/v1/comment/list`) and CLI commands (`flow pr comment add/list`, `flow staging comment add/list`).
- [ ] **General PR Discussion Timeline & Activity Stream:**
  - Interactive timeline in PR Overview combining comments, review submissions, and state transitions.
  - User mentions (`@user`) and cross-referencing of issues (`#123`, `BUG#456`).
- [ ] **Suggested Changes:**
  - Reviewers can propose inline code changes within comments.
  - Author can apply suggested changes directly with a single click (creating a git commit).
- [ ] **Revision Diffing (Interdiff / Range-diff):**
  - Compare revision N against revision N+1 when a PR is updated or force-pushed.
  - Review only the changes made in response to previous review feedback.

---

## 3. Standard Git Forge Features
- [ ] **Native Issue Tracking:**
  - Built-in issue tracker per project/package with labels, milestones, assignees, and state tracking.
- [ ] **Web-based File Editing:**
  - In-browser editor for spec files, patches, and documentation with direct commit support.
- [ ] **Repository Settings & Branch Protection:**
  - Web UI for branch protection rules (enforce PRs, require reviews, prevent force pushes).
  - Webhook configurations for external notification systems.
- [ ] **Forks UI & Discovery:**
  - Visual fork network visualization for packages.
  - 1-click "Fork" button in the web UI.
- [ ] **Git Blame / Annotate View:**
  - Line-by-line blame view in the code browser showing author, commit SHA, and date.
- [ ] **Code & Commit Search:**
  - Search code, filenames, and commit messages across repositories.

---

## 4. Git Transport & Performance
- [ ] **SSH Transport:**
  - User SSH public key management in accounts (`SSHKey` model).
  - `obs-flow-shell` wrapper command executing `git-upload-pack` and `git-receive-pack` over SSH.
  - Integration with OpenSSH `AuthorizedKeysCommand` or `authorized_keys`.
  - Reuse unified authorization service (`core.git_forge` / `git_transport.policy`) for SSH commands.
- [ ] **Git LFS (Large File Storage):**
  - Git LFS Batch API endpoint (`POST /info/lfs/objects/batch`).
  - Binary object storage backend on local POSIX filesystem for large source archives (`.tar.xz`, `.tar.gz`).
  - Upload (PUT) and download (GET) endpoints with token authentication.
