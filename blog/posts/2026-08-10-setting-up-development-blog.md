---
title: "Setting up our Development Blog and GitHub Pages Deployment"
date: 2026-08-10
authors:
  - dmach
tags: [ci-cd, mkdocs, github-actions, uv]
---

To document technical deep-dives, development stories, and engineering best practices,
we have set up a development blog using MkDocs Material and automated its deployment to GitHub Pages.

<!-- more -->

### The Tooling

We chose [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) for its clean layout, built-in blog plugin, and excellent support for technical documentation. 

To keep our environment lightweight and fast, we leverage `uv` to manage and run MkDocs.

### Configuration

We created a simple `mkdocs.yml` at the root of the repository:

```yaml
site_name: "OBS Flow Blog"
theme:
  name: material
  features:
    - navigation.indexes

docs_dir: blog

plugins:
  - search
  - blog:
      blog_dir: .
      post_dir: posts
```

The blog posts are stored in `blog/posts/` and authors are configured in `blog/.authors.yml`.

### Tool Installation with uv

When installing MkDocs and its Material theme via `uv`, we use the following command:

```bash
uv tool install mkdocs --with mkdocs-material
```

#### Why not `uv tool install mkdocs-material`?

`uv tool install` is designed to install executable tools into isolated environments and expose their binaries to the user's PATH. 

1. **No Executable:** The `mkdocs-material` package is a theme and plugin library. It does not expose any command-line entry points (executables) of its own. If you attempt to run `uv tool install mkdocs-material`, `uv` will fail because there is no executable to install.
2. **Isolated Environments:** To use `mkdocs-material`, it must be present in the same Python environment as the `mkdocs` executable.
3. **The `--with` Solution:** By running `uv tool install mkdocs --with mkdocs-material`, we install the `mkdocs` tool and inject the `mkdocs-material` dependency directly into its isolated virtual environment. This allows the `mkdocs` executable to find and load the Material theme.

### Local Preview with Makefile

To simplify local development and writing, we added a standard `Makefile` to the repository root. Instead of remembering the full `uvx` command, developers can simply run:

```bash
make blog
```

This target automatically:
1. Starts the MkDocs development server using `uvx --with mkdocs-material mkdocs serve`.
2. Waits for 1 second and automatically opens the local preview (`http://127.0.0.1:8080`) in the default web browser using `xdg-open`.

Running `make` without arguments also provides a self-documenting help menu listing all available targets.

### Automated Deployment

We configured a GitHub Actions workflow in `.github/workflows/publish-blog.yml` to build and deploy the blog automatically on every push to the `main` or `code` branches.

The workflow uses `astral-sh/setup-uv` to install `uv`, installs `mkdocs` with the `mkdocs-material` plugin, and deploys using `mkdocs gh-deploy`:

```yaml
name: Publish Blog

on:
  push:
    branches:
      - main
    paths:
      - 'blog/**'
      - 'mkdocs.yml'
      - '.github/workflows/publish-blog.yml'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install MkDocs Material
        run: uv tool install mkdocs --with mkdocs-material

      - name: Deploy to GitHub Pages
        run: uvx mkdocs gh-deploy --force
```

This ensures automated log updates with zero manual overhead.
