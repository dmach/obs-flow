# Tech Stack
- This document presents decisions on the technical stack used in the project.


## General Guidance
- Prefer boring, proven programming languages and libraries.
- Plan for maintainability and sustainability for the next 10+ years.
- Keep the dependencies small.
- Keep the code small.


## Operating System
- openSUSE Tumbleweed
- openSUSE Leap (the latest version)
- SLE 16+
- Other distros are a plus.


## Python
- Widely adopted interpreted language.
- Sufficient performance.
- Sets a relatively low bar for new contributors.
- Minimal supported version: 3.11


## Golang
- Only for the performance critical functionality.
- Its use MUST be justified and the justification SHOULD be backed by data.


## Django
- Established framework with 20 years of history.
- Well documented.
- Good security, scaling, etc.
- LTS releases.


## django-bolt
- Potentially risky, but fast performing and fits into Django ecosystem.


## PostgreSQL


## Background Jobs
- Built-in background workers in Django 6+.
- Database-backed by default, keeping infrastructure simple without external brokers.


## Git & API Integration
- Encapsulated Git wrapper object that manages Git CLI operations via Python's standard `subprocess` module.
- Python Standard Library `urllib.request` for Gitea and OBS API communications to avoid external dependency bloat. (TODO: consider requests or urllib3)


## Testing & Ephemeral Environments
- Podman as the native, daemonless container engine on openSUSE.
- `testcontainers-python` to manage isolated, ephemeral service containers during integration tests. (TODO: look into this, do we need it at all?)


## JavaScript / TypeScript
- Avoid Node.js (npm) ecosystem, it's rapidly changing, frequently suffering from security issues and dependency rot.
