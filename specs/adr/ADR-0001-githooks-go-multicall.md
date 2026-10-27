---
id: ADR-0001
date: 2026-10-27
status: active
agreed_by: []
supersedes: 
superseded_by: 
---

# ADR-0001: Go-based Multicall Binary and Centralized Commit Processing for Git Hooks

## Context
Git hooks enforce policies (data integrity, commit validation, access control) during git operations in server-side bare repositories.
Performance is critical, especially for operations involving many commits (like large pushes).
Traditionally, hooks or individual policies might independently parse git objects, leading to redundant I/O and processing overhead.
We need a fast, lightweight, and easily deployable system to execute these hooks efficiently.

## Decision
Implement Git hooks as a single Go multicall binary that centralizes commit processing and executes hook policies as callbacks.

1. **Go:** Fast startup, single static binary with no external runtime dependencies.
2. **Multicall Binary:** Hooks (e.g., `pre-receive`, `update`, `post-receive`) are symlinks to one binary; the execution context is determined by `os.Args[0]`.
3. **Centralized Commit Enumeration:** The binary implements a central mechanism to enumerate all commits involved in the git operation and fetch the necessary information from them in a single pass.
4. **Callback Architecture:** Individual hook policies run as callbacks on the enumerated commits. This ensures we "touch every commit once," avoiding redundant git object lookups, diff calculations, and parsing across different policies.
5. **Deferred Communication:** The mechanism for communicating with external background services (e.g., for fetching policy settings or locking) is explicitly descoped from this decision and deferred to a separate ADR.

## Consequences
**Positive:**
- **Performance:** Drastically reduces redundant git object parsing and I/O by touching each commit only once per operation.
- **Maintainability:** Centralized parsing and enumeration logic reduces duplication across different hook implementations.
- **Deployment:** A single binary simplifies deployment, versioning, and symlink-based hook management.

**Negative:**
- **Internal Complexity:** The callback architecture requires a well-defined internal API for hook policies to register and execute against the enumerated commits.
- **No Local Extensibility:** All hook logic remains centralized within the multicall binary; it does not support local drop-in scripts.

## Considered Options
- **Independent Hook Scripts/Binaries:** Rejected due to the performance overhead of starting multiple processes and the redundant commit parsing that occurs when each script independently inspects the git state.
- **Go Binary per Hook:** Rejected due to a larger deployment footprint and the difficulty of sharing the centralized commit enumeration state across separate processes without complex IPC.

## Assumptions
- Hooks execute in a server-side bare repository environment without a working tree.
- The internal callback API can be designed to accommodate all current and future hook policy requirements.
