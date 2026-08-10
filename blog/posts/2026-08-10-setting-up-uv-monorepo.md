---
title: "Setting up our Python monorepo with uv"
date: 2026-08-10
authors:
  - dmach
tags: [python, uv, monorepo, layout]
---

## The Layout

Because `obs-flow` consists of multiple components that need to be updated and tested together, we decided to use a **monorepo** approach.
We chose [uv](https://github.com/astral-sh/uv) by Astral for its native workspace support.
We structured our project using a `packages/` directory for our components, utilizing the standard `src/` layout internally for each package to prevent accidental import shadowing.

<!-- more -->

* `common`: Shared utilities and domain models.
* `client`: Python client library providing programmatic access to the API.
* `cli`: Command-line interface to manage packaging workflows, reviews, and staging.
* `server`: Backend orchestration service managing packaging workflows, reviews, and staging.

## Initialization Steps

We used `uv init` to bootstrap the repository:

```bash
# 1. Initialize the workspace root
uv init --bare --name obs-flow

# 2. Create the internal components
uv init --lib packages/common --name obs-flow-common
uv init --lib packages/client --name obs-flow-client
uv init --app packages/cli --name obs-flow-cli
uv init --app packages/server --name obs-flow-server
```

## Python Version Management

We keep the `.python-version` files in our packages to ensure consistent `venv` installation across the development team.

* To raise the minimum Python requirement, use: `uv python pin <python-version>`
* To manually change the Python version for specific tasks (e.g., in tests), use: `uv run --python <python-version> <command>`
