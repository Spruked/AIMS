# A.I.M.S. v1 Hardening Contract

## Release status

The current code is frozen as **A.I.M.S. v0.2.0 — Functional Prototype**.
It provides an integrity-focused local foundation. It is not a production
baseline and must not be described as a completed cognitive memory system.

Every future release must state only capabilities demonstrated by its tests,
benchmarks, recovery exercises, and documented operating limits.

## Release sequence

| Release | Scope | Required evidence |
| --- | --- | --- |
| v0.3 | Retrieval and epistemic hardening | Three-SKG domain tests, authority-class tests, outcome-signal tests, explainable ranking tests |
| v0.4 | Security and recovery | Threat model, migration fixtures, backup/restore and corruption-recovery exercises |
| v0.5 | Scale and performance | Published append, replay, retrieval, rebuild, restart, and resource benchmarks |
| v0.6 | Host integration and Display Hub | Provider-neutral host examples and read-only human inspection package |
| v0.7 | Replication and anchoring adapters | Deterministic replication/divergence and independent checkpoint verification |
| v0.8 | Independent review | Reproducible verification package and signed independent review results |
| v0.9 | Release candidate | All stated release gates pass under a documented operating envelope |
| v1.0 | Production baseline | Measured gates, recovery proof, security review, and release criteria complete |

## Derived graph backend decision

**Default/reference backend:** `PythonSKGBackend`, with no external graph
dependency. It is the deterministic baseline and always rebuilds from Vault
events.

**First optional accelerator:** `GraphQLiteSKGBackend` via
`aims-memory-system[graphqlite]`. It was selected because it is embedded,
SQLite-based, available through a Windows wheel, and supports Cypher queries
and graph algorithms without introducing a server. It is a derived-state
mirror, never an authority source.

LadybugDB and LatticeDB remain benchmark candidates. Neither becomes a core
dependency until it passes the same replay, digest, crash-recovery, traversal,
and packaging conformance suite against the Python reference backend.

## v0.3 requirements — retrieval and epistemic hardening

| ID | Requirement | Acceptance gate |
| --- | --- | --- |
| EPI-1 | Replace the single mixed-domain graph with A Priori, A Posteriori, and Collective derived SKGs. A Priori owns only A Priori atom edges; A Posteriori owns only A Posteriori atom edges; Collective owns only cross-domain atom edges. | Domain-routing, rejection, restart/replay, and no-atom-mutation tests pass. |
| EPI-2 | Preserve `memory_core.skg` as the import surface while replacing the conflicting `skg.py` module with a package and compatibility facade. | Existing host imports and approved compatibility tests pass. |
| EPI-3 | Keep long-term-entry provenance in immutable Vault atom provenance, not SKG topology. | A derived A Posteriori atom retains source-entry traceability without creating an invalid graph endpoint. |
| EPI-4 | Persist `skg_domain`, edge identity, transition evidence, prior state, resulting state, and reason before treating a graph transition as committed. | Fault-injection proves failed persistence does not advance in-memory graph state. |
| EPI-5 | Extend relations to supports, contradicts, supersedes, corroborates, same_entity, context_dependent, temporally_precedes, causally_related, and derived_from. | Each relation round-trips through Vault replay. |
| EPI-6 | Add `authority_class` to Vault atoms: assertion, preference, configuration, policy, invariant, legal_constraint, and extensible local classes. | Only explicit protected classes receive non-overridable behavior; ordinary A Priori assumptions may be challenged or retired through evidence. |
| EPI-7 | Introduce a formal `OutcomeSignal` contract containing source, confidence, causal attribution, delay, evidence, and feedback quality. | Absent or weak feedback cannot materially reinforce relevance; update magnitude is bounded and restart-safe. |
| EPI-8 | Separate truth confidence, relevance, retrieval utility, authority, and outcome attribution. | Edge/result explanations identify every contributing signal; no single opaque score is treated as truth. |
| RET-1 | Replace literal-only lookup with pluggable lexical, semantic, entity/provenance, temporal, and graph retrieval adapters. The core remains provider-neutral and supports lexical-only operation. | Each adapter and fused retrieval mode is independently tested; Vault semantics remain unchanged. |
| RET-2 | Make Collective Index a reconciliation layer that fuses the two domain indexes with authority, provenance, temporal, contradiction, utility, and SKG signals. | A returned result includes an explainable ranking breakdown. |
| STM-1 | Upgrade STM selection/eviction with salience, novelty, recurrence, task relevance, active-goal relevance, contradiction pressure, and decay. | Useful context survives irrelevant noise; stale low-value context expires predictably. |

## v0.4 requirements — security, operations, and recovery

| ID | Requirement | Acceptance gate |
| --- | --- | --- |
| SEC-1 | Publish a threat model covering key compromise, rollback, truncation, replay, ledger substitution, index poisoning, malicious feedback, and service attacks. | Each threat has mitigation, detection, residual risk, and a practical test where feasible. |
| SEC-2 | Add scoped service authorization, identity, rotation, revocation, immutable privileged-access events, rate/resource limits, and isolated tenant instances. | Authorization, revocation, audit, abuse, and cross-tenant isolation tests pass. |
| SEC-3 | Add static/dependency/secret scanning, property/fuzz tests, corruption/crash/rollback tests, and migration fixtures. | No unresolved Critical or High findings at release. |
| OPS-1 | Version persisted schemas; provide deterministic migrations and a compatibility policy. | Historical hashes and provenance survive fixture upgrades. |
| OPS-2 | Document installation, backup, recovery, key loss/rotation, corruption, migration, index rebuild, disaster recovery, and incident response. | A new operator completes a deliberate damage-and-recovery exercise using the runbooks alone. |
| OPS-3 | Segment immutable ledgers with manifests, checkpoints, hot/cold tiers, and archival procedures. | Archived segments retain proof, replay, lookup, and provenance. |

## v0.5+ requirements — scale, inspection, and optional adapters

| ID | Requirement | Acceptance gate |
| --- | --- | --- |
| PERF-1 | Benchmark append, replay, retrieval, SKG/index rebuild, receipts, and restart at 10K, 100K, and 1M+ records. | Publish p50/p95/p99, throughput, RAM, disk, and replay time; claims never exceed measurements. |
| HUB-1 | Build a headless Display Hub/Web Components package that reads but never alters authority state. | Vault integrity, keyed Glyph lineage, retrieval receipts, SKG state, and checkpoints are inspectable. |
| ANC-1 | Add optional signed checkpoints and anchoring adapters; keep them outside the core trust requirement. | A copied or tampered local Vault can be independently checked against a checkpoint. |
| REP-1 | Define optional replication above the local core: node identity, immutable event transport, checkpoints, and divergence behavior. | Two nodes deterministically reproduce evidence and detect divergence. |
| GOV-1 | Retain proprietary ownership while enabling independent verification. | NDA review process, reproducible benchmark package, SBOM, signed releases, public test vectors, and signed audit reports exist. |

## Non-negotiable constraints

- The Vault remains authoritative and never undergoes cognitive pruning.
- Derived indexes and SKGs remain rebuildable from immutable evidence.
- Semantic, anchoring, replication, and host integrations are optional adapters.
- The local-first, zero-secret visual mode remains fully functional.
- No release receives a maturity label solely because a feature name exists in code.
