---
id: ADR-0023
date: 2026-11-23
status: proposed
agreed_by: []
supersedes: 
superseded_by: 
---

# ADR-0023: Enterprise Maintainership Model and Phase-Aware Review Overrides

## Context
Package maintainer and review management in legacy tooling exhibits major operational pain points (`MAINTAINERS-001` through `006`, `REVIEW-005`):
1. **Lack of Group Assignment:** Maintainership can only be assigned to individual user accounts, forcing manual updates whenever team members change and leaving unassigned packages when individuals leave.
2. **Missing Hierarchy:** No mechanism exists to declare global package maintainers with project- or codestream-specific overrides.
3. **Disconnected Review Routing:** Maintainers are not automatically notified or required as reviewers when packages are introduced, modified, or deleted.
4. **Stuck Review Deadlocks:** When automated bots cannot decide or assigned maintainers are out of office, critical security and product releases become blocked. Existing tools lack fine-grained ACLs to override reviews safely without bypassing global security controls.

## Decision
We chose to implement a hierarchical maintainership model backed by enterprise identity provider (IDP) groups, combined with phase-aware, audited review overrides.

1. **Enterprise IDP / OIDC Group Maintainers:**
   - Maintainership can be assigned to individual accounts (`~alice`) or synchronized IDP groups (`@security-team`, `@gnome-maintainers`).
   - The Workflow Service synchronizes group membership via OIDC/LDAP.

2. **Hierarchical Maintainership & Project Overrides:**
   - **Global Maintainership:** Packages have authoritative default maintainers defined in the central catalog (`pool/`).
   - **Project-Level Overrides:** Downstream projects and products can extend or override maintainers for specific codestreams without modifying the global definition.

3. **Automated Review Routing:**
   - The Review Engine (ADR-0009) automatically expands assigned maintainer groups and schedules required reviews for pull requests.
   - New package requests and package deletion requests automatically assign the effective package maintainers as required reviewers.

4. **Phase-Aware Review Overrides with Audit Logging:**
   - Reviews can be overridden without global administrator escalation, governed by project phase:
     - **Development Phase:** Release Engineers and project owners have override authority.
     - **Maintenance Phase:** Maintenance Coordinators and Security Team members have override authority.
     - **Global Scope:** OBS System Administrators retain universal override authority.
   - **Mandatory Justification:** Every override requires a non-empty textual justification (e.g., tracking ticket reference and rationale).
   - **Immutable Audit Trail:** All override events (who, when, why, previous state) are permanently recorded in the pull request review timeline and notify original assignees.

## Consequences

**Positive:**
- Eliminates manual maintainer updates by delegating team management to enterprise IDP groups.
- Resolves maintainer review assignment for new package introductions and deletions.
- Prevents release deadlocks by providing phase-aware override authority to responsible release and maintenance engineers.
- Maintains regulatory and security compliance through mandatory justifications and immutable audit logs.

**Negative:**
- Requires periodic synchronization with external enterprise IDP/LDAP services.
- Requires the Workflow Service to track lifecycle phases per project to enforce phase-aware ACLs.

## Considered Options

- **Individual Accounts Only:**
  Rejected due to high administrative overhead, stale assignments, and lack of team coverage.
- **Unrestricted Administrator-Only Overrides:**
  Rejected because routing all routine out-of-office overrides through system administrators creates bottleneck delays during release crunch periods.
- **Unlogged Overrides / Forced PR Merges:**
  Rejected because bypassing reviews without recording reasons violates supply-chain security standards and compliance audits.

## Assumptions
- The enterprise provides an accessible OIDC/LDAP IDP for team group resolution.
- Target projects configure their active lifecycle phase (e.g., Development vs. Maintenance).

Revisit this decision if decentralized identity or multi-party cryptographic threshold signatures replace role-based review overrides.
