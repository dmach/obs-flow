---
id: ADR-0005
date: 2026-09-30
status: active
agreed_by: [dmach]
---

# ADR-0005: CLI Command Lazy Loading with Click

## Context
The CLI manages an expanding hierarchy of commands.
Standard CLI frameworks eagerly import all command modules at startup, degrading execution responsiveness and shell tab completion.

## Decision
We chose `click` for the CLI and implemented on-demand lazy loading based on file-system naming conventions.

## Consequences

**Positive:**
- Minimizes startup and shell completion latency.
- Introduces zero new external dependencies.
- Removes manual command registration boilerplate.

**Negative:**
- Discovery relies on explicit file naming conventions.
- Import errors in dormant commands surface only at invocation or during tests.

## Considered Options

- **Cyclopts / Typer** - Rejected to avoid adding new dependencies.
- **argparse** - Rejected due to excessive boilerplate for deep subcommands.

## Assumptions
- Command modules adhere to the discovery directory conventions.

Revisit this decision if Click provides native zero-overhead lazy loading.
