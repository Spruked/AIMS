# A.I.M.S. — AGNOSTIC IMMUTABLE MEMORY SYSTEM

> A.I.M.S. is a model-agnostic immutable memory system that preserves
> authoritative memory in an append-only Vault, distinguishes A Priori
> knowledge from A Posteriori learning, indexes each independently and
> collectively, maintains a self-pruning Structured Knowledge Graph, records
> every consequential retrieval, and recursively improves future memory
> relevance without rewriting historical truth.

## Signature Architecture & Doctrine

**Architecture Class:** Model-Agnostic Cognitive Memory Substrate
**Primary Authority:** Immutable Vault System
**Knowledge Structure:** Structured Knowledge Graph (SKG)
**Memory Modes:** Short-Term / Long-Term / A Priori / A Posteriori
**Temporal Model:** Epoch + UTC Standard + Julian Date
**Trace Model:** Glyph Trace + Cryptographic Hash Lineage
**Persistent Retrieval Evidence:** SQLite Retrieval Ledger
**Design Principle:** *The system may improve its understanding of the past, but it may never rewrite the past.*

---

# 1. Executive Definition

The A.I.M.S. system is a reusable model-agnostic memory substrate designed to
be embedded into any software system. “Cognitive memory layer” is descriptive
architecture terminology, not the product name.

It is not tied to:

* a particular LLM;
* a particular agent;
* a particular application;
* a particular operating system;
* a particular cloud provider;
* a particular blockchain;
* a specific reasoning methodology;
* Caleon Prime;
* Prometheus Prime;
* ORB;
* ISS;
* DLAS;
* or any other mission-specific architecture.

The layer exists to provide a cognitive system with five fundamental capabilities:

1. **Remember what happened.**
2. **Recall what matters.**
3. **Distinguish what was already known from what was learned.**
4. **Improve the relevance of future recall through experience.**
5. **Preserve a forensic record of how memory contributed to later cognition.**

The architecture is built around one absolute rule:

> **The Immutable Vault is the source of truth. Everything else is derived state.**

The Structured Knowledge Graph, indexes, caches, retrieval scores, summaries, confidence values, and cognitive interpretations may evolve.

The historical Vault does not.

---

# 2. Architectural Doctrine

The architecture deliberately separates **historical truth** from **current cognitive understanding**.

These are not the same thing.

The Vault answers:

> **What was actually recorded?**

The SKG answers:

> **What is the system's current structured understanding of those records?**

The Retrieval Controller answers:

> **Which memories are most relevant to the problem being considered now?**

The Short-Term Memory layer answers:

> **What information is currently active in cognition?**

The Retrieval Ledger answers:

> **What memory was actually returned to the cognitive system at that moment?**

This separation prevents self-improvement from becoming self-revisionism.

A system is therefore permitted to conclude:

> “My earlier understanding was wrong.”

It is never permitted to make the earlier record disappear.

---

# 3. Governing Architecture

```text
                           COGNITIVE HOST
                    LLM / Agent / ORB / Robot /
                 Browser / Voice / Decision Engine
                               │
                               ▼
                     RETRIEVAL CONTROLLER
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       A PRIORI INDEX   A POSTERIORI INDEX   COLLECTIVE INDEX
              │                │                │
              ▼                ▼                │
       A PRIORI VAULT   A POSTERIORI VAULT     │
              │                │                │
              └───────────┬────┘                │
                          │                     │
                          ▼                     ▼
                    IMMUTABLE VAULT            SKG
                    SOURCE OF TRUTH             │
                          │                     │
                          └──────────┬──────────┘
                                     ▼
                              MEMORY RETURN SET
                                     │
                       ┌─────────────┴─────────────┐
                       ▼                           ▼
              SHORT-TERM MEMORY           SQLITE RETRIEVAL
                    CACHE                      LEDGER
               Temporary State             Permanent Evidence
                       │                           │
                       └─────────────┬─────────────┘
                                     ▼
                              COGNITIVE PROCESS
                                     │
                                     ▼
                                   ACTION
                                     │
                                     ▼
                                   OUTCOME
                                     │
                                     ▼
                         A POSTERIORI COMMIT
                                     │
                                     ▼
                          INDEX + SKG REVISION
                                     │
                                     ▼
                      RECURSIVE SELF-EVALUATION
                                     │
                                     ▼
                    STRENGTHEN / WEAKEN / MERGE /
                         RETIRE / PRUNE / LEARN
```

---

# 4. The Immutable Vault System

The **Vault System is the authoritative memory record**.

It is append-only.

Existing committed records are never silently edited, replaced, or deleted.

A later record may:

* contradict an earlier record;
* supersede its interpretation;
* qualify it;
* correct it;
* dispute it;
* reinforce it;
* establish that it was based on incomplete information.

But the earlier record remains part of history.

This means cognitive improvement occurs through **new evidence**, not historical mutation.

## Core Vault Principle

> **The system learns by appending a better understanding of the past — not by rewriting the past.**

The Vault should therefore contain sufficient provenance to reconstruct the evolution of knowledge over time.

---

# 5. A Priori Vault

The **A Priori Vault** contains knowledge that existed before a particular observation, experience, or cognitive event.

Examples include:

* declared facts;
* identity information;
* system configuration;
* established doctrine;
* known constraints;
* policies;
* rules;
* user-provided preferences;
* inherited knowledge;
* operating assumptions;
* system capabilities;
* previously established relationships.

A Priori describes **epistemic origin**, not permanent correctness.

An A Priori belief may later be contradicted by evidence.

Therefore:

```text
A_PRIORI ≠ PERMANENTLY TRUE
```

Instead:

```text
A_PRIORI = KNOWN OR ASSERTED BEFORE THE RELEVANT EXPERIENCE
```

Where necessary, authority should be separately classified.

For example:

```text
epistemic_origin: A_PRIORI

authority_class:
- assertion
- configuration
- preference
- policy
- invariant
- legal_constraint
- system_rule
```

This prevents ordinary assumptions from receiving the same standing as genuine system invariants.

---

# 6. A Posteriori Vault

The **A Posteriori Vault** contains knowledge acquired through experience.

Examples include:

* observations;
* outcomes;
* detected patterns;
* corrections;
* learned preferences;
* successful approaches;
* failed approaches;
* contradiction evidence;
* causal observations;
* interaction results;
* environmental discoveries;
* recursive memory evaluations.

A Posteriori records provide the architecture with the ability to distinguish:

> **What did I believe before acting?**

from:

> **What did I learn because I acted?**

This separation creates a genuine forensic record of learning.

---

# 7. Long-Term Memory

Long-Term Memory is the durable committed record from which persistent cognitive memory is derived.

Its required properties are:

* append-only operation;
* deterministic sequence ordering;
* cryptographic hash chaining;
* explicit writer identity;
* namespace isolation;
* Glyph Trace identity;
* triple temporal coordinates;
* durable filesystem writes;
* startup integrity verification;
* direct Vault references.

Long-Term Memory may contain raw observations that have not yet been promoted into a structured belief.

It therefore records **experience**, while the Vault records authoritative memory objects and epistemic classifications.

---

# 8. Short-Term Memory

Short-Term Memory is the active cognitive working set.

It may contain:

* current conversation context;
* current task state;
* recent observations;
* active retrieved memories;
* temporary hypotheses;
* current entities;
* open contradictions;
* active objectives;
* recent reasoning inputs.

Short-Term Memory is deliberately temporary.

It may use:

* capacity limits;
* recency;
* vivacity;
* frequency of access;
* contextual relevance;
* decay;
* eviction.

Short-Term Memory is the **only memory tier permitted to forget silently**.

However, this creates an important distinction:

> **The cache may expire. The fact that a memory was returned to the cache does not expire.**

Every retrieval entering Short-Term Memory creates permanent retrieval evidence.

---

# 9. Permanent Retrieval Ledger

Every memory retrieval is permanently receipted in a local SQLite database.

This creates an independent record of what information was actually available to cognition.

The Retrieval Ledger records **all returns forever**.

It does not mean all temporary cache state is retained forever.

It means every material memory return is retained as a referenceable retrieval event.

## Core Tables

```text
retrieval_events
retrieval_results
cache_sessions
query_events
evaluation_events
index_references
```

## Retrieval Event

A retrieval event should record:

```text
retrieval_id
session_id
query_hash
retrieval_mode
epoch_timestamp
standard_timestamp
julian_timestamp
glyph_trace_id
result_count
retrieval_set_hash
```

## Retrieval Result

Each returned memory should record:

```text
retrieval_id
returned_rank
source_vault
source_index
source_record_id
source_glyph
record_hash
relevance_score
confidence_score
skg_weight
return_hash
retrieval_reason
```

The Retrieval Ledger therefore makes it possible to determine later:

* what was asked;
* which indexes were searched;
* which records were returned;
* their ranking;
* their relevance weights;
* the SKG state affecting retrieval;
* what entered Short-Term Memory;
* what decision followed;
* what outcome occurred.

This creates **cognitive chain-of-custody**.

---

# 10. Triple Index Architecture

The architecture maintains three independent but cooperating indexes.

## 10.1 A Priori Index

Indexes only the A Priori Vault.

It supports retrieval based on:

* entities;
* concepts;
* relationships;
* subject;
* namespace;
* time;
* confidence;
* authority;
* provenance;
* semantic similarity;
* contextual relevance.

Every index result points back to its authoritative Vault record.

---

## 10.2 A Posteriori Index

Indexes only the A Posteriori Vault.

It supports retrieval of:

* observed outcomes;
* learned behavior;
* corrections;
* evidence;
* discovered relationships;
* prior successes;
* prior failures;
* recursive evaluations;
* experiential knowledge.

The separation prevents learned evidence from being confused with what was believed before the experience occurred.

---

# 10.3 Collective Index

The **Collective Index** spans both Vault domains.

It does not become another source of truth.

Its purpose is to detect and expose cross-vault relationships.

Examples include:

```text
supports
contradicts
supersedes
corroborates
derived_from
same_entity
context_dependent
temporally_precedes
causally_related
```

Example:

```text
A Priori Record:
"Customer prefers telephone contact."

A Posteriori Record:
"Customer ignored nine calls and responded to four emails."

Collective Index:
Prior preference contradicted by observed behavior.
```

Neither historical record is altered.

The Collective Index identifies their relationship.

---

# 11. Structured Knowledge Graph — SKG

The **Structured Knowledge Graph** represents the system's current structured understanding of the Vault.

The SKG is not the source of truth.

It is derived state.

Therefore it may be:

* recalculated;
* reorganized;
* strengthened;
* weakened;
* merged;
* retired;
* pruned;
* rebuilt.

The SKG should be completely reconstructable from authoritative Vault evidence.

If the SKG were destroyed, the system should lose convenience and optimized cognition — not historical truth.

---

# 12. SKG Self-Pruning

The SKG must actively remove cognitive dead weight.

Without pruning, a knowledge graph eventually accumulates:

* obsolete edges;
* duplicate concepts;
* weak associations;
* stale hypotheses;
* disproven relationships;
* low-value embeddings;
* redundant summaries;
* orphan concepts;
* temporary contextual relationships;
* repeatedly unsuccessful retrieval pathways.

The SKG may therefore perform:

```text
strengthen
weaken
merge
retire
prune
```

Suggested lifecycle:

```text
ACTIVE
  ↓
WEAKENED
  ↓
DORMANT
  ↓
RETIRED
  ↓
PRUNED FROM ACTIVE SKG
```

Pruning the SKG does **not** delete Vault evidence.

---

# 13. Evidence-Preserving Pruning

Important SKG modifications should generate an immutable Vault event before derived state changes.

Example:

```text
event_type: skg_pruning_event

target:
edge-8837

action:
retired

reason:
superseded_by_newer_evidence

supporting_records:
glyph-4721
glyph-4884

previous_weight:
0.42

resulting_weight:
0.08
```

This means even the system's process of forgetting derived relationships remains forensically explainable.

---

# 14. Recursive Self-Evaluation

The architecture does more than accumulate memories.

It evaluates how useful prior memories were.

After meaningful cognitive cycles, the evaluator should examine:

* Which memories were retrieved?
* Why were they retrieved?
* Which memories influenced the decision?
* Was the resulting prediction correct?
* Did the action succeed?
* Did reality contradict prior knowledge?
* Was an older belief incomplete?
* Should a relationship become stronger?
* Should a relationship become weaker?
* Should a new SKG connection be created?
* Should an existing connection be retired?

Importantly, the evaluator does not modify historical memory.

It appends a new evaluation.

Example:

```text
Memory M102
Original assertion preserved.

Evaluation E4938:
target: M102
finding: partially contradicted
evidence: M4935, M4936
confidence_delta: -0.31
```

The SKG then adjusts its current interpretation.

---

# 15. Retrieval Utility Learning

Memory relevance should improve with experience.

A memory repeatedly retrieved and associated with successful outcomes should gain cognitive utility.

A memory repeatedly retrieved but producing poor results should lose retrieval influence.

Conceptually:

```text
M42
retrieved: 73
useful: 45
neutral: 4
harmful: 2
→ increase retrieval utility
```

Versus:

```text
M95
retrieved: 38
useful: 1
contradicted: 17
→ reduce SKG influence
```

The historical records remain unchanged.

Only **current cognitive relevance** evolves.

---

# 16. Retrieval Controller

The Retrieval Controller sits between the cognitive host and the memory architecture.

It may search in three modes:

```text
PRIOR_ONLY
POSTERIOR_ONLY
COLLECTIVE
```

## PRIOR_ONLY

Answers questions such as:

> What did the system know before this event?

Uses the A Priori Index.

## POSTERIOR_ONLY

Answers questions such as:

> What did experience teach us?

Uses the A Posteriori Index.

## COLLECTIVE

Answers:

> What is the system's best current understanding?

Uses:

* both Vault indexes;
* Collective Index;
* SKG relevance;
* contradiction state;
* temporal relationships;
* retrieval utility.

---

# 17. Retrieval Ranking

Retrieval should not depend only on semantic similarity.

Potential weighting dimensions include:

```text
semantic similarity
recency
confidence
corroboration
epistemic origin
authority class
retrieval usefulness
causal relevance
temporal relevance
source authority
SKG relationship strength
contradiction pressure
active task
active goal
namespace relevance
```

Conceptually:

```text
retrieval relevance =
    semantic relevance
  × evidence strength
  × confidence
  × retrieval usefulness
  × contextual relevance
  × temporal relevance
  × relationship strength
  - contradiction pressure
  - redundancy penalty
```

Exact weighting remains implementation-specific.

---

# 18. Retrieval Set Hash

Every ordered bundle of memory returned into active cognition receives a deterministic fingerprint.

Conceptually:

```text
retrieval_set_hash =
SHA256(
    query_hash
    + ordered_record_hashes
    + retrieval_mode
    + temporal_coordinates
)
```

A later cognitive event can reference the retrieval set:

```text
reasoning_event
├── retrieval_set_hash
├── input_glyph
├── output_glyph
└── outcome_reference
```

This establishes exactly which memory context was provided to cognition.

---

# 19. Glyph Trace

Every permanent memory event carries a **Glyph Trace**.

The Glyph Trace is a human-recognizable lineage representation associated with cryptographic provenance.

It may contain:

```text
glyph_id
memory_id
namespace
source_identity
writer_identity
session_id
parent_trace
correlation_trace
memory_class
epistemic_origin
temporal_coordinates
content_hash
previous_hash
evidence_references
confidence
provenance
glyph_hash
```

The Glyph is not a replacement for cryptographic integrity.

It provides:

* rapid human inspection;
* recognizable continuity;
* compact lineage identification;
* cross-system correlation;
* forensic rendering;
* certificate representation;
* visual anomaly indication.

If stronger cryptographic independence is required, a separately protected signing or anchoring mechanism must be used.

---

# 20. Triple Timestamp Model

Every permanent record should carry three representations of its event time.

```text
epoch
standard
julian
```

## Epoch

Machine-native Unix time.

Recommended:

```text
epoch_ms
```

or higher precision where warranted.

## Standard

Human-readable UTC ISO-8601.

Example:

```text
2026-09-13T04:41:27.481Z
```

## Julian

Astronomical Julian Date.

Example structure:

```json
{
  "epoch_ms": 1789274487481,
  "standard": "2026-09-13T04:41:27.481Z",
  "julian": 2461296.695457
}
```

The representations should be internally cross-verified.

This verifies **representation consistency**.

It does not, by itself, prove that the originating system clock was externally authoritative.

---

# 21. Memory Lifecycle

The canonical cognitive lifecycle is:

```text
OBSERVE
   ↓
SHORT-TERM CACHE
   ↓
INDEXED RETRIEVAL
   ↓
RETRIEVAL RECEIPT
   ↓
COGNITION
   ↓
DECISION / ACTION
   ↓
OUTCOME
   ↓
LONG-TERM COMMIT
   ↓
A POSTERIORI VAULT
   ↓
RE-INDEX
   ↓
COLLECTIVE RECONCILIATION
   ↓
SKG UPDATE
   ↓
RECURSIVE SELF-EVALUATION
   ↓
STRENGTHEN / WEAKEN / MERGE / RETIRE / PRUNE
   ↓
IMPROVED FUTURE RETRIEVAL
```

This produces learning without permitting history to mutate.

---

# 22. Forensic Cognitive Reconstruction

The architecture should permit reconstruction of a cognitive event after the fact.

Given a decision or output, the system should be able to determine:

```text
What triggered cognition?
↓
What query was generated?
↓
Which indexes were searched?
↓
Which memories were considered?
↓
Which memories were returned?
↓
What rank did they receive?
↓
What SKG relationships affected the ranking?
↓
What entered Short-Term Memory?
↓
What retrieval-set hash represented that context?
↓
What action was taken?
↓
What outcome followed?
↓
What was subsequently learned?
```

This is not merely memory.

It is **forensic cognitive provenance**.

---

# 23. System Independence

The memory architecture makes no assumptions about the cognitive host.

Potential consumers include:

* large language models;
* local language models;
* multimodal models;
* autonomous software agents;
* ORB systems;
* browser agents;
* robots;
* industrial systems;
* voice assistants;
* decision-support systems;
* desktop assistants;
* edge devices;
* human-supervised cognitive systems.

The interface remains conceptually:

```text
REMEMBER
RECALL
RELATE
VERIFY
EVALUATE
CHECKPOINT
```

---

# 24. Storage Roles

The architecture intentionally separates storage responsibilities.

## Short-Term Cache

```text
Purpose:
Working cognition

Behavior:
Mutable
Temporary
Fast
Decay permitted
```

## SQLite Retrieval Ledger

```text
Purpose:
Permanent history of memory returns

Behavior:
Persistent
Indexed
Referenceable
Append-oriented
All retrieval returns retained
```

## Immutable Vault

```text
Purpose:
Historical authority and source of truth

Behavior:
Append-only
Cryptographically traceable
Never silently rewritten
Never cognitively pruned
```

## SKG

```text
Purpose:
Current structured understanding

Behavior:
Mutable
Weighted
Self-pruning
Self-improving
Rebuildable
Derived from Vault evidence
```

---

# 25. Integrity Model

The baseline implementation should provide:

* deterministic canonical serialization;
* SHA-256 content hashing;
* previous-record hash chaining;
* sequence validation;
* Glyph Trace linkage;
* triple timestamps;
* startup chain verification;
* durable write acknowledgement;
* retrieval-set hashing;
* retrieval ledger persistence.

A critical terminology rule applies:

> `flush()` and `fsync()` improve write durability. They do not transform an ordinary filesystem into physically immutable WORM storage.

Therefore the correct baseline claim is:

> **Logically append-only, durable, cryptographically tamper-evident memory.**

True physical immutability requires an additional storage control such as:

* hardware WORM;
* immutable object storage;
* protected snapshots;
* signed external checkpoints;
* independent cryptographic anchoring.

---

# 26. Failure Doctrine

The architecture should degrade safely.

If Short-Term Memory is lost:

> Current working context may be lost, but permanent historical memory remains.

If an index is lost:

> Rebuild it from its corresponding Vault.

If the Collective Index is lost:

> Rebuild it from A Priori and A Posteriori indexes and Vault references.

If the SKG is lost:

> Reconstruct the graph from the Vault, indexes, evaluation records, and graph-change events.

If SQLite Retrieval Ledger is damaged:

> Cognitive retrieval provenance is affected, but authoritative Vault content remains intact.

If the Vault is corrupted:

> This is a primary integrity incident and should stop authoritative memory operations until verification/recovery completes.

Thus:

> **Everything above the Vault should be recoverable from the Vault wherever practical.**

---

# 27. Relationship Between Memory Layer and Vault System

The two systems should remain architecturally distinct.

## Vault System

Responsible for:

* authoritative storage;
* immutable evidence;
* provenance;
* hash lineage;
* Glyph identity;
* authoritative records;
* evaluation history;
* append-only persistence.

## Cognitive Memory Layer

Responsible for:

* memory organization;
* indexing;
* retrieval;
* active working memory;
* relevance;
* SKG construction;
* recursive evaluation;
* contradiction handling;
* retrieval weighting;
* cognitive adaptation.

Their relationship is:

```text
VAULT SYSTEM
"What happened?"

      ↕ direct connection

COGNITIVE MEMORY LAYER
"What matters now?"
"What have I learned?"
"What should I remember next time?"
```

Neither replaces the other.

Together they form a persistent cognitive substrate.

---

# 28. Non-Negotiable Architectural Rules

### Rule 1 — Vault Authority

The Immutable Vault is the source of historical truth.

### Rule 2 — No Historical Mutation

Learning must never require silent modification of an existing committed record.

### Rule 3 — SKG Is Derived

The SKG may evolve because it is not authoritative evidence.

### Rule 4 — SKG Must Prune

Dead cognitive weight must not accumulate indefinitely.

### Rule 5 — Vault Never Cognitively Prunes

Historical evidence remains preserved even when no longer cognitively relevant.

### Rule 6 — A Priori and A Posteriori Remain Distinguishable

The system must be able to reconstruct what was known before an experience and what was learned afterward.

### Rule 7 — Separate Indexes

A Priori and A Posteriori Vaults maintain independent indexes.

### Rule 8 — Collective Reconciliation

A third Collective Index spans both domains without becoming a source of truth.

### Rule 9 — Cache Is Temporary

Working memory may decay and expire.

### Rule 10 — Retrieval Evidence Is Permanent

Every material memory return is permanently receipted.

### Rule 11 — Cognitive Context Is Fingerprinted

Returned memory sets receive a deterministic retrieval-set hash.

### Rule 12 — Self-Evaluation Creates Evidence

Recursive evaluation creates new records rather than rewriting old ones.

### Rule 13 — Temporal Records Use Three Coordinates

Epoch, UTC Standard, and Julian representations accompany permanent cognitive evidence.

### Rule 14 — Every Persistent Record Is Traceable

Cryptographic lineage and Glyph Trace identify its provenance.

### Rule 15 — Cognitive Hosts Are Replaceable

No specific LLM, agent, model, product, or service owns the memory architecture.

---

# 29. Signature Doctrine

The architecture can be summarized in five statements:

> **The Vault preserves truth.**

> **The indexes locate truth.**

> **The SKG organizes relevance and removes cognitive dead weight.**

> **Short-Term Memory carries active cognition.**

> **The Retrieval Ledger remembers every return forever.**

And the governing principle over all five is:

> **Memory may improve its interpretation of history indefinitely, but history itself remains intact.**

---

# 30. Signature Architecture Statement

The A.I.M.S. architecture is designed as a permanent memory substrate rather
than an application feature; “cognitive memory layer” remains descriptive
terminology only.

Any cognitive system built above it may change.

Models may be replaced.

Agents may evolve.

Interfaces may disappear.

Knowledge graphs may reorganize themselves.

Indexes may be regenerated.

Caches may expire.

Reasoning systems may improve.

But the provenance of memory remains.

The result is a cognitive architecture in which **continuity does not depend on the continued existence of the intelligence currently using it**.

That is the defining purpose of the system:

> **A persistent, model-independent memory foundation capable of preserving experience, distinguishing knowledge from learning, documenting every consequential return, and continuously improving cognitive relevance without sacrificing historical truth.**
