# Database Schema
- This document presents the anticipated design of the database schema.
- For simplicity, we don't make any difference between database schema and ORM models in this document.


## Assumptions

### Architecture & Source of Truth
- **Workflow Source of Truth:** While Pull Requests originate in Gitea, this Service is the absolute source of truth for all workflow states (Reviews, Gating (TODO: confirm), Staging).
- **Synchronization:** The Service mirrors Gitea Pull Requests. Skipping any intermediate Gitea state doesn't matter, we the Service always synchronizes the currently latest state.
- **Immutable Identifiers:** Core identifiers (project names, package names, usernames, group names) MUST NOT change after creation. Renames are forbidden by design.

### Audit Trail & Data Integrity
- **Append-Only History:** Unless explicitly stated otherwise, all state-changing models MUST generate an immutable audit trail on change. Data is revoked/superseded, never deleted.

### Pull Requests & Revisions
- **Target Branch Stability:** The target branch of a Pull Request MUST NOT change. If it changes in Gitea, the Service should close the PR or handle it as an invalid state.
- **Immutable Revisions:** Pull Requests are tracked via immutable revisions. Any change to the source code (`head_sha`) triggers a new revision.
- **Revision-Bound Workflow:** All reviews, test results, and staging decisions are strictly tied to a specific pull request revision, not the pull request as a whole.

### Staging
- **Multiple Active Batches:** A Pull Request SHOULD typically belong to only one active Staging Batch at any given time, but it is technically possible to include it in multiple concurrent Staging Batches if necessary. The first Staging Batch to complete successfully will merge the Pull Request; subsequent batches containing the same Pull Request will either treat it as a no-op (if already merged) or must resolve any resulting conflicts.
- **Single Target Project:** A Staging Batch can target only one project at a time. Mixing pull requests targeting different projects within a single batch is forbidden (must be enforced by application logic).


## Authentication & Users

### User
Represents a human user, a bot, or an internal system account.
- `username` (String)
- `username_lower` (String, unique): Used for case-insensitive uniqueness enforcement.
- `full_name` (String, null)
- `email` (String, unique, null)
- `description` (String, null): Description of the bot and system users.
- `oidc_sub` (UUID, unique, null): Stable identifier from the Identity Provider (e.g., Authentik).
- `account_type` (Enum: `human`, `bot`, `system`): Differentiates regular users from automated actors.
- `is_active` (Boolean, default=True): Soft-disable for users who left.
TODO: determine if usernames in OBS can change
TODO: determine how OBS users map to oidc_sub
TODO: lazy user sync from OBS? User.objects.get_or_create(username=...)
TODO: how to sync users? what is_active means exactly?
TODO: data we own vs cache; clearly mark entries that should be synced vs those we manage internally (service accounts); a flag? time of last sync?
TODO: roles (maintainer, reader, bugowner, ...); git workflow has only maintainers; maybe explain why we don't need/want these any more

### Group
Represents a team of users, mapped from OBS. Used for group-based reviews and ACLs (TODO: confirm).
- `name` (String)
- `name_lower` (String, unique): Used for case-insensitive uniqueness enforcement.
- `email` (String, unique, null): Mailing list for the group.
- `description` (String, null)

### UserGroup (M2M)
Maps users to groups.
- `user` (FK to User)
- `group` (FK to Group)
- *Constraint:* `unique_together(user, group)`


## Git Forge & OBS Entities

### Project
Represents an OBS Project.
- `name` (String, unique): The stable OBS project name (e.g., `SUSE:SLFO:1.0`).
TODO: project inheritance is possible in OBS - possibly out of scope for git based workflow
      check how it works for community projects, devel projects; we don't use this at all with pool/ and products/

### Package
Represents an OBS Package within a Project.
- `project` (FK to Project)
- `name` (String): The OBS package name.
- *Constraint:* `unique_together(project, name)`
TODO: how to populate? A githook on every project git change?

### GitMapping
Maps a specific Git branch to exactly one OBS entity.
- `owner` (String)
- `repo` (String)
- `branch` (String)
- `project` (FK to Project, null=True, unique=True)
- `package` (FK to Package, null=True, unique=True)
- *Constraint:* Django UniqueConstraint using `Lower('owner')` and `Lower('repo')` with `branch`.
- *Constraint:* Django CheckConstraint (XOR): Exactly one of `project` or `package` MUST be set.


## Pull Requests

### PullRequest
Represents a Gitea Pull Request.
- `target` (FK to GitMapping): The destination branch. This implicitly links the PR to exactly one Project or Package.
- NOTE: `owner` and `repo` are part of GitMapping
- `number` (Integer): The PR number in Gitea.
- `author` (FK to User)
- `state` (Enum: `open`, `closed`, `merged`)
- `title` (String, null)
- `is_draft` (Boolean)
- `source_owner` (String): The owner of the fork/repo where the changes originate.
- `source_repo` (String): The repository where the changes originate.
- `source_branch` (String): The branch containing the changes.
- *Constraint:* `unique_together(target, number)`

### PullRequestRevision
An immutable snapshot of a Pull Request's state. A new revision is created whenever the source code (`head_sha`) changes.
- `pull_request` (FK to PullRequest)
- `revision_number` (Integer): Incremental number (1, 2, 3...).
- `head_sha` (String): The commit SHA of the source branch.
- `base_sha` (String): The commit SHA of the target branch at the time of revision creation.
- `created_at` (DateTime)
- *Constraint:* `unique_together(pull_request, revision_number)`


## Review Configuration

### ReviewConfigurationBase (Abstract)
Shared fields for all types of review configuration.
- `type` (Enum: `project`, `package`, `staging`)
- `reviewer_user` (FK to User, null=True)
- `reviewer_group` (FK to Group, null=True)
- `dynamic_role` (Enum: `maintainer`, `...`, null=True): Special handling for project/package maintainers which are different per project/package.
- `depends_on` (FK to Self, null=True)
- *Constraint:* Django CheckConstraint (XOR): Exactly one of `reviewer_user`, `reviewer_group`, or `dynamic_role` MUST be set.
- *Constraint:* Application-level validation: `depends_on` MUST reference an entry within the same project and MUST NOT point to itself.
TODO: depends_on is probably not sufficient, we may need M2M
TODO: dynamic_role needs a design discussion

### ReviewConfiguration
Defines review rules at the project level. Applies to the project, all packages or all stagings at the project level.
- Inherits all fields from `ReviewConfigurationBase`
- `project` (FK to Project)
- *Constraint:* Django UniqueConstraints with conditions (e.g., `condition=Q(reviewer_user__isnull=False)`) for each of the three reviewer types to prevent duplicate rules per project.

### ReviewConfigurationOverride
Defines review overrides at the package level.
NOTE: probably skip for now, Git Workflow doesn't support it either.
- Inherits all fields from `ReviewConfigurationBase`
- `package` (FK to Package)
- `mode` (Enum: `add`, `remove`)
- *Constraint:* Django CheckConstraint: `depends_on` MUST be NULL when `mode` is `remove`.
- *Constraint:* Django UniqueConstraints with conditions for each of the three reviewer types to prevent duplicate rules per package.


## Reviews

### BaseReview (Abstract)
Shared fields for all types of reviews.
- Has most of the fields identical to `ReviewConfigurationBase` excluding `type`:
- `reviewer_user` (FK to User, null=True): Set if the review was assigned to a specific user.
- `reviewer_group` (FK to Group, null=True): Set if the review was assigned to a group.
- `dynamic_role` (Enum: `maintainer`, `...`, null=True): Special handling for project/package maintainers which are different per project/package.
- `depends_on` (FK to Self, null=True)
- *Constraint:* Django CheckConstraint (XOR): Exactly one of `reviewer_user`, `reviewer_group`, or `dynamic_role` MUST be set.
- *Constraint:* Application-level validation: `depends_on` MUST reference an entry within the same project and MUST NOT point to itself.
- Additional fields:
- `actor` (FK to User, null=True): The actual human who submitted the decision. Null while pending. Maybe we could take the actor from the audit trail.
- `state` (Enum: `waiting`, `pending`, `needinfo`, `accepted`, `rejected`, `overridden`)
    TODO: who can override a state? project maintainers? release managers? bot account owners?
    TODO: define `needinfo` behavior; expects action from PR or Staging author and clearing the flag to unblock the review.
    TODO: review states (design discussion)
- `justification` (Text, null): Mandatory for `needinfo`, `rejected` and `overridden`, resets on `state` change.
- `external_review_url` (URL, null): URL of external review results, such as log or a page in a different service.
- `locked_by` (FK to User, null=True): Temporary lock for group reviews.
- `locked_until` (DateTime, null=True): Expiration time for the lock. If `locked_until` is in the past, the lock is considered expired and ignored.
- *Constraint:* Django CheckConstraint: `actor` is NULL when `state` is 'waiting' or 'pending', and NOT NULL otherwise.
- *Constraint:* Django CheckConstraint: `justification` is NOT NULL when `state` is 'needinfo', 'rejected', or 'overridden'.
- *Constraint:* Django CheckConstraint: `locked_by` and `locked_until` MUST both be NULL or both be NOT NULL.
TODO: external_review_url - clarify what it means; mainly pointer to a log of an automated check

### PullRequestReview
Records a review decision made on a specific Pull Request Revision.
- Inherits all fields from `BaseReview`.
- `revision` (FK to PullRequestRevision)
- *Constraint:* Django UniqueConstraints with conditions (e.g., `condition=Q(reviewer_user__isnull=False)`) for each of the three reviewer types to prevent duplicate reviews.

### StagingReview
Records a review decision made on a specific StagingBatch.
TODO: Does Staging also need revisions?
- Inherits all fields from `BaseReview`.
- `staging` (FK to StagingBatch)
- *Constraint:* Django UniqueConstraints with conditions (e.g., `condition=Q(reviewer_user__isnull=False)`) for each of the three reviewer types to prevent duplicate reviews.


## Staging

### StagingBatch
Represents a group of Pull Requests being integrated and tested together.
- `project` (FK to Project): The target project for this batch. All included pull requests must target this project or packages within it (enforced by application logic).
- `title` (String, null): A descriptive title of the staging group.
- `description` (String, null)
- `state` (Enum: `collecting`, `in-progress/open`, `pending-release`, `merged/completed`, `failed`)
- `author` (FK to User, null=True): The user who created the batch (null if automated).
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `closed_at` (DateTime, null=True)
- `collecting_until` (DateTime, null=True): When the batch stops accepting new PRs.
- `release_date` (DateTime, null=True): Planned release date.
- `embargo_date` (DateTime, null=True): For security updates.
- *Constraint:* Django CheckConstraint: `closed_at` is set if and only if `state` is 'merged/completed' or 'failed'.

### StagingBatchPullRequest (M2M)
Maps Pull Requests to Staging Batches, allowing a Pull Request to belong to multiple Staging Batches.
- `staging_batch` (FK to StagingBatch)
- `pull_request` (FK to PullRequest)
- *Constraint:* `unique_together(staging_batch, pull_request)`

TODO: categorizing PRs for staging (== working with staging backlog)
- prevent touching a single PR in backlog multiple times
- forwarded PRs are needed now
- generate a git ref with project change for the package PR?


## Bugs & Issues

### IssueTracker
Represents an external issue tracker (e.g., Bugzilla, Jira, GitHub, CVE database) configured in the system. We mirror this configuration to generate correct links, but we do not fetch issue details from the remote servers. A copy of /issue_trackers from OBS.
- `name` (String, unique): The short name of the tracker (e.g., `bnc`, `cve`, `gh`).
- `kind` (Enum: `other`, `bugzilla`, `cve`, `fate`, `trac`, `launchpad`, `sourceforge`, `github`, `jira`, `debbugs`): The type of the issue tracker.
- `description` (String, null)
- `url` (String): The base URL of the issue tracker.
- `show_url` (String, null): The URL template to show an issue (e.g., `https://bugzilla.suse.com/show_bug.cgi?id=@@@`).
- `regex` (String): Regular expression used to identify issue references in text.
- `label` (Text): The label used in the UI.

### Issue
Represents a specific issue/bug/CVE tracked in an external system.
- `issue_tracker` (FK to IssueTracker)
- `name` (String): The identifier of the issue in the external tracker (e.g., `123456`, `CVE-2023-1234`).
- *Constraint:* `unique_together(issue_tracker, name)`

### PullRequestRevisionIssue (M2M)
Maps Pull Requests to Issues they address or reference.
- `pull_request_revision` (FK to PullRequestRevision)
- `issue` (FK to Issue)
- *Constraint:* `unique_together(pull_request, issue)`
TODO: Evaluate the need for reference counting. We may need that for producing issue diffs.
TODO: the latest revision has the actual bug references for the pull request
