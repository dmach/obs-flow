# Use Cases: Pull Requests

This document presents a structured User Story Map for Pull Requests.

---

## Queries
- [PULL-QUERY-1] Filter pull requests by the target project and package in OBS.
- [PULL-QUERY-2] Filter pull requests by the source project and package in OBS.
- [PULL-QUERY-3] Filter pull requests by the target owner, repository, and branch.
- [PULL-QUERY-4] Filter pull requests by the source owner, repository, and branch.
- [PULL-QUERY-5] Filter pull requests by the draft status.
- [PULL-QUERY-6] Filter pull requests by related bug references (including issues, CVEs, etc.). [RELENG]

---

## Gating
- [PULL-GATING-1] Set the pull request as blocked (with justification) to prevent it from merging. [RELENG]
- [PULL-GATING-2] Clear the blocked flag (with justification) to allow merging again. [RELENG]
