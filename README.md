# A.I.M.S. — Agnostic Immutable Memory System

A drop-in memory substrate for any system with cognitive traits —
no dependency on a specific agent identity, mission architecture, or
external time/cloud authority. `memory_core` is stdlib-only Python;
`service.py` is an optional thin HTTP wrapper if you want it running
as its own process instead of imported directly.

This is a generalization of an earlier Caleon/ISS-specific WORM ledger.
Everything mission-specific (`Caleon_Prime_X1`, ISS stardate sync, DLAS
sync) has been removed. What's left is the part that was always
actually general-purpose, plus three additions requested for this pass:
a **glyph trace**, a **tri-timestamp model**, and a genuine three-tier
memory architecture (long-term / short-term / vault) with the vault
acting as a **self-pruning, self-improving, recursively self-evaluating
source of truth**.

## The three tiers

```
                 ┌─────────────────────────────────────────┐
   observe() ──▶ │  Short-Term Memory (STM)                 │
                 │  fast, cheap, vivacity-decayed cache      │
                 │  the only tier allowed to forget silently │
                 └───────────────┬───────────────────────────┘
                                 │ promotion_candidates()
                                 ▼
                 ┌─────────────────────────────────────────┐
   commit() ───▶ │  Long-Term Memory (LTM)                  │
                 │  WORM ledger: hash chain + glyph trace +  │
                 │  tri-timestamp. Physically fsync'd.       │
                 │  Never forgets, never edits.              │
                 └───────────────┬───────────────────────────┘
                                 │ derive_aposteriori() / assert_apriori()
                                 ▼
                 ┌─────────────────────────────────────────┐
                 │  Vault  (A Priori / A Posteriori atoms)  │
                 │  + SKG  (relations: supports/contradicts/│
                 │          derived_from)                    │
                 │  self_prune() · self_improve() ·          │
                 │  recursive_self_evaluate()                │
                 │  → truth() is the queryable source of     │
                 │    truth for the rest of the host system  │
                 └─────────────────────────────────────────┘
```

- **Short-Term Memory** (`memory_core/short_term.py`) — a
  capacity-bounded cache with vivacity decay (half-life driven, not a
  hard TTL). Items that get touched (re-observed / re-referenced) enough
  times while still vivid become `promotion_candidates()`. STM is the
  only tier that forgets on its own (`sweep()`); nothing here is ever
  claimed as true.

- **Long-Term Memory** (`memory_core/long_term.py`) — the WORM ledger.
  Append-only, `flush()` + `os.fsync()` on every write, SHA-256 hash
  chain, and now a parallel **glyph trace** (see below) threaded through
  every entry. No update or delete method exists anywhere in the class —
  logical immutability by construction, not by convention.

- **Vault + SKG** (`memory_core/vault.py`, `memory_core/skg.py`) — the
  judgment layer. The Vault holds distilled claims ("atoms"), split into:
  - **A Priori** atoms — asserted by design, not derived from any single
    observed entry (axioms, declared constraints). They have a
    confidence floor (`A_PRIORI_FLOOR`) they cannot be pruned below,
    though they can still be reinforced upward.
  - **A Posteriori** atoms — distilled from committed long-term entries
    (or other atoms), starting on probation and graduating to `ACTIVE`
    (i.e. counted in `source_of_truth()`) only once reinforced enough.

  The SKG adds the relational layer over these atoms — `supports`,
  `contradicts`, `derived_from` edges — and is what actually runs
  **recursive self-evaluation**: it walks every active atom, weighs it
  against what its neighbors in the graph currently believe, and
  reinforces or challenges it accordingly, for up to `max_passes`. A
  newly-admitted atom can retroactively change the standing of an atom
  admitted long before it, purely through this graph walk — no new
  external event required. `prune_and_improve()` then removes what
  collapsed and compounds confidence in what has been reinforced
  repeatedly without ever being challenged.

  `CognitiveMemoryLayer.truth()` is the single query surface a host
  system should read from when it needs "what does this system
  currently believe" — active atoms only, each with its
  support/contradiction/derivation edges attached so a caller can audit
  *why* it's trusted, not just that it is.

## Tri-Timestamp model (`memory_core/temporal.py`)

Every entry and every vault atom carries three parallel time
representations instead of one proprietary clock:

| Field      | What it is                              | Why it's there |
|------------|------------------------------------------|-----------------|
| `epoch`    | Unix epoch seconds                        | machine-native, trivially comparable |
| `standard` | ISO-8601 string                           | human-native, timezone-explicit |
| `julian`   | Julian Day Number                         | continuous, calendar-agnostic, astronomy-grade |

`TriTimestamp.verify_internal_consistency()` recomputes each
representation from the others and flags drift beyond tolerance — a
cheap tripwire for clock skew or tampering that a single-format
timestamp can't self-check.

## Glyph Trace (`memory_core/glyph_trace.py`)

A second, independently-derived lineage marker threaded alongside the
SHA-256 hash chain. Each entry's hash maps onto a short sequence of
visually distinct symbols (`derive_glyph`), and each entry's glyph is
then chained into the next (`thread_glyph`) the same way hashes are —
so tampering with one entry breaks visual continuity even if an
attacker manages to patch the hash chain itself. It's meant to be
scanned by eye (or by a lightweight monitor with no crypto library) as
a first-pass anomaly check, not as a replacement for `verify_chain()`.

## What was removed from the original design

- `Caleon_Prime_X1` / `Caleon_MemoryInterface` — mission-specific writer
  identity and wrapper. Replaced by a plain `writer_id: str` you set
  however your host system identifies itself.
- ISS stardate sync (`iss_module`, `iss_stardate()`) — replaced entirely
  by the tri-timestamp model, which needs no external time authority.
- DLAS sync endpoint — removed; this layer makes no assumption about
  what (if anything) it should sync to.

## Usage

```python
from pathlib import Path
from memory_core import CognitiveMemoryLayer, EntryType

memory = CognitiveMemoryLayer(Path("./data"))

# fast, cheap, may be forgotten
item = memory.observe({"saw": "a repeated build failure on module X"})

# permanent, chained, never edited
entry = memory.commit(
    EntryType.OBSERVATION,
    content={"build_failure": "module X", "count": 4},
    writer_id="build-monitor",
)

# distill into a judged claim
atom = memory.derive_aposteriori(
    "module X has a recurring build failure",
    source_entries=[entry],
    initial_confidence=0.5,
)

# what does the system currently believe?
print(memory.truth())

# periodic self-tending: forget stale STM, prune/improve the vault,
# recursively re-evaluate the SKG
print(memory.run_maintenance_cycle())
```

## Running as a service

```bash
pip install -r requirements.txt --break-system-packages
MEMORY_STORE_PATH=./data python service.py
```

Then `POST /stm/observe`, `POST /ltm/commit`, `POST /vault/apriori`,
`POST /vault/aposteriori`, `POST /skg/link`, `GET /skg/truth`,
`POST /maintenance/run`, `GET /status`.

## Design note

`memory_core` has no third-party dependencies. It runs with a bare
Python 3.9+ interpreter — no cloud service, no network call, no
external time source. That's deliberate: a memory layer that a
cognitive system depends on for its own continuity should not itself
depend on something outside the host's control to function.
