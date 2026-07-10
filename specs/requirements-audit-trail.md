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
- The `revoked_event` MUST be equal to or newer than `created_event`.


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


## Comparative Analysis of Existing Alternatives
To justify the engineering choice of designing a custom, reusable temporal audit library (Anchor-State Split model), this section contrasts our requirements against standard ecosystem options.

### Summary Matrix

| Evaluation Dimension | Our Temporal Audit Library | django-simple-history | django-reversion | django-auditlog | pgAudit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Relational Integrity** | **Absolute (DB-enforced)**. Standard foreign keys point to the immutable Anchor. M2M uses audited custom through-models. | **Broken**. Foreign key constraints are dropped from historical tables to prevent cascade deletion side-effects. | **None**. Stores serialized records as JSON/XML text blobs. No database-level integrity or constraints. | **None**. Uses generic relations/GVKs and text/JSON delta logs. No database-level constraints. | **Systemic**. Purely records execution logs; does not build or maintain relational history in DB schemas. |
| **Entity Identity (Anchor)** | **Yes**. Anchor maintains permanent primary keys, allowing normal Django models to point directly to it. | **No**. Twin historical table is populated. Referencing history directly from other models breaks cascades. | **No**. Changes are packed as independent serialized revision records in a generic version table. | **No**. Centrally tracked delta changes in a single unstructured table. | **No**. Mutations occur in-place; audit logs are streamed to Postgres server logs. |
| **Pessimistic Concurrency** | **Guaranteed**. Uses `SELECT FOR UPDATE` on Anchor, database-level unique filters, and rejects late arrivals. | **None**. Relies on basic `post_save` signals. Susceptible to concurrent race conditions and history forks. | **None**. Relies on thread-local/signal wrappers. Under high concurrency, intermediate states can easily fork. | **None**. Basic signals without row-locking logic. Subject to database write races. | **Database Engine**. Enforces standard SQL isolation levels but has no application-level awareness of concurrency. |
| **Query Transparency** | **Seamless**. History is queried via normal Django API (e.g., `.as_of(event)`) yielding typed model instances. | **Partial**. Requires querying a twin `.history` manager yielding distinct `Historical[Model]` instances. | **Poor**. Requires pulling and deserializing string/JSON payloads inside Python. Inefficient for database joins. | **None**. Designed for reading diff lists, not for reconstructing full database model graphs or querying past states. | **None**. Reconstructing a state requires parsing raw external server logs and replaying SQL statements. |
| **Context & Lazy Event** | **Implicit & Lazy**. Context propagates automatically; database Event row is created ONLY if a mutation occurs. | **Partial**. Propagates request user via thread-locals, but does not support lazy DB row generation. | **Eager**. Revision rows are registered on block execution, polluting database with empty revisions if no save happens. | **Eager**. Directly logs events sequentially upon signal triggers. | **None**. Completely divorced from Django application threads, users, and lazy evaluation contexts. |

---

### In-Depth Architectural Evaluation

#### 1. django-simple-history
* **Mechanism:** Intercepts Django save/delete signals and clones the model's attributes into a mirror "Historical" table (e.g., `HistoricalBook`).
* **Why it fails our requirements:**
  * **Destruction of Database-Level Integrity:** To prevent historical records from being deleted when referenced items are dropped, `django-simple-history` intentionally strips database-level foreign key constraints (converting them to simple integer or UUID columns). This violates our requirement that *real foreign keys must be used to guarantee data integrity*.
  * **Lack of Identity Anchor:** It does not utilize an Anchor-State split. Consequently, if Model B has a foreign key to Model A, and Model A is updated, Model B still points to the mutated, in-place version of Model A. Under simple-history, there is no immutable Identity Anchor that acts as a stable reference while its state is historically cataloged.
  * **Concurrency & Late Arrivals:** It lacks native row-locking mechanisms (`SELECT FOR UPDATE`) during state generation, allowing race conditions to record duplicate active states, out-of-order writes, or timeline forks under heavy concurrent server requests.

#### 2. django-reversion
* **Mechanism:** Serializes model states into text/JSON blocks stored in global, central revision tables (`Revision` and `Version` models) linked via Django Generic Foreign Keys (GFK).
* **Why it fails our requirements:**
  * **No Database Constraints:** Serializing fields into text/JSON columns completely bypasses SQL indexes, database-level data types, referential integrity checks, and foreign key cascades. A delete in an external table can leave dangling, invalid, or corrupt references inside the serialized string payload with no way for the RDBMS to prevent or heal it.
  * **Query Inefficiency:** Because data is serialized as text, performing standard Django queries, filters, or database-level SQL joins on past history is mathematically complex and performance-prohibitive. Reconstructing a complex graph of related models at a specific point in time requires loading and parsing massive amounts of JSON/XML data sequentially in Python memory.
  * **No Transparency:** It does not allow developers to interact with historical states as if they were standard, native Django model entities directly within the database.

#### 3. django-auditlog
* **Mechanism:** A lightweight logging tool that tracks changes to models in a centralized `LogEntry` table, storing serialized delta changes (diffs) and user metadata.
* **Why it fails our requirements:**
  * **Not Designed for State Reconstruction:** `django-auditlog` is built for ledger-style visual change auditing (displaying a list of changes to administrators), not for system-level temporal querying or Time Travel. Reconstructing an object's full state (let alone an entire relational graph of objects) "as of" a timestamp from flat diff logs is extremely inefficient and not supported by the API.
  * **Referential Fragility:** Relies on Django's Generic Foreign Keys, bypassing database-level integrity checks, indexes, and cascades.
  * **Concurrency & Integrity:** No transactional safety locks or late-arrival protection.

#### 4. pgAudit
* **Mechanism:** A PostgreSQL extension that streams detailed session and object execution audits to the PostgreSQL server log.
* **Why it fails our requirements:**
  * **Divorced from Application Context:** Operates entirely inside the PostgreSQL engine. It lacks direct, native access to application-level context (e.g., Django thread-safe variables, active request users, logical transaction intents, or lazy validation state) unless complex comment-injection mechanisms are built.
  * **No Django ORM Transparency:** Django application code and developers have no native or transparent access to historical records. Performing "Time Travel" queries directly within Django views or business logic is impossible.
  * **Database Lock-In:** It is strictly bound to PostgreSQL. Our architecture mandates compatibility across standard Django-supported backends to facilitate clean, isolated unit testing (e.g., using fast, in-memory SQLite instances in hermetic test runs).
