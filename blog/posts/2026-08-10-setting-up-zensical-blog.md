---
title: "Setting up our Development Blog with Zensical"
date: 2026-08-10
authors:
  - dmach
tags: [ci-cd, zensical, github-actions, uv, rust]
---

To document technical deep-dives, development stories, and engineering best practices,
we have migrated our development blog to Zensical, a modern, Rust-powered static site generator.

<!-- more -->

### The Tooling

We chose [Zensical](https://zensical.org/) as our static site generator. Designed by the creators of Material for MkDocs as its official successor, Zensical consolidates the SSG engine, the theme, and the plugin ecosystem into a single, high-performance toolchain.
With introducing MkDocs 2.0 as a complete rewrite, dropping the existing plugins and user requirements, Zensical seems to be a more sustainable choice.

To keep our environment lightweight and fast, we leverage `uv` to manage and run Zensical.

### Configuration

We created a simple `zensical.toml` at the root of the repository:

```toml
[project]
site_name = "OBS Flow Blog"
docs_dir = "blog"

[project.theme]
variant = "classic"
features = [
    "navigation.indexes"
]

[project.plugins.search]

[project.plugins.blog]
blog_dir = "."
post_dir = "posts"
```

The blog posts are stored in `blog/posts/` and authors are configured in `blog/.authors.yml`.

### Local Preview with Makefile

To simplify local development and writing, we updated our standard `Makefile` at the repository root. Developers can run:

```bash
make blog
```

This target automatically starts the Zensical development server using `uvx zensical serve -a 0.0.0.0:8080 -o`.

The `-o` (or `--open`) flag is a built-in Zensical feature that automatically opens the local preview in the default web browser, eliminating the need for custom background scripts or `xdg-open` workarounds.

### Automated Deployment

We configured a GitHub Actions workflow in `.github/workflows/publish-blog.yml` to build and deploy the blog automatically on every push to the `main` or `code` branches.

Instead of pushing to a `gh-pages` branch via legacy tools, we use the modern, official GitHub Pages deployment actions (`actions/upload-pages-artifact` and `actions/deploy-pages`).

```yaml
name: Publish Blog

on:
  push:
    branches:
      - main
      - code
    paths:
      - 'blog/**'
      - 'zensical.toml'
      - '.github/workflows/publish-blog.yml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Configure GitHub Pages
        uses: actions/configure-pages@v6

      - name: Checkout repository
        uses: actions/checkout@v7

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: 3.x

      - name: Install Zensical
        run: pip install zensical

      - name: Build documentation site
        run: zensical build --clean

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v5
        with:
          path: site

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```

This ensures automated, secure, and lightning-fast log updates with zero manual overhead.
