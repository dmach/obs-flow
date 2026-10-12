---
id: ADR-0013
date: 2026-10-12
status: active
agreed_by: []
---

# ADR-0013: Target Source Rebuild with Reproducible Checks

## Context
During pull request (PR) reviews, ephemeral staging subprojects in Open Build Service (OBS) build and validate packages before merging. Quality Engineering (QE) raised concerns regarding redundant testing cycles: once in the temporary PR staging subproject, and again after the PR merges and rebuilds in the product target project.

A possible proposal is to skip the target rebuild by copying pre-built binaries directly from the staging subproject into the product target project and resigning them with production keys. However, direct binary copying violates fundamental build guarantees and introduces critical system limitations:

- Ephemeral staging projects are deleted after merge, turning embedded provenance metadata (`DISTURL`, SLSA attestations) into dead links (HTTP 404).
- Post-mortem crash analysis, GDB debugging, and `debuginfod` servers rely on valid `DISTURL` endpoints to locate source trees and debuginfo packages.
- Packages with embedded cryptographic signatures (e.g., `kernel`, `shim`, `grub2`) cannot be resigned via RPM header modification alone; they require multi-stage rebuilds using official production keys that cannot be exposed to untrusted PR sandboxes.
- Concurrent PR merges into shared dependencies can produce Application Binary Interface (ABI) mismatches if pre-built binaries are copied without a rebuild against the updated target baseline.

## Decision
We chose to rebuild all merged packages from source in authoritative target projects and verify build equivalence against ephemeral staging artifacts using automated reproducible build checks (`obs-reproduciblecheck`).

When the bitwise comparison confirms identical binaries, QE inherits the staging test validation without re-testing the package. We strictly reject copying binaries directly from ephemeral staging subprojects into product repositories.

## Consequences

**Positive:**
- Preserves build provenance, immutable audit logs, and permanent `DISTURL` references in published packages.
- Maintains automated crash analysis, GDB debugging fidelity, and `debuginfod` symbol resolution without dead references to pruned staging subprojects.
- Isolates production release keys and Secure Boot certificates from untrusted PR staging environments.
- Supports packages with embedded binary signatures that cannot be resigned via package headers alone.
- Prevents ABI and symbol version incompatibilities caused by concurrent PR merges into shared dependencies.
- Eliminates duplicate QE testing whenever the reproducible check passes, cryptographically inheriting staging validation.
- Enables pre-merge validation of downstream product and image builds (KIWI, Docker, Product Composer) via ephemeral staging overlays, eliminating post-merge composition failures and avoiding the fragile setup of populating legacy channel repositories.

**Negative:**
- Consumes additional build worker compute by rebuilding every merged package from source in the target project.
- Requires a full QE re-test in the target project whenever non-deterministic packaging or environment drift causes reproducible checks to fail.

## Considered Options

- **Direct Binary Copying with Header Resigning** - Copy pre-built RPM packages from staging subprojects to target projects and swap GPG signatures.
  Rejected because it invalidates `DISTURL` provenance once ephemeral subprojects are pruned, breaks automated crash dump analysis and `debuginfod` symbol resolution, fails to support embedded binary signatures without repackaging, and risks ABI breakage under concurrent PR merges.
- **Permanent Retention of PR Staging Subprojects** - Retain all PR subprojects indefinitely as immutable archives, similar to maintenance incident projects.
  Rejected because storing thousands of PR sandbox projects and source trees causes unsustainable storage bloat.
- **Faking Target Project Provenance in Staging** - Inject product target project names and repository paths into staging builds.
  Rejected because it falsifies build provenance, violates security auditability, and misaligns DWARF debugging symbols if staging dependencies diverge from the target tree.

## Assumptions
- Target packages support deterministic compilation using pinned toolchains and timestamps (`SOURCE_DATE_EPOCH`).
- The build infrastructure provides `obs-reproduciblecheck` to strip RPM header signatures and execute bitwise verification (`cmp -s`).
- Authoritative target projects permanently retain buildroot environment definitions (`_buildenv`), source snapshots, and build logs.

Revisit this decision if OBS introduces native content-addressed artifact caching with verifiable, signed provenance rewriting across project boundaries.
