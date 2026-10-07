---
id: ADR-0005
date: 2026-09-30
status: active
agreed_by: []
---

# ADR-0005: CLI Command Lazy Loading with Click

## Context
The CLI (`obs-flow-cli`) manages an expanding hierarchy of commands.
`click` is already a transitive dependency via `django-bolt`.
Standard CLI frameworks eagerly import all command modules at startup, degrading execution responsiveness and shell tab completion.

## Decision
We chose `click` for the CLI and implemented on-demand lazy loading based on file-system naming conventions.
Modules are imported only when their specific command is invoked.
Automated test suites support an eager-loading mode to catch import errors.

## Consequences

**Positive:**
- Introduces zero new external dependencies.
- Minimizes startup and shell completion latency.
- Removes manual command registration boilerplate.
- Test suites verify syntax across all commands via eager mode.

**Negative:**
- Discovery relies on explicit file naming conventions.
- Import errors in dormant commands surface only at invocation or during test runs.

## Considered Options

- **Cyclopts** - Modern type-driven CLI parser.
  Rejected due to lack of track record and adding a new dependency.
- **Typer** - Type-driven CLI framework atop Click.
  Rejected to avoid adding another dependency.
- **argparse** - Standard library module.
  Rejected due to excessive boilerplate for deep subcommands and completions.

## Assumptions
- `django-bolt` continues to include `click`.
- Command modules adhere to the discovery directory conventions.

Revisit this decision if Click provides native zero-overhead lazy loading.
