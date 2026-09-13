# A.I.M.S. — Agnostic Immutable Memory System

A.I.M.S. is a local-first, model-agnostic memory system. It preserves
authoritative evidence in append-only ledgers, separates A Priori knowledge
from A Posteriori learning, and derives indexes and current relevance without
rewriting historical truth.

> The Vault preserves truth.
>
> The indexes locate truth.
>
> The SKG organizes relevance.
>
> Short-Term Memory carries active cognition.
>
> The Retrieval Ledger remembers every return forever.

## Storage hierarchy

```text
Immutable Vault event ledger     authoritative evidence and provenance
  A Priori / A Posteriori atoms  replayed from append-only Vault events
  evaluation / retirement events evidence for changing interpretation
  relationship evidence          rebuilds the SKG

Derived persistent indexes       A Priori, A Posteriori, Collective
Structured Knowledge Graph       mutable and rebuildable interpretation
Short-Term Memory                temporary, decaying cache
SQLite Retrieval Ledger          permanent retrieval sets and feedback
```

The Vault is never self-pruning. The SKG evaluates relevance and records
resulting evaluation or retirement evidence in the Vault ledger.

## Integrity modes

Every ledger begins with an immutable genesis security policy.

- `visual`: zero-secret SHA-256 hash chain with deterministic visual Glyphs.
- `authenticated`: SHA-256 canonical entry hashes plus an HMAC-SHA-256 Glyph
  chain. `glyph_mode` and `glyph_key_id` are part of the canonical hash.

Authenticated ledgers fail closed without the corresponding runtime keyring.
Secrets are never serialized into ledgers, Vault records, indexes, retrieval
receipts, API responses, or logs. Key rotations create immutable events; old
records continue to validate with their recorded key IDs.

## Local service

```powershell
pip install -r requirements.txt
$env:MEMORY_STORE_PATH = '.\data'
python service.py
```

The default binding is `127.0.0.1:8000`; CORS is disabled by default. Remote
binding requires `AIMS_BIND_HOST` and `AIMS_API_TOKEN` explicitly.

For authenticated mode, provide the active key ID and a local keyring:

```powershell
$env:AIMS_SECURITY_MODE = 'authenticated'
$env:AIMS_GLYPH_KEY_ID = 'local-glyph-2026-01'
$env:AIMS_GLYPH_KEYS_FILE = 'C:\secure\aims-glyph-keys.json'
```

The keyring is a local JSON object mapping key IDs to secrets, for example
`{"local-glyph-2026-01":"runtime-secret"}`. Keep it outside this repository.

## Headless API

The versioned API is presentation-free:

- `GET /api/v1/status`
- `GET /api/v1/memory/summary`
- `GET /api/v1/indexes/status`
- `GET, POST /api/v1/retrievals`
- `GET /api/v1/retrievals/{id}`
- `POST /api/v1/retrievals/{id}/feedback`
- `GET /api/v1/skg/status`
- `GET /api/v1/skg/activity`
- `GET /api/v1/vault/integrity`

The portable display hub is intentionally deferred as a separate presentation
milestone; the core API and evidence contracts are now covered by integration
tests.

## Validation

```powershell
python -m unittest discover -s tests -v
```

## License

This repository is proprietary and confidential. See [LICENSE](LICENSE).
