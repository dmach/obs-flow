# obs-flow
- (OBS) Flow is workflow orchestration service for the Open Build Service, aiming to simplify and replace parts of Git Packaging Workflow.
- It is currently in an **early phase of gathering ideas**, user stories and technical decisions.
- There is no ongoing implementation (yet?).
- The documents will change a lot in the next weeks, you may expect even some force-pushes.


## Design Documents
- [Requirements](specs/requirements.md)
- [Tech Stack](specs/tech-stack.md)
- [User Stories: Pull Requests](specs/user-stories-pull-requests.md)
- [User Stories: Reviews](specs/user-stories-reviews.md)
- [User Stories: Staging](specs/user-stories-staging.md)

## Issues with Git Packaging Workflow
- Gitea contains random git repos. After cloning one, it's not clear if it is a project, package or something else.
- Multiple OBS projects or packages can use a single git owner/repo:branch; making changes in such branch has side-effects.
- Project git contains metadata such as workflow.config and staging.config that contain references to OBS projects.
  - TL;DR: 1:1 mapping between the project/package and underlying source as it was done in OBS is a good design choice.
  - Circular reference (project points to git via scmurl, git points back via configs).
  - Forking a project or making a snapshot or mirroring it doesn't make much sense, because we most likely want the workflow and staging config to be different.
  - These configs are part of context of pull request reviews, because they refer to the target project. It that changes, we must redo the reviews.
  - Also, the OBS prj/pac vs Gitea owner/repo:branch disconnect negatively impacts user experience.

## TODO
- consider using Architecture Decision Records (ADRs) for design decisions
  - one decision in one file
  - create an AI skill to help with that?
  - rewrite tech-stack.md using this
- explain how to read and write the specs
- use identifiers in the specs that can be referenced in the tests and documentation
- set branches to be automatically in sync with a given branch; that would require doing automatic fast-forwards and also protecting the branches from arbitrary pushes via git hooks (and ideally transactional changes across multiple branches)
- branch life cycle - delete unneeded branches, preserve devel projects etc.
- sync with Gitea (PR revisions)
- ACLs based on Gitea perms
- auth
  - do we need any special system accounts? (avoid collisions with the external source of usernames)
- staging rule engine:
  - add to an existing group if it's still collecting
  - stay in the backlog
  - create a new group (race conditions!) and become part of it
  - based on package name (prefix?)
  - based on devel project (list of projects? globs?)
  - schedule staging batch creation?
  - schedule staging batch branch state
- how to report results from background jobs?
  - closing/merging a pull request fails; if it runs in a background job, the result should be accessible via the PR page
