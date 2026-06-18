# Use Cases: Pull Request Reviews

This document presents a structured User Story Map for Pull Request Reviews.

---

## Actor Role Glossary

- **[AUTHOR]**: The developer who submitted the pull request.
- **[REVIEWER]**: An individual reviewer, either a person or an automated tool that approves/rejects the changes in the pull request.
- **[GROUP-REVIEWER]**: A member of a review team that represents a certain role or type of review. This role allows performing reviews on behalf of different review groups.
- **[MANAGER]**: The team lead tracking queue health and tuning priorities.
- **[RELENG]**: The integrator of bulk project changes who cross-references source changes with issues or bugs.

---

## Context
*Information a reviewer should know before performing the review, because it impacts how the changes are reviewed.*

- [REVIEW-CONTEXT-1] The previous review state and justification.
- [REVIEW-CONTEXT-2] The identity of the pull request author, which helps to understand if it comes from a trusted source.
- [REVIEW-CONTEXT-3] The target project and package in OBS.
- [REVIEW-CONTEXT-4] The source project and package in OBS.
- [REVIEW-CONTEXT-5] The target owner/repo:branch.
- [REVIEW-CONTEXT-6] The source owner/repo:branch.
- [REVIEW-CONTEXT-7] The source SHA (head SHA).
- [REVIEW-CONTEXT-8] The target SHA (base SHA).
- [REVIEW-CONTEXT-9] Whether the pull request is a draft.
- [REVIEW-CONTEXT-10] Bug references (including issues, CVEs, etc.) related to the pull request.
- [REVIEW-CONTEXT-11] Justification for changes in the pull request (such as dropped patches or bugs not described in the changes file).
- [REVIEW-CONTEXT-12] The diff against the previous version of the repository (diff versus base).
- [REVIEW-CONTEXT-13] The diff against the previously approved pull request revision by the same reviewer.
- [REVIEW-CONTEXT-14] Build results (in many cases requires staging first)

---

## Backlog
*Managing the review backlog, including priorities.*

- [REVIEW-BACKLOG-1] Increase the priority of certain reviews (either manually or via a rules engine) so they get reviewed first. [MANAGER]
- [REVIEW-BACKLOG-2] Order the review queue by priority and creation date by default. [MANAGER]
- [REVIEW-BACKLOG-3] Review selected pull requests without following the queue. [REVIEWER]
- [REVIEW-BACKLOG-4] Display the review queue for a selected reviewer. [REVIEWER, GROUP-REVIEWER]

---

## Group Reviews
*Support for distributed teams to perform group reviews.*

- [REVIEW-GROUPS-1] List all pull requests that require a review by the given group. [GROUP-REVIEWER]
- [REVIEW-GROUPS-2] Temporarily lock a group review to myself. [GROUP-REVIEWER]
- [REVIEW-GROUPS-3] The review lock lasts while I am reviewing. [GROUP-REVIEWER]
- [REVIEW-GROUPS-4] Store my login as part of the review decision, but keep the review assigned to the original group. [GROUP-REVIEWER]

---

## Queries
- [REVIEW-QUERY-1] List all reviews that are assigned to a team member who is currently unavailable. [MANAGER]
- [REVIEW-QUERY-2] List stale reviews. [MANAGER]

---

## Feedback Loop
*The interactive phase where reviewers communicate with the author in a feedback loop.*

- [REVIEW-FEEDBACK-1] Leave an informative comment associated with a review without changing the review state. [REVIEWER]
- [REVIEW-FEEDBACK-2] Ask the author for additional information, and remove the review from the backlog until that information is provided. [REVIEWER]
- [REVIEW-FEEDBACK-3] Provide the information requested by a reviewer, and restart the review. [AUTHOR]

---

## Decision
*The conclusion of the review where final state is recorded.*

- [REVIEW-DECISION-1] Accept the review. [REVIEWER]
- [REVIEW-DECISION-2] Reject the review while providing a justification for my decision. [REVIEWER]
- [REVIEW-DECISION-3] Override the review result with a justification (state "overridden", track the actor). [REVIEWER]
- [REVIEW-DECISION-4] Re-request a review while providing a justification. [AUTHOR, RELENG]

---

## Unsorted
- Keep the review out of the backlog if an automated test related to the review fails. [REVIEWER]
- Delegate personal reviews to another user when going on vacation. [REVIEWER]
- Delegate personal reviews from one team member to another. [MANAGER]

- GIT: submodules update, relative paths, LFS checks, metadata checks, store review states + other metadata to git (into merge commit?), handling subdirs (_manifest), 
- *additional* checks defined in a project/package
