---
name: adr
description: Prepare a new Architecture Decision Record (ADR) for review and propose where to store it.
disable-model-invocation: true
---

# ADR

## Template

```md
---
id: ADR-NNNN             # Sequential ID. Never reuse an ID.
date: YYYY-MM-DD         # Date when the decision was made.
status: active           # active | superseded | deprecated
agreed_by: []            # People who agreed with this ADR. Empty if nobody was asked.
supersedes: ADR-NNNN     # Optional. ADR replaced by this decision.
superseded_by: ADR-NNNN  # Optional. ADR that replaces this decision.
---

# ADR-NNNN: [Short title]

## Context
Explain the situation before the decision.
Include important technical constraints, business needs, and previous decisions.
Write this so a new team member can understand it.

## Decision
State the decision clearly.
Use active voice, for example: "We chose X."

## Consequences
Describe both positive and negative consequences.

**Positive:**
- [benefit]

**Negative:**
- [drawback]

## Considered Options
List the main alternatives and why they were not chosen.

- **[Option]** - [what it would provide].
  Rejected because [specific reason].

## Assumptions
List the conditions under which this decision is valid.
Use concrete numbers or conditions where possible.

Also state when the decision should be revisited.
Use a concrete condition, for example:
"Revisit this decision when traffic exceeds 10,000 requests per minute."
```

## Instructions

### 1. Check existing ADRs

Read active ADRs: `grep -l '^status: active' specs/adr/*.md`
Use them to understand existing decisions and avoid conflicts.
If you do not have enough context or cannot identify reasonable alternatives, stop and ask the user.
Never invent missing facts, alternatives, or consequences.

### 2. Check if an ADR is needed

An ADR is useful when the decision:
- is hard to reverse,
- may surprise someone later,
- or involves a real trade-off.

If the decision does not clearly meet these conditions, warn the user but prepare the draft anyway.

### 3. Verify Architectural Foundations (Prerequisites)

Before drafting the ADR, identify the core concepts and mechanisms it relies on.
Cross-reference these concepts against the active ADRs you read in Step 1.
- If a concept is standard industry knowledge (e.g., "REST API", "PostgreSQL"), proceed.
- If a concept is specific to this project (e.g., "Immutable Revisions", "Review DAG"), it **must** be defined in a previous ADR.
- If the proposed ADR relies on a major project-specific concept that has *not* been defined yet, **STOP**. Do not draft the ADR.
  Instead, ask the user: "This proposal relies on [Concept], which is not defined in our existing ADRs. Should we draft an ADR for [Concept] first?"

### 4. Keep it Simple and Focused (Single Core Decision)

Each ADR must cover strictly **one architectural decision**.
Keep ADRs simple and decoupled. If a proposal covers multiple distinct concerns (e.g., scoping logic vs event throttling/scheduling), split them into separate ADRs.
Focus on the core decision, the "why", and high-level trade-offs rather than the "how".
Do not include implementation details, specific class/function names, internal coding patterns, or directory/file paths unless they are the direct subject of the decision itself.
Avoid over-specifying technical details that belong in design docs or code comments.

### 5. UTF-8 and text formatting

Use plain UTF-8 text. Keep structural and typographic punctuation ASCII-only (use standard `-`, `"`, `'`).
Do not use smart quotes, typographic dashes, emojis, non-breaking spaces, or invisible characters.
Keep formatting simple, predictable, and console-friendly without unnecessary line wrapping.

### 6. Output

Return:

1. The complete ADR draft in a fenced Markdown block.
2. Any warnings (e.g., conflict with an existing ADR).
3. The proposed file path: specs/adr/ADR-NNNN-slug.md

The slug must:
- be lowercase,
- use hyphens,
- contain no numbers.

Do not create, modify, or write any file.
The output is only a draft for review and planning.
Wait for user confirmation before any file is created.
