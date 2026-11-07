---
id: ADR-0018
date: 2026-11-07
status: accepted
agreed_by: []
---

# ADR-0018: Shared Commenting System for Pull Requests and Staging Batches

## Context
In open-source distribution maintenance, collaboration happens across multiple workflow stages: during initial package submission reviews (Pull Requests) and during aggregate staging integration testing (Staging Batches). Both entities require rich discussion, reviewer feedback, question-and-answer threads, and decision rationales. Duplicating comment models, UI templates, RPC APIs, and CLI commands for every workflow object violates DRY principles and creates maintenance overhead.

## Decision

1. **Polymorphic Data Model (`core.models.Comment`):**
   - Implemented a unified `Comment` model in the `core` app using Django's `ContentType` framework and `GenericForeignKey`.
   - Connected `PullRequest` and `StagingBatch` models using `GenericRelation("core.Comment")`.
   - Fields include `author`, `body`, `created_at`, `updated_at`, `parent` (for future threaded replies), and nullable `path` / `line_number` (for future inline diff reviews).

2. **Unified RPC Backend API:**
   - Introduced endpoints `/api/v1/comment/add` and `/api/v1/comment/list`.
   - Both endpoints take a canonical `target_type` (`"pull_request"` or `"staging_batch"`) and a flexible `target_id` (numeric ID or formatted scoped PR identifier like `openSUSE:Factory/python3#1`).

3. **Shared HTMX UI Component:**
   - Created a reusable template partial `core/_comments_section.html`.
   - Includes author badges, timestamps, formatted markdown-compatible body text, deletion actions for authors/admins, and an inline submission form.
   - Embedded directly within the detail views for both Pull Requests (`pr_detail.html`) and Staging Batches (`staging_detail.html`).
   - Powered by standard HTMX endpoints (`/comments/add/` and `/comments/<id>/delete/`) for smooth in-place swaps.

4. **CLI Integration:**
   - Added `flow pr comment add` and `flow pr comment list`.
   - Added `flow staging comment add` and `flow staging comment list`.
   - Both utilize the shared `obs_flow_client.comments` module and `CommentRenderer`.

## Consequences

**Positive:**
- Single source of truth for commenting logic, storage, authorization, and UI presentation across the entire platform.
- Clean database design: adding comment functionality to new entity types (such as issues, builds, or release milestones) requires zero schema modifications.
- Consistent user experience in both web UI and CLI.

**Negative:**
- Generic Foreign Keys require caution with bulk queries; `select_related("author")` and `prefetch_related("comments")` must be applied deliberately.
