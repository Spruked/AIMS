#!/usr/bin/env python3
"""
service.py
Host-agnostic HTTP service around CognitiveMemoryLayer.

No mission-specific sync target, no external agent identity, no
proprietary time authority. Configure only where the store lives and
what to call it.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory_core import AIMSMemorySystem, EntryType, IntegrityError, Relation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory-layer-service")

app = FastAPI(
    title="A.I.M.S. — Agnostic Immutable Memory System",
    description="Immutable Vault System + short-term memory + a priori/a posteriori indexes + SKG",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

layer: Optional[AIMSMemorySystem] = None


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


@app.on_event("startup")
async def startup_event():
    global layer
    store_path = Path(os.getenv("MEMORY_STORE_PATH", "./data"))
    store_path.mkdir(parents=True, exist_ok=True)
    matrix_id = os.getenv("MEMORY_MATRIX_ID", "long_term_matrix")
    glyph_key = os.getenv("AIMS_GLYPH_KEY")
    glyph_key_id = os.getenv("AIMS_GLYPH_KEY_ID") if glyph_key else None
    if glyph_key and not glyph_key_id:
        raise RuntimeError("AIMS_GLYPH_KEY_ID is required when AIMS_GLYPH_KEY is set")
    try:
        layer = AIMSMemorySystem(
            store_path, matrix_id=matrix_id,
            glyph_key=glyph_key, glyph_key_id=glyph_key_id,
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
    uvicorn.run("service:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
