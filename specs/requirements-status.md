# Requirements Status and TODO List

## TODO: Requires Architectural Grilling

These requirements involve complex OBS mechanics (frozenlinks, expanded sources, emergency updates) and require dedicated grilling before drafting ADRs.

- **SCM-002**: Working with upstream expanded sources instead of using a tarball. In particular, Virtualization team works with downstream repos without using patch files.
- **STAGING-002**: Re-introduce freezing for staging projects (frozenlinks)
- **SCM-007**: It should be easy to cherry-pick upstream bugfixes when working with downstream repos (e.g. git subtrees are cumbersome)
- **BUILD-002**: Providing a way to trigger an high prio event (right now Java packagers use a trick: add a comment in _config)
- **BUILD-004**: It should be possible to create a project PR with _config changes from a Devel project to official product without having to adapt project name inside.  * Already discussed with Adrian: they could use macros
- **MAINTENANCE-001**: Final patchinfo doesn’t have final ID (too long, truncated, no longer unique)
- **UI/UX-017**: Enforce/automate configuration changes needed when moving from development/GA to maintenance.
- **MAINTENANCE-002**: The Gitea Action for the patchinfo numerator must be configured and enabled in the MLM 5.2 packages Git repository (in addition to the product compose repository).
- **MAINTENANCE-003**: The automated workflow on the packages repository must ensure that the updateinfo ID is properly populated by the numerator prior to release, preventing fallback to the default string (product-IBSproject-patchinfoName)
- **MAINTENANCE-004**: Implement an automated check that validates the XML syntax and schema of any added or modified patchinfo files. The validator must check not only XML well-formedness, but also the presence of all required IBS metadata (replicating the validation rules of the legacy IBS workflow).
- **UI/UX-021**: Unable to do maintenance fast, need to wait until integrations tests finish etc.
- **STAGING-006**: Managing staging (project PRs) manually to detect changes in package PR and modify patchinfo accordingly.
- **UI/UX-022**: Maintenance workflow is different to development workflow.
- **BUILD-008**: The current workflow does not allow for emergency updates in a timely manner due to the two-stage build process. Maintenance coordination needs to revert untested updates in slf0-* to prioritize an EU.
- **STAGING-008**: As a release engineer, I want to configure and use both permanent and throwaway staging projects within the same staging workflow, so I can balance fast incremental builds for core packages with isolated testing for standalone submissions. I want permanent staging projects to retain previously built binaries across staging cycles so that subsequent submissions rebuild incrementally rather than from scratch.

## OUT OF SCOPE

- **SCM-001**: API to show tarball differences
  - *Reason:* Explicitly out of scope per maintainer decision.
- **BUILD-001**: The build time on ARM is 5 times higher  than the respective x86_64.
  - *Reason:* Hardware / OBS Worker Infrastructure.
- **UI/UX-008**: Provide a way to get if a patch is in our package.
  - *Reason:* Tooling / Code search scope.
- **UI/UX-009**: Provide a way to check if a specific Bugzilla/PED ticket has been released, as well as which product releases contain it.
  - *Reason:* Release tracker integration.
- **BUILD-003**: Product composer doesn't support debian packages.  * Already discussed with Adrian: if it's mainly related to the produtcompose file needed for SCC we should find another way
  - *Reason:* Product Composer toolchain integration.
- **SCM-009**: Remove vendored (bundled) packages from project git repos. They are difficult to discover and work with. Use submodules only.
  - *Reason:* Developer policy, not SCM architecture.
- **UI/UX-023**: PTF workflow is different to other workflows, using Git infrastructure, but not Git Workflow directly. Every PTF is a micro-codestream.
  - *Reason:* PTF workflows must adapt to standard Workspaces.
- **BUILD-007**: Have older buildenv available to rebuild packages in their original build environment.
  - *Reason:* OBS Backend / Infrastructure retention policy.
- **API-004**: Automated creation of PTF project + packages for source changes.
  - *Reason:* PTF workflows must adapt to standard Workspaces.
- **UI/UX-026**: It would be great to have an integrated issue management system as a replacement for code.opensuse.org.
  - *Reason:* General-purpose issue tracking system.

## COVERED BY EXISTING ADRs

| ID | Summary | ADR |
| :--- | :--- | :--- |
| **STAGING-001** | Staging PRs merge action should be decoupled from reviews | [ADR-0007](adr/ADR-0007-staging-batches.md) |
| **UI/UX-001** | One API to rule them all | [ADR-0003](adr/ADR-0003-rpc-style-api-design.md), [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **REVIEW-001** | Don't re-ask for human reviews when changing staging content | [ADR-0011](adr/ADR-0011-review-request-debouncing.md), [ADR-0012](adr/ADR-0012-review-dependencies-and-workflow-orchestration.md) |
| **MAINTAINERS-001** | Support group assignment in package maintainership (for new package process) | [ADR-0023](adr/ADR-0023-enterprise-maintainership-and-review-overrides.md) |
| **REVIEW-002** | Product-Scoped Branches: Evaluate changes strictly in the scope of their destination product. | [ADR-0010](adr/ADR-0010-path-scoped-reviews-and-decision-inheritance.md) |
| **REVIEW-003** | Single-Package Pull Requests: Refrain from combining updates across separate packages in one PR | [ADR-0013](adr/ADR-0013-org-based-git-forge.md) |
| **SCM-003** | Enforce a unique project definition structure (e.g. all packages should be submodules) | [ADR-0013](adr/ADR-0013-org-based-git-forge.md), [ADR-0018](adr/ADR-0018-githook-forbidden-files-validation.md) |
| **API-001** | API to retrieve all PRs for which a user or group has been requested to review. | [ADR-0003](adr/ADR-0003-rpc-style-api-design.md) |
| **REVIEW-004** | We should enforce a rule requiring at least two groups to review common criteria products. | [ADR-0009](adr/ADR-0009-creating-reviews-from-review-configs.md) |
| **ADMIN-001** | Eliminate Multi-Platform Administration | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **UI/UX-002** | Provide Detailed User-Facing Errors: The missing client-side error notifications adds to the admin workload. It leads to poor UX. | [ADR-0006](adr/ADR-0006-server-driven-ui-with-htmx.md) |
| **UI/UX-003** | All API call should provide a feeback. Now, unpredictable bot response times: This stems from background operations lacking progress indicators or real-time status updates inside PR threads. | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **UI/UX-004** | Git LFS issues: Using Git LFS creates significant operational complications for the team. Purging files from the Git tree that should have been LFS pointers requires rewriting the commit history. | [ADR-0019](adr/ADR-0019-githook-git-lfs-attribute-consistency.md), [ADR-0020](adr/ADR-0020-githook-git-lfs-object-verification.md) |
| **ADMIN-002** | Automated ACLs: Access controls and branch protection rules should be generated automatically. | [ADR-0014](adr/ADR-0014-git-transport-and-authorization.md) |
| **REVIEW-005** | Overrides for reviews with an explicit justification - design ACLs - needs to be per review. We need to allow release/maintenance to override automatic bot reviews or we need to override a review when a team member is out of office. | [ADR-0023](adr/ADR-0023-enterprise-maintainership-and-review-overrides.md) |
| **REVIEW-006** | Feature: conditional reviews: bot/tool can’t decide -> ask human | [ADR-0009](adr/ADR-0009-creating-reviews-from-review-configs.md) |
| **REVIEW-007** | If package PR author is a maintainer, it shouldn't review its own work. | [ADR-0009](adr/ADR-0009-creating-reviews-from-review-configs.md) |
| **MAINTAINERS-002** | Package maintainers added in new package requests shall be added as reviewers. Applies also to kernel lifepatches that are treated as new packages. | [ADR-0023](adr/ADR-0023-enterprise-maintainership-and-review-overrides.md) |
| **MAINTAINERS-003** | Package maintainers should be notified when a product deletes a package they are maintaining via a deletion request. | [ADR-0023](adr/ADR-0023-enterprise-maintainership-and-review-overrides.md) |
| **API-002** | Provide an API to figure out where the sources to be fixed live (e.g. which is the devel project) | [ADR-0022](adr/ADR-0022-hierarchical-org-namespaces-and-product-composition.md) |
| **SCM-004** | Provide an easy way to forward changes from Factory to other codestreams | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **SCM-005** | Bring factory in Git / Fix unrelated histories problems | [ADR-0013](adr/ADR-0013-org-based-git-forge.md) |
| **SCM-006** | One-to-one mapping between Git and OBS projects and packages | [ADR-0013](adr/ADR-0013-org-based-git-forge.md), [ADR-0022](adr/ADR-0022-hierarchical-org-namespaces-and-product-composition.md) |
| **MAINTAINERS-004** | Validation of package maintainers metadata | [ADR-0023](adr/ADR-0023-enterprise-maintainership-and-review-overrides.md) |
| **MAINTAINERS-005** | One global definition for maintainers with possibility to override per project base | [ADR-0023](adr/ADR-0023-enterprise-maintainership-and-review-overrides.md) |
| **MAINTAINERS-006** | Getting all packages maintained by an IDP team | [ADR-0023](adr/ADR-0023-enterprise-maintainership-and-review-overrides.md) |
| **UI/UX-005** | Need for project/package build results (SVG implementation is an hack) | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **UI/UX-006** | Missing metadata for osc (e.g. Packaging team has to use --alternative-project for osc build, Virtualization team needs to run git-obs meta before osc service mr). | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-007** | Tool that allows to create a workspace for working on a fix for multiple codestreams (https://gitlab.suse.de/david.anes/packaton) | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-010** | Provide a way to search which product is providing a certain package. | [ADR-0022](adr/ADR-0022-hierarchical-org-namespaces-and-product-composition.md) |
| **UI/UX-011** | Multiple CLI tools (osc/git-obs and git) | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **STAGING-003** | Provide a way for packagers to share their staging projects with the release or maintenance team. This makes work on Elemental really time consuming. | [ADR-0007](adr/ADR-0007-staging-batches.md) |
| **STAGING-004** | Provide a way to specify staging project dependencies with the release or maintenance team. | [ADR-0007](adr/ADR-0007-staging-batches.md) |
| **STAGING-005** | Provide a way to define which packages should be grouped together in the same staging project. | [ADR-0007](adr/ADR-0007-staging-batches.md) |
| **UI/UX-012** | Provide a way to view the list of packages in a git project. | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **UI/UX-013** | Devel project integration is not working as legacy OBS | [ADR-0022](adr/ADR-0022-hierarchical-org-namespaces-and-product-composition.md) |
| **API-003** | Create pull requests completely via API (incl. the code changes) | [ADR-0003](adr/ADR-0003-rpc-style-api-design.md) |
| **SCM-008** | Support storing patches as individual files in a subdirectory. Currently not working because we still use the old OBS source backend that doesn't support subdirectories and Git is synced to it. | [ADR-0018](adr/ADR-0018-githook-forbidden-files-validation.md) |
| **BUILD-005** | QE tests: 2-stage builds, what we ship is not what we’ve tested | [ADR-0016](adr/ADR-0016-target-source-rebuild-with-reproducible-checks.md) |
| **UI/UX-014** | Too many branches, no inheritance of metadata. Source branch cannot be reused for multiple PRs. e.g. (Dirk) create a PR only to slfo-main that applies automatically to all other slfo-X.Y branches | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-015** | Only PR creator and target repo collaborators can modify a PR. We need a way to enable a team to work on the same PR. | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-016** | Manage project and package properties such if it builds and where, debuginfo, publishing etc. (== changing _meta via webui) | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **BUILD-006** | Be able to build packages from branches that are not directly associated with a project. (most of the branches used for submitting PRs) | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **SCM-010** | (One-to-one?) mapping between Git and products | [ADR-0022](adr/ADR-0022-hierarchical-org-namespaces-and-product-composition.md) |
| **SCM-011** | Create a place (a temporary project?) to develop changes of multiple packages and then create related pull requests | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-018** | Difficult to track progress of pull requests, partially due to split (forwarded) PRs with their status. | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **MAINTENANCE-005** | Support for embargoed / private fixes | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-019** | Lack of information about where each repo gets synced (e.g. pushing security sensitive info into internal repo may get mirrored to a public repo) | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **UI/UX-020** | Too many commands or steps required to perform a single action | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **SCM-012** | Extract information from RPM headers to determine it's source. | [ADR-0016](adr/ADR-0016-target-source-rebuild-with-reproducible-checks.md) |
| **REVIEW-008** | A PR created from an official Devel project by one of the maintainers should not require another review from the same team. (Conditional Reviews) | [ADR-0009](adr/ADR-0009-creating-reviews-from-review-configs.md) |
| **UI/UX-024** | Package branch shall be easy via the webui (it must automatically create an OBS project where to test changes, not only a Gitea fork) E.g. OEM images | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-025** | It should be easy to add a new package/update an existing package to Leap (we should hide PackageHub internal complexity) | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-027** | It would be great to link an issue/epic to all PRs to easily report status back. | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-028** | Conditional reviews: assurance that the package has been built before running tests. | [ADR-0012](adr/ADR-0012-review-dependencies-and-workflow-orchestration.md) |
| **UI/UX-029** | Conditional reviews: Reviews shall not be requested for only bot configuration changes. | [ADR-0009](adr/ADR-0009-creating-reviews-from-review-configs.md) |
| **UI/UX-030** | The Project UI should not take that long to load, even with multiple packages. | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **UI/UX-031** | Better to have server side actions (remind about people in Asia/Australia) | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **UI/UX-032** | Tools are not designed to work with a lot of package submissions. | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **API-005** | An API is needed to return a diff of a package file. | [ADR-0003](adr/ADR-0003-rpc-style-api-design.md) |
| **API-006** | An API is needed that returns the version of a package. | [ADR-0003](adr/ADR-0003-rpc-style-api-design.md) |
| **UI/UX-033** | We need support for old multi-action submit requests. Inside a devel project, we don't want to review multiple single PRs. | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-034** | Multiple commands are needed to forward changes from factory to slfo-*. | [ADR-0021](adr/ADR-0021-workspaces-multi-codestream-forwarding.md) |
| **UI/UX-035** | No overview of packages that have a PR for a given branch/product. | [ADR-0015](adr/ADR-0015-custom-git-forge-for-distribution-workflows.md) |
| **UI/UX-036** | I want to view a consolidated list of all source packages included in a product once its Pull Requests (PRs) are approved,  So that I can track the exact composition, dependencies, and release readiness of the product. | [ADR-0022](adr/ADR-0022-hierarchical-org-namespaces-and-product-composition.md) |
| **UI/UX-037** | As a package maintainer, I want to see the linked devel project on the package overview page so I know where to submit fixes or check upstream changes. | [ADR-0022](adr/ADR-0022-hierarchical-org-namespaces-and-product-composition.md) |
| **UI/UX-038** | As a package maintainer, I want a link from my PR/submitreq to the staging project where it is being built, so I can quickly check for build errors or missing package dependencies. | [ADR-0007](adr/ADR-0007-staging-batches.md) |
| **STAGING-007** | As a release engineer (or staging manager), I want to assign submit requests for new packages and delete requests to a staging project so I can verify that adding or removing packages doesn't break dependencies or builds in the target distribution before accepting them. | [ADR-0007](adr/ADR-0007-staging-batches.md) |
| **REVIEW-009** | As a release engineer, I want to work only with immutable PRs (pinned to a fixed revision/commit) when staging, so that my staging projects remain stable during testing and maintainers cannot unintentionally alter staged content simply by pushing new changes to a branch. | [ADR-0008](adr/ADR-0008-revision-identity-and-immutability.md) |
