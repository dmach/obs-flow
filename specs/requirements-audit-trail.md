# Requirements - Audit Trail
- This document presents technical requirements (the HOW) of audit trail extension for Django models.


## Conformance
- The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL"
  in this document are to be interpreted as described in [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).


## Executive Summary
- Our goal is to maintain a complete, legally defensible, and queryable history of all changes without sacrificing
  relational integrity or developer experience.
- **Accountability:** Track 5Ws: Who did What, When, Where and Why.
- **Auditing:** Provide data for audits, frequently required by certifications.
- **Rapid Incident Resolution (MTTR):** Significantly reduce investigation times by providing enough data to detect origin of each system change or data anomaly.
- **Legal Protection:** Generate immutable, tamper-evident logs, providing legally defensible proof of who performed what action.


## Prerequisites
- Everything MUST work transparently, any Python API user MUST NOT see any difference when using Django models.
- Real foreign keys and many-to-many relations MUST be used to guarantee data integrity.
- It MUST be resilient to race conditions such as data races or late arrivals.
- It MUST work with the django-bolt API.


## Concerns
- Scaling.
- Excessive data growth.
- NIH. There are existing alternatives, none of them has exactly the features described in this document: django-simple-history, django-reversion, django-auditlog, pgAudit.


## The Principle of Non-Destruction (Revocation)
- To maintain a true history, we MUST NOT delete data. If we delete a record, its history is lost.
- Instead of `DELETE` or standard in-place updates, the system **MUST** use **Revocation**.
- Every audited model **MUST** link to an `Event` (representing the "5Ws" of an action) via two fields:
  - `created_event`: When the record or state version came into existence.
  - `revoked_event`: When the record was superseded by an update or logically deleted. If this is `NULL`, the record is "active."


## The Challenge of Mutations and Foreign Keys
- If we simply append a new row every time a record is updated, we break foreign key relationships.
- If Model B points to Model A, and Model A is updated (creating a new row with a new primary key),
- Model B's foreign key now points to an old, revoked version of Model A.
- Using generic foreign keys (e.g., loose UUIDs) is a non-goal because it abandons database-level constraint enforcement.
- We MUST use real, database-enforced foreign keys.


## The Solution: The Anchor-State Split
To solve the foreign key dilemma, each audited model **MUST** be split into two parts under the hood:
- **The Anchor (Immutable Identity with Ephemeral Operational Fields):**
  - This is the permanent identity of the object.
  - It holds the primary key that other models point to.
  - While the Anchor is conceptually immutable (only changing when the entity is created or deleted),
    it **MAY** host mutable, ephemeral fields that have no historical significance for auditing—such
    as temporary locking flags, active user-session locks, or transient process assignments.
    Because these fields act as runtime coordination mechanisms rather than core business data,
    updating them **MUST** modify the Anchor in-place and **MUST NOT** trigger new history entries in the State table.
- **The State (Mutable):**
  - This companion table **MUST** hold all the actual data fields of the object.
  - When data changes, the system **MUST NOT** update the existing state row; instead, it **MUST** revoke it and create a *new* state row linked to the same Anchor.
This solves everything: Foreign keys point to the unchanging Anchor, while the State table safely tracks the history of mutations.


## Maintaining the Illusion (Transparency)
- While the Anchor-State split is powerful, it is complex.
- Developers using the system **SHOULD NOT** have to think about it.
- The API MUST be **Transparent**.
- When a developer interacts with a model in Django (querying, updating, deleting), it **MUST** behave like a normal, single entity.
- Under the hood, revoked entries **MUST** be presented as deleted, and the anchor/state split **MUST** be hidden entirely from the public API.


## Ensuring Concurrency and Integrity
- In a multi-threaded web application, race conditions are inevitable.
- If two requests try to update the same record simultaneously, we risk forking the history (creating two active states).
- Strict concurrency controls **MUST** be enforced:
  - All state mutations MUST be wrapped in atomic transactions.
  - The system **MUST** aggressively lock the Anchor using `SELECT FOR UPDATE` before applying any state changes.
    This ensures modifications are serialized and prevents concurrent forks.
  - A database-level unique constraint **MUST** ensure only one active state (where `revoked_event` is `NULL`) exists per Anchor at any time.
  - Out-of-order writes ("late arrivals") **MUST** be blocked to protect the chronological timeline.
    Any operation using an event timestamp older than the active state's event timestamp **MUST** raise a `ValidationError`.
  - Standard cascading deletes (`models.CASCADE`) bypass Python soft-delete logic by issuing hard SQL deletes.
    To maintain soft-delete integrity across relations, the system **MUST** provide an `AuditForeignKey` (defaulting to `on_delete=audit_cascade`). 
    The `AuditTrailModel.delete()` method **MUST** automatically identify these relationships and perform recursive soft-deletions on active children. 
    If standard Django hard-delete collectors ever attempt to delete an audited model via SQL, a `RuntimeError` **MUST** be raised to safeguard data integrity.


## Managing Relational Complexity
- Hidden, auto-generated junction tables for Many-to-Many relationships cannot be effectively audited.
- To maintain absolute audit trails and data integrity, `AuditManyToManyField` **MUST** strictly require
  an explicit, audited `through` model inheriting from `AuditTrailModel`. 
- If a `through` model is omitted, the system **MUST** raise an `ImproperlyConfigured` exception during class load.


## The Event Lifecycle and Lazy Evaluation
- Passing an `Event` instance explicitly to every `.save()` or `.delete()` is cumbersome, especially during automated cascading operations.
- The system **MUST** support an implicit, thread-safe context manager (e.g., `with audit_event(event):`)
  to pass the active event down the entire save and cascade chain seamlessly.
- **Lazy Event Creation:** To prevent database pollution with empty `Event` rows
  (e.g., during read-only HTTP requests or when form validation fails), Event creation **MUST** be lazy.
- The `audit_event` context manager **MUST** accept a callable factory (e.g., `lambda: Event.objects.create(...)`). 
- The actual `Event` row **MUST ONLY** be created in the database when a `.save()` or `.delete()` mutation actually occurs,
  and cached thereafter. If a request results in no database changes, no `Event` **SHALL** be created.


## Time Travel (History)
- Because we have an unbroken chain of Events and States, we can reconstruct the past.
- The API **MUST** allow developers to query an object's state *as of* a specific Event or Timestamp.
- This **MUST** return entities in the standard Django way, reflecting the exact fields that were current at that moment,
  and respecting lifecycle bounds (entities that weren't yet created or were already deleted **MUST** be excluded).
