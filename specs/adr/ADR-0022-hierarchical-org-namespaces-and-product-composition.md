---
id: ADR-0022
date: 2026-11-23
status: proposed
agreed_by: []
supersedes: 
superseded_by: 
---

# ADR-0022: Hierarchical Organization Namespaces and Product Composition Mapping

## Context
ADR-0013 introduced a flat org-based layout where every project is a branch in repositories owned by an organization. However, enterprise distributions produce multiple distinct products (`SLES`, `MLM`, `Public Cloud`, `openSUSE Leap`) that share vast subsets of packages compiled across shared codestreams (`factory`, `slfo-main`, `slfo-1.2`).

Conflating package sources with product compositions causes critical issues:
1. **Repository Duplication:** Duplicating 20,000+ package Git repositories across product lines causes unsustainable storage and synchronization overhead.
2. **Ambiguous Mapping (`SCM-010`):** Defining multiple products inside a single shared project or across ad-hoc branches obscures product boundaries.
3. **Flat Namespace Limitations:** Flat orgs cannot model permission inheritance across product lines or separate developer experimentation from core distribution pools.

Legacy Code 15 releases remain on legacy OBS infrastructure and are excluded from this Git model.

## Decision
We chose to implement a hierarchical namespace (nested groups up to 3 levels deep) that strictly separates the shared package pool, community devel projects, and product family compositions.

1. **Hierarchical Namespace (Max 3 Levels):**
   - Namespaces follow a structured path: `<root-org>/<sub-group>/<repo>.git`.
   - Permissions inherit down the hierarchy: administrators at `<root-org>` inherit access across all underlying product groups, while product maintainers are scoped to `<root-org>/<product>`.

2. **Dedicated Purpose Organizations:**
   - **`pool/` (or `<org>/pool/`):** The single source of truth for software package repositories (`pool/<package>.git`). Branches represent shared distribution codestreams (`factory`, `slfo-main`, `slfo-1.1`, `slfo-1.2`). OBS continuously compiles these branches into standard binary repositories (e.g., `SUSE:SLFO:1.2`).
   - **`devel/` (Community Devel Projects):** Dedicated namespace for community and team development projects (e.g., `devel/gnome/<package>.git`, `devel/languages:python/<package>.git`). Allows teams to stage package stacks before proposing pull requests to the central `pool/`.
   - **Product Family Namespaces (`suse/sles`, `suse/mlm`, `suse/public_cloud`):** Dedicated product organizations holding only composition definitions and product-level release assets:
     - `_project.git`: OBS project definition, architectures, and build flags.
     - `000productcompose.git`: Product Composer specifications defining which binary packages from which OBS codestream repositories are composed into media.
     - `000release-packages.git`: Product release notes, branding, EULAs, and release packages.
     - `kiwi-templates.git`: Appliance and container build recipes.
     - Product family orgs **never** duplicate package source repositories.

3. **Product Releases as Branches (1:1 Mapping):**
   - Each product release corresponds to an exact Git branch across the product family repositories (e.g., `suse/sles` on branch `16.0`, `16.1`).
   - The branch points to the target compiled OBS codestream repository, providing an unambiguous 1:1 mapping between a product release and its composition recipe.

## Consequences

**Positive:**
- Eliminates package repository duplication: package sources exist once in `pool/`.
- Resolves `SCM-010` with a clean 1:1 mapping between product releases and Git branches.
- Provides clean permission inheritance via GitLab-style nested groups without unbounded nesting depth.
- Standardizes devel project locations under `devel/`, avoiding collision with production release spaces.

**Negative:**
- Release Engineers must maintain composition manifests (`000productcompose`) synchronized with active OBS codestream repositories.
- URL routing and filesystem repository managers must enforce the 3-level depth constraint.

## Considered Options

- **Flat Organizations with Prefix Naming:**
  Rejected because flat orgs lack permission inheritance, requiring manual access synchronization across dozens of independent organizations.
- **Duplicating Package Repositories per Product Org:**
  Rejected due to massive storage bloat and fragmented, redundant package maintenance.
- **Unbounded Hierarchical Nesting:**
  Rejected because deeply nested groups lead to unwieldy URLs, complex path parsing, and confusing permission overrides.

## Assumptions
- Product Composer and KIWI consume binary packages built by OBS from `pool/` codestream branches.
- Code 15 maintenance continues on legacy OBS.

Revisit this decision if distribution composition shifts from package-based composition to monolithic tree composition.
