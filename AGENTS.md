# Agent Guidelines


## Basic rules
- `Makefile` contains hints for running tests and working with migrations.
- We don't want to commit several types of files into git because we're still prototyping:
  - migrations (except `__init__.py`)
  - `uv.lock`


## Project layout

- `packages/cli` - command-line interface based on Click
- `packages/client` - HTTP client to the server API, client configuration
- `packages/common` - shared functionality across client, cli, and server
- `packages/server` - Django web service with HTMX + django-bolt API


## Server layering (Django apps)

- **Thin models:**
  - The DB interface.
  - Accessors that unify queries.
  - No business logic.
  - No calls to external systems.
- **Text identity:**
  - Some models implement human readable identifiers that are not the database integer IDs.
  - Functions `<entity>_build_text_id`, `<entity>_parse_text_id` are shared between server and client and belong to `obs_flow_common/<entity>.py`.
  - Models expose a `text_id` property and manager lookup `get_by_text_id(...)`.
- **Business logic:**
  - Lives in `<app>/workflows.py`.
  - Entity building blocks (state transitions, validation, provisioning, DTO mapping).
  - Multi-entity or external-system procedures (sync, merge, membership changes).
  - These sections are identified with header comments (see existing files for examples).
- **Thin API endpoints:**
  - Only wrappers to code from `workflows.py`.
- **Management commands:**
  - Using `workflows.py`, never `api.py`.
