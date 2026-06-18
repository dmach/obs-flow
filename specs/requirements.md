# Requirements
- This document presents technical requirements (the HOW) of the project.


## Conformance
- The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL"
  in this document are to be interpreted as described in [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).


## Glossary
- **the Service**: The Open Build Service workflow orchestration service specified in this document.


## Executive Summary
- The Service implements resilient, enterprise grade workflow for Open Build Service with Git SCM.
- The Service is the source of truth that orchestrates the workflow.
- Everything is designed with idempotency in mind (applying the state from the source of truth, multiple identical operations always lead to the same result).


## Pull Request Synchronization
- The Service MUST mirror every Gitea pull request (PR) upon its creation or modification.

### Synchronization Reliability
- Gitea Webhooks MUST NOT be the sole mechanism for synchronization because they are unreliable:
  - If the Service is down, it doesn't receive any notifications.
  - Gitea job queue is FIFO, but the jobs are processed in parallel, and they might be delayed on retries, etc.
  - The receiver of the webhooks generally processes them in parallel and doesn't guarantee any order.
- The Service MUST implement alternative or fallback mechanisms to ensure reliable synchronization.

### Revisions
- Working with only the pull request ID (`owner/repo#number`) is insufficient.
- Pull request contents change over time, which causes race conditions and unclear states.
- The Service MUST break down pull requests into immutable revisions to mitigate this issue.
- The Service MUST create a new pull request revision every time the `head SHA` or `target branch` changes.
- The human-readable ID of a revision SHOULD follow the format `owner/repo#number.revision`.
- The current state of the pull request MUST be defined by the state of its latest revision.
- All reviews and tests MUST be associated with a specific pull request revision.
- Actions on a revision MUST be idempotent. They MUST always produce the same results.

### Mapping to OBS
- The Service MUST map each mirrored pull request to an OBS project and package.
- This binding MUST provide the context of the pull request:
  - Project configuration.
  - The Service MUST provide access to the project configuration via API. (TODO: too vague, clarify details)
  - Build environment.


## Source Reviews
- Every pull request MUST be reviewed by all reviewers defined in the project configuration.
- Reviews MUST be associated with pull request revisions.
- A pull request passes reviews when its latest revision passes reviews.


## Integration Batches (Staging)
- Batch is a group of pull requests + metadata.
- Every pull request MUST map to 0 or 1 batch. (TODO: verify with stakeholders, maybe make configurable)
- Batch is considered ready to be integrated when all associated pull requests are reviewed.


## Synchronicity vs Asynchronicity
- All operations SHOULD be synchronous by default.
- If an operation takes longer or has side effects, it MUST run as a background job so it doesn't get interrupted when the user interrupts the HTTP request.
- Any asynchronous operations MUST return 202 with a job ID so the user can query its status.
- Background job status MUST be protected with ACLs, only the user that created the job can query it.


## Transactional Source Control Management
- Individual Git operations are atomic.
- Changing multiple Git repositories at once or syncing their state with a database can be interrupted.
- Interrupted processes MUST NOT lead to an inconsistent state.
- The Service MUST implement resilience mechanisms to handle interruptions.
- These resilience mechanisms MUST cover the following operations:
  - Updating a pull request by pushing new content to the source branch.
  - Merging one or more pull requests in a single, atomic transaction.


## Audit Trail
- All database records MUST have an audit trail that captures their changes or past states.
- The audit trail functionality SHOULD be implemented transparently, models should behave normally, but should have access to history if needed.


## Observability
- TODO: revisit this point, check if it is reasonable to implement this. It requires audit trail with mapping the changes to common event/changeset entries.
- Any request that modifies the database SHOULD map the changes to an event/changeset entry that also contains HTTP request ID.
- This mapping can be used to track what a problematic request did in the Service.
- The stored HTTP request ID MUST be deleted when the legitimate interest no longer applies (and to free up some space).
