# Strategic Plan: Migrating OBS SCM to a Git-Native Architecture

## 1. Executive Summary
Migrating the Open Build Service (OBS) SCM to Git is our strategic imperative.
However, attempting to fulfill this by wrapping a general-purpose forge like Gitea
with a layer of external helper bots introduces severe long-term risks.
To ensure system stability, reduce support escalations, and guarantee data integrity,
we must build a strictly transactional, Git-native SCM tailored for distribution engineering.

Rather than modifying the legacy OBS codebase, we propose building a new, dedicated component: **The Workflow Service**.

**What is the Workflow Service?**
It is a new, standalone service designed to act as the strict **single source of truth** for all distribution source code.
Its core responsibilities are:
1.  **Source Management:** Natively handling Git repositories and ensuring a precise 1:1 mapping with distribution packages.
2.  **Workflow Control:** Natively managing complex distribution states such as pull requests, code reviews, and staging.

## 2. Why Extending the Current OBS is Not an Option
Before considering new tools, we must address why we cannot simply "bolt Git onto" the existing OBS codebase.
The current OBS architecture is severely hindered by its legacy design:

*   **The Historical "Split-Brain":** OBS is currently divided into a "Backend" (source server) and a "Frontend" (a Ruby on Rails application providing the Web UI and API).
*   **Tangled Responsibilities:** The Rails application sometimes acts as a simple proxy for backend calls, but other times it contains independent logic and relies on its own separate database.
*   **Fragile Foundation:** This tangled dependency means any significant modification—like introducing native Git versioning deeply into the core—risks breaking the entire system.
*   **The Goal:** We need to move away from this intertwined legacy. By introducing the **Workflow Service**, we establish strict, clean boundaries where responsibilities are clearly defined, rather than adding more complexity to the existing Rails monolith.

## 3. Why Gitea is a High-Risk Choice
Gitea is built for standard application development, not complex Linux distributions.
Trying to force our workflows into it will create significant operational and support overhead:

*   **The Wrong Scope:** Standard forges assume "1 Repository = 1 Application". OBS manages 20,000+ interdependent packages that require staging and integration testing. Gitea cannot natively model this complexity.
*   **The "Poor Man's API" Problem:** To bridge the gap between Gitea and OBS without a central workflow service, we built and maintain an ecosystem of bots. These bots trigger based on Gitea events (or even by parsing user comments) to perform actions in Gitea and OBS.
*   **The Synchronization Nightmare:** Bots operate asynchronously, acting as a "poor man's API" lacking reliable error codes. This causes severe synchronization issues not only between Gitea and the legacy OBS core but also *within* Gitea itself, as bots often write state back into Gitea. Webhooks drop, duplicate, or timeout. This asynchronous complexity goes far beyond simply writing state to a database. When a bot fails or desynchronizes, UIs show one state while the actual system holds another. This guarantees confusion, broken workflows, and a massive influx of support tickets.
*   **Lack of Atomic Changes:** Making changes to multiple dependent packages requires a coordinated, atomic action. Gitea doesn't natively support that.

## 4. The Solution: Purpose-Built Git SCM
Instead of forcing a generic tool to do things it wasn't designed for, or hacking the legacy OBS codebase,
we propose a clean architectural cut. We decouple the storage from the workflow logic with strict boundaries:

*   **Storage (Git):** Use standard Git directly on our infrastructure to store code and metadata. This replaces the legacy source server for versioning.
*   **Git as the Source of Truth for Metadata:** Git will serve as the strict source of truth for code and package metadata in many cases. Upon any push or merge, this metadata will be strictly validated and subsequently extracted and stored in a database. This allows us to provide fast, complex queries, dashboards, and reporting to users without compromising the integrity of the Git repository.
*   **Workflow Control (The Workflow Service):** A new, clean API layer acts as the sole "brain" and single source of truth for the workflow incl. reviews and staging.
*   **Unambiguous 1:1 Mapping:** Every OBS package maps exactly to one Git repository, eliminating shared-branch side effects.
*   **Immutable Revisions:** Every change is tied to a specific, immutable Git commit. If a developer alters code during a review, it creates a new revision. This resolves a critical issue where external systems must independently calculate whether they are operating on the exact same Pull Request state or not. Having each external tool implement its own logic to track state changes is unreliable, fragile, and creates inconsistencies across the ecosystem.

## 5. The Trap to Avoid: A "Temporary Gitea Bridge"
We must avoid building a temporary adapter or deploying a fleet of bots to bridge Gitea and OBS while we figure out a final solution.
*   It requires writing throwaway code that we will eventually discard.
*   It forces operations to maintain a convoluted ecosystem (Gitea + Bots, legacy OBS, and our new Workflow Service on top). While Gitea and bots exist already, engaging in iterative development to slowly bend everything toward the new service will cause significant operational pain.
*   It frustrates developers by changing their workflows multiple times.
*   **Constant Migrations:** Operating in intermediate phases necessitates continuous data migrations. Each transition requires a meticulous plan for migrating old data and state. All temporary workarounds would need to be extensively documented, further draining resources.

## 6. Business Value & Return of Investment
*   **Drastically Lower Maintenance:** We eliminate the need to maintain, monitor, and troubleshoot complex asynchronous eco-system.
*   **Predictable Stability:** By establishing clean boundaries and keeping workflow control inside a dedicated service, we ensure a single source of truth. We eliminate the false error states and sync issues that drive up support costs.
*   **Familiar Developer Experience:** Developers use standard `git` commands for code changes, and a smart, fast CLI (`osc 2.0`) for complex distribution workflows.

## 7. Safe, Milestone-Based Migration Strategy
We will not execute a risky "big bang" rollout. We prioritize stability and transparent communication:
*   **Milestone 1:** Open RFC (Request for Comments) and transparent prototyping.
*   **Milestone 2:** Opt-In Alpha for integration testing and to gather early feedback.
*   **Milestone 3:** Parallel shadowing of complex workflows (Staging, SLE Maintenance, Devel projects) to prove stability without affecting active releases.
*   **Milestone 4:** Formal approval and production cutover.

## Decision Required
**Requesting approval to launch Milestone 1:**
1. Endorse the decoupled architecture model (Native Git storage + The Workflow Service with clean boundaries).
2. Allocate resources to draft the public RFC and build the initial Proof of Concept.
3. Create a feedback loop with both SUSE stakeholders and openSUSE community.
