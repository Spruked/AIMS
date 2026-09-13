#!/usr/bin/env python3
"""
service.py
Host-agnostic HTTP service around CognitiveMemoryLayer.

No mission-specific sync target, no external agent identity, no
proprietary time authority. Configure only where the store lives and
what to call it.
"""

import hmac
import json
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from memory_core import AIMSMemorySystem, EntryType, IntegrityError, Relation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory-layer-service")

app = FastAPI(
    title="A.I.M.S. — Agnostic Immutable Memory System",
    description="Immutable Vault System + short-term memory + a priori/a posteriori indexes + SKG",
    version="0.2.0",
)
_cors_origins = [origin.strip() for origin in os.getenv("AIMS_CORS_ORIGINS", "").split(",") if origin.strip()]
if _cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-AIMS-Token"])

layer: Optional[AIMSMemorySystem] = None
api_token = os.getenv("AIMS_API_TOKEN")


def _load_keyring() -> Dict[str, str]:
    """Load runtime-only key material from a local JSON secret source."""
    keyring: Dict[str, str] = {}
    key_file = os.getenv("AIMS_GLYPH_KEYS_FILE")
    if key_file:
        try:
            raw = json.loads(Path(key_file).read_text(encoding="utf-8"))
            source = raw.get("keys", raw) if isinstance(raw, dict) else None
            if not isinstance(source, dict) or not all(isinstance(key_id, str) and isinstance(key, str) for key_id, key in source.items()):
                raise ValueError("keyring must be a JSON object mapping key IDs to secrets")
            keyring.update(source)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise RuntimeError("Unable to load AIMS_GLYPH_KEYS_FILE") from error
    active_key = os.getenv("AIMS_GLYPH_KEY")
    active_key_id = os.getenv("AIMS_GLYPH_KEY_ID")
    if active_key:
        if not active_key_id:
            raise RuntimeError("AIMS_GLYPH_KEY_ID is required when AIMS_GLYPH_KEY is set")
        keyring[active_key_id] = active_key
    return keyring


@app.middleware("http")
async def require_remote_token(request: Request, call_next):
    if api_token and not hmac.compare_digest(request.headers.get("X-AIMS-Token", ""), api_token):
        return JSONResponse(status_code=401, content={"detail": "Valid X-AIMS-Token required"})
    return await call_next(request)


class ObserveRequest(BaseModel):
    content: Dict[str, Any]
    tags: Optional[List[str]] = None


class CommitRequest(BaseModel):
    entry_type: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    writer_id: Optional[str] = "system"


class AprioriRequest(BaseModel):
    statement: str
    metadata: Optional[Dict[str, Any]] = None


class AposterioriRequest(BaseModel):
    statement: str
    source_entry_ids: List[str]
    metadata: Optional[Dict[str, Any]] = None
    initial_confidence: float = 0.5


class LinkRequest(BaseModel):
    source_atom_id: str
    target_atom_id: str
    relation: str
    weight: float = 1.0


class RetrievalRequest(BaseModel):
    query: str
    mode: str = "COLLECTIVE"
    limit: int = 20


class RetrievalFeedbackRequest(BaseModel):
    cognitive_event_id: Optional[str] = None
    outcome_id: Optional[str] = None
    useful_atom_ids: List[str] = []
    harmful_atom_ids: List[str] = []
    irrelevant_atom_ids: List[str] = []
    evidence_ids: List[str] = []


@app.on_event("startup")
async def startup_event():
    global layer
    store_path = Path(os.getenv("MEMORY_STORE_PATH", "./data"))
    store_path.mkdir(parents=True, exist_ok=True)
    matrix_id = os.getenv("MEMORY_MATRIX_ID", "long_term_matrix")
    glyph_keys = _load_keyring()
    glyph_key_id = os.getenv("AIMS_GLYPH_KEY_ID")
    glyph_key = glyph_keys.get(glyph_key_id) if glyph_key_id else None
    security_mode = os.getenv("AIMS_SECURITY_MODE") or ("authenticated" if glyph_key else "visual")
    if security_mode == "authenticated" and (not glyph_key_id or glyph_key is None):
        raise RuntimeError("Authenticated A.I.M.S. requires AIMS_GLYPH_KEY_ID and its keyring entry")
    bind_host = os.getenv("AIMS_BIND_HOST", "127.0.0.1")
    if bind_host not in {"127.0.0.1", "::1", "localhost"} and not api_token:
        raise RuntimeError("Remote A.I.M.S. binding requires AIMS_API_TOKEN")
    try:
        layer = AIMSMemorySystem(
            store_path, matrix_id=matrix_id,
            glyph_key=glyph_key, glyph_key_id=glyph_key_id, glyph_keys=glyph_keys,
            security_mode=security_mode,
        )
        logger.info("Memory layer ready: %s entries loaded", layer.long_term.total_entries)
    except IntegrityError as e:
        logger.error("Failed to initialize memory layer: %s", e)
        raise


def _require_layer() -> AIMSMemorySystem:
    if layer is None:
        raise HTTPException(status_code=503, detail="Memory layer not initialized")
    return layer


@app.get("/health")
async def health():
    m = _require_layer()
    return {"status": "healthy", "ltm_ready": m.long_term.ready, "entries": m.long_term.total_entries}


# Versioned headless API. These contracts are intentionally presentation-free.
@app.get("/api/v1/status")
async def api_status():
    return {"system": "A.I.M.S.", "name": "Agnostic Immutable Memory System", **_require_layer().full_status()}


@app.get("/api/v1/memory/summary")
async def api_memory_summary():
    m = _require_layer()
    return {"long_term": m.long_term.get_statistics(), "short_term": m.short_term.stats(), "vault": m.vault.stats(), "skg": m.skg.stats()}


@app.get("/api/v1/indexes/status")
async def api_indexes_status():
    return _require_layer().indexes.status()


@app.get("/api/v1/retrievals")
async def api_retrievals(limit: int = 50):
    return {"items": _require_layer().retrieval_ledger.recent(limit)}


@app.post("/api/v1/retrievals")
async def api_retrieve(req: RetrievalRequest):
    try:
        return _require_layer().retrieve(req.query, mode=req.mode, limit=req.limit)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/api/v1/retrievals/{retrieval_id}")
async def api_retrieval(retrieval_id: str):
    receipt = _require_layer().retrieval(retrieval_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Retrieval receipt not found")
    return receipt


@app.post("/api/v1/retrievals/{retrieval_id}/feedback")
async def api_retrieval_feedback(retrieval_id: str, req: RetrievalFeedbackRequest):
    if _require_layer().retrieval(retrieval_id) is None:
        raise HTTPException(status_code=404, detail="Retrieval receipt not found")
    try:
        return _require_layer().evaluate_cognitive_outcome(
            retrieval_id, req.cognitive_event_id, req.outcome_id, req.useful_atom_ids,
            req.harmful_atom_ids, req.irrelevant_atom_ids, req.evidence_ids,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/api/v1/skg/status")
async def api_skg_status():
    return _require_layer().skg.stats()


@app.get("/api/v1/skg/activity")
async def api_skg_activity():
    return {"relationships": _require_layer().vault.relationships(), "durable": True}


@app.get("/api/v1/vault/integrity")
async def api_vault_integrity():
    m = _require_layer()
    ltm_valid, ltm_corrupted = m.long_term.verify_chain()
    vault_valid, vault_corrupted = m.vault.event_ledger.verify_chain()
    return {
        "vault_status": "verified" if ltm_valid and vault_valid else "corrupted",
        "memory_ledger": {"chain_valid": ltm_valid, "corrupted_sequences": ltm_corrupted},
        "vault_event_ledger": {"chain_valid": vault_valid, "corrupted_sequences": vault_corrupted},
        "security_mode": m.long_term.security_mode,
        "active_glyph_key_id": m.long_term.glyph_key_id,
    }


@app.post("/stm/observe")
async def observe(req: ObserveRequest):
    m = _require_layer()
    item = m.observe(req.content, tags=req.tags)
    return {"item_id": item.item_id, "vivacity": item.vivacity}


@app.get("/stm/candidates")
async def stm_candidates():
    m = _require_layer()
    return [{"item_id": i.item_id, "content": i.content, "touch_count": i.touch_count, "vivacity": i.vivacity}
            for i in m.short_term.promotion_candidates()]


@app.post("/ltm/commit")
async def commit(req: CommitRequest):
    m = _require_layer()
    try:
        entry_type = EntryType[req.entry_type.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid entry_type: {req.entry_type}")
    try:
        entry = m.commit(entry_type, req.content, metadata=req.metadata, writer_id=req.writer_id)
    except IntegrityError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return entry.to_dict()


@app.get("/ltm/entry/{entry_id}")
async def read_entry(entry_id: str):
    m = _require_layer()
    entry = m.long_term.read_entry(entry_id=entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry.to_dict()


@app.get("/ltm/verify")
async def verify_ltm():
    m = _require_layer()
    is_valid, corrupted = m.long_term.verify_chain()
    return {"chain_valid": is_valid, "corrupted_sequences": corrupted}


@app.post("/vault/apriori")
async def add_apriori(req: AprioriRequest):
    m = _require_layer()
    atom = m.assert_apriori(req.statement, metadata=req.metadata)
    return atom.to_dict()


@app.post("/vault/aposteriori")
async def add_aposteriori(req: AposterioriRequest):
    m = _require_layer()
    source_entries = []
    for eid in req.source_entry_ids:
        entry = m.long_term.read_entry(entry_id=eid)
        if not entry:
            raise HTTPException(status_code=404, detail=f"Source entry not found: {eid}")
        source_entries.append(entry)
    atom = m.derive_aposteriori(req.statement, source_entries, metadata=req.metadata, initial_confidence=req.initial_confidence)
    return atom.to_dict()


@app.post("/skg/link")
async def link(req: LinkRequest):
    m = _require_layer()
    try:
        relation = Relation(req.relation)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid relation: {req.relation}")
    edge = m.link(req.source_atom_id, req.target_atom_id, relation, weight=req.weight)
    return {"source_id": edge.source_id, "target_id": edge.target_id, "relation": edge.relation.value}


@app.get("/skg/truth")
async def truth(min_confidence: float = 0.0):
    m = _require_layer()
    return m.truth(min_confidence=min_confidence)


@app.get("/atom/{atom_id}/trace")
async def trace(atom_id: str):
    m = _require_layer()
    result = m.trace(atom_id)
    if not result:
        raise HTTPException(status_code=404, detail="Atom not found")
    return result


@app.post("/maintenance/run")
async def run_maintenance(self_eval_passes: int = 3):
    m = _require_layer()
    return m.run_maintenance_cycle(self_eval_passes=self_eval_passes)


@app.get("/status")
async def status():
    m = _require_layer()
    return m.full_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("service:app", host=os.getenv("AIMS_BIND_HOST", "127.0.0.1"), port=int(os.getenv("PORT", 8000)), reload=False)
