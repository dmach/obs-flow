## 1:1 mapping between Git and OBS

### Current State
- Git: branches identified with org, repo, branch
- OBS: projects identified with project name, packages identigied with project name and package name
- There is no clear mapping between them, single git branch can be used in multiple obs packages.

### Requirements
- Users want to be dealing with projects and packages.
- Git structure should be an implementation detail.

### Idea
- Use git orgs to group related projects and their packages together (pool concept).
- Git branch names map to projects; repos are packages, _project repo is project.

#### Distro

| Git Org | Git Repo | Git Branch | | OBS Project | OBS Package |
| - | - | - | - | - | - |
| suse | _project | slfo-main | | suse:slfo-main | |
| suse | bash | slfo-main | | suse:slfo-main | bash |

#### Devel Projects

| Git Org | Git Repo | Git Branch | | OBS Project | OBS Package |
| - | - | - | - | - | - |
| GNOME | _project | factory | | GNOME:factory | |
| GNOME | gtk4 | factory | | GNOME:factory | gtk4 |
| GNOME | gnome-desktop | factory | | GNOME:factory | gnome-desktop |
| GNOME | _project | next | | GNOME:next | |
| GNOME | gtk4 | next | | GNOME:next | gtk4 |
| GNOME | gnome-desktop | next | | GNOME:next | gnome-desktop |

#### Home Projects

| Git Org | Git Repo | Git Branch | | OBS Project | OBS Package |
| - | - | - | - | - | - |
| ~alice | _project | 3d-printing | | home:alice:3d-printing | |
| ~alice | orcaslicer | 3d-printing | | home:alice:3d-printing | orcaslicer |
| ~alice | _project | ai | | home:alice:ai | |
| ~alice | llamacpp | ai | | home:alice:ai | llamacpp |

NOTE: Using ~ as prefix for home orgs to create a namespace, avoiding any collision with regular orgs.


## Pull Requests Are Mutable Too Much

### Current State
- Workflow: make changes in devel project, then open a pull request to Factory.
- Further changes in the devel project **modify** any related open pull requests to Factory.
- This is an unexpected side-effect!
- It doesn't apply to OBS ecosystem, because submitrequests are mutable; Git pull requests are mutable and any changes it their source branch changes them.

### Requirements
- Pull requests must change only upon a user action, not as a side-effect.

### Constraints
- Can't distinguish between a push that should modify an open PR vs a push that only moves code in devel project forward.
- Do not add overhead (no new manual steps, simple workflow).
- Support team work (anyone with sufficient perms can update the PR).

### Idea
- Opening pull requests directly from **devel projects** must be forbidden.
- Opening pull requests directly from **other production branches** must be forbidden.
- We need to create an itermediate branch that would remain frozen for the given pull request unless changed explicitly.
- We need to track relation to the actual source branch or source project, keep the itermediate branch an implementation detail.
- There's a demand to create transient projects (named workspaces?) for submitting changes in multiple packages at once - this might solve the problem.
- We need to create one-off package changes without big overhead.
- Also, package maintainers manage their TODO lists of what needs to be fixed; these workspaces could be the list
- This might also work for security/maintenance workflow in general, need to check how it could work with patchinfo life-cycle.

#### Consider the following being submitted to Factory, Leap 16.1 and SLFO main

| Git Org | Git Repo | Git Branch | | OBS Project | OBS Package |
| - | - | - | - | - | - |
| GNOME | _project | factory | | GNOME:factory | |
| GNOME | gtk4 | factory | | GNOME:factory | gtk4 |
| GNOME | gnome-desktop | factory | | GNOME:factory | gnome-desktop |

#### Freeze the branches by creating workspaces for updating GNOME to 51.0

The branch naming would be: `workspace/<workspace-name>/<org>/<project>`.

| Git Org | Git Repo | Git Branch | | OBS Project | OBS Package |
| - | - | - | - | - | - |
| GNOME | _project | workspace/51.0/opensuse/factory | | GNOME:workspace:51.0:opensuse:factory | |
| GNOME | gtk4 | workspace/51.0/opensuse/factory | | GNOME:workspace:51.0:opensuse:factory | gtk4 |
| GNOME | gnome-desktop | workspace/51.0/opensuse/factory | | GNOME:workspace:51.0:opensuse:factory | gnome-desktop |
| GNOME | _project | workspace/51.0/opensuse/leap-16.1 | | GNOME:workspace:51.0:opensuse:leap-16.1 | |
| GNOME | gtk4 | workspace/51.0/opensuse/leap-16.1 | | GNOME:workspace:51.0:opensuse:leap-16.1 | gtk4 |
| GNOME | gnome-desktop | workspace/51.0/opensuse/leap-16.1 | | GNOME:workspace:51.0:opensuse:leap-16.1 | gnome-desktop |
| GNOME | _project | workspace/51.0/suse/slfo-main | | GNOME:workspace:51.0:suse:slfo-main | |
| GNOME | gtk4 | workspace/51.0/suse/slfo-main | | GNOME:workspace:51.0:suse:slfo-main | gtk4 |
| GNOME | gnome-desktop | workspace/51.0/suse/slfo-main | | GNOME:workspace:51.0:suse:slfo-main | gnome-desktop |

