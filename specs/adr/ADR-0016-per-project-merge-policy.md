---
id: ADR-0016
date: 2026-11-27
status: proposed
agreed_by: []
---

# ADR-0016: Per-Project Merge Policy

## Context
Projects differ in how much release discipline they need:
- Distribution projects require coordinated, tested releases.
- Personal or simple projects want minimal friction.
A single policy for all either over-constrains simple projects or under-protects distribution projects.

## Decision
We chose a per-project **merge policy**: two pointers on an ordered chain of merge levels.

1. **Merge levels:**
   - `push` - Maintainers can push directly to git, everyone else lands via merging PRs.
   - `pr` - Changes land via merging PRs.
   - `batch` - Changes require opening PRs, land via merging staging batches. (Details in ADR-0007)
   - `compose` - Changes require opening PRs, continue through staging batches and land via merging composes. (Details in ADR-0013)
2. **Chain:** an ordered sequence of merge levels: `push` < `pr` < `batch` < `compose`.
3. **Pointers:**
   - `merge_floor` (default `push`) - the lowest permitted merge level, i.e. the discipline.
   - `merge_ceiling` (default `batch`) - the highest enabled merge level.
   - Constraint: `merge_floor` <= `merge_ceiling`.
   - The default (`push`, `batch`) is a safe default for majority of the projects, allowing direct pushes by maintainers and external contributions via PRs and batches.
4. **Landing rule:** a change may land on any level within `[merge_floor .. merge_ceiling]`. Levels below the floor and above the ceiling are disabled.
5. **Changes:** a policy change takes effect immediately for all work in the project, including open objects; no per-object pinning.
   Consequences for stranded objects are resolved manually (changes are exceptional).

Example: a devel project with floor=`push`, ceiling=`batch`:
- Changes land via direct pushes (maintainers only) or PRs or staging batches.
- Disables composes.

Example: a distribution project with floor=`compose`, ceiling=`compose`:
- Changes land via composes.
- Forbids direct pushes, PR merges, and staging batch merges.

## Consequences

**Positive:**
- One knob pair expresses both discipline (floor) and convenience (ceiling). Optional intermediate steps are expressible (e.g. direct pushes plus optional staging).
- Extensible: new merge levels slot into the chain without changing the mechanism.

**Negative:**
- Two fields instead of one enum; validation (`merge_floor` <= `merge_ceiling`) required.
- Policy changes affect in-flight work immediately. Stranded objects need manual resolution.

## Considered Options
- **Mandatory full chain for all projects** - Rejected because it over-constrains simple projects.
- **Single tier enum** (topmost layer = merge unit) - Rejected because it cannot express "level available but not mandatory" (devel project case).
- **Independent flags per level** - Rejected because they allow odd combinations and cause combinatorial growth.

## Assumptions
- Each extending ADR defines its level's landing semantics; this ADR owns only the high-level mechanism.
