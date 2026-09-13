"""SQLite forensic receipts and learned retrieval utility for A.I.M.S."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .temporal import TriTimestamp


class RetrievalLedger:
    def __init__(self, path: Path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS retrieval_events (
                    retrieval_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, retrieval_mode TEXT NOT NULL,
                    query TEXT NOT NULL, retrieval_set_hash TEXT NOT NULL, result_count INTEGER NOT NULL,
                    tri_timestamp TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS retrieval_snapshots (
                    retrieval_id TEXT NOT NULL, position INTEGER NOT NULL, payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL, PRIMARY KEY(retrieval_id, position)
                );
                CREATE TABLE IF NOT EXISTS retrieval_feedback (
                    feedback_id TEXT PRIMARY KEY, retrieval_id TEXT NOT NULL, created_at TEXT NOT NULL,
                    cognitive_event_id TEXT, outcome_id TEXT, useful_atom_ids TEXT NOT NULL,
                    harmful_atom_ids TEXT NOT NULL, irrelevant_atom_ids TEXT NOT NULL, evidence_ids TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS retrieval_utility (
                    atom_id TEXT PRIMARY KEY, utility REAL NOT NULL, useful_count INTEGER NOT NULL,
                    harmful_count INTEGER NOT NULL, irrelevant_count INTEGER NOT NULL
                );
            """)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(retrieval_events)")}
            if "tri_timestamp" not in columns:
                connection.execute("ALTER TABLE retrieval_events ADD COLUMN tri_timestamp TEXT")
            connection.commit()
        finally: connection.close()

    def _connect(self): return sqlite3.connect(self.path)

    @staticmethod
    def _snapshot_hash(payload: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

    def record(self, retrieval_mode: str, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        retrieval_id, timestamp = str(uuid.uuid4()), TriTimestamp.now()
        snapshots = []
        for position, result in enumerate(results):
            snapshot = {**result, "rank": position + 1}
            snapshots.append({**snapshot, "returned_payload_snapshot": result, "returned_payload_hash": self._snapshot_hash(result)})
        set_hash = self._snapshot_hash({"retrieval_mode": retrieval_mode, "query": query, "ordered_results": snapshots})
        receipt = {
            "retrieval_id": retrieval_id, "query": query, "retrieval_mode": retrieval_mode,
            "retrieval_set_hash": set_hash, "result_count": len(snapshots),
            "tri_timestamp": timestamp.to_dict(), "results": snapshots,
        }
        connection = self._connect()
        try:
            connection.execute("INSERT INTO retrieval_events VALUES (?, ?, ?, ?, ?, ?, ?)", (retrieval_id, timestamp.standard, retrieval_mode, query, set_hash, len(snapshots), json.dumps(timestamp.to_dict(), sort_keys=True)))
            connection.executemany("INSERT INTO retrieval_snapshots VALUES (?, ?, ?, ?)", [(retrieval_id, index, json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False), snapshot["returned_payload_hash"]) for index, snapshot in enumerate(snapshots)])
            connection.commit()
        finally: connection.close()
        return receipt

    def get(self, retrieval_id: str) -> Optional[Dict[str, Any]]:
        connection = self._connect()
        try:
            event = connection.execute("SELECT retrieval_id, retrieval_mode, query, retrieval_set_hash, result_count, tri_timestamp FROM retrieval_events WHERE retrieval_id = ?", (retrieval_id,)).fetchone()
            if not event: return None
            snapshots = connection.execute("SELECT payload_json, payload_hash FROM retrieval_snapshots WHERE retrieval_id = ? ORDER BY position", (retrieval_id,)).fetchall()
        finally: connection.close()
        results = []
        for payload_json, payload_hash in snapshots:
            payload = json.loads(payload_json)
            if self._snapshot_hash(payload["returned_payload_snapshot"]) != payload_hash: raise ValueError("Retrieval payload snapshot hash mismatch")
            results.append(payload)
        return {"retrieval_id": event[0], "retrieval_mode": event[1], "query": event[2], "retrieval_set_hash": event[3], "result_count": event[4], "tri_timestamp": json.loads(event[5]), "results": results}

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        connection = self._connect()
        try: ids = connection.execute("SELECT retrieval_id FROM retrieval_events ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
        finally: connection.close()
        return [self.get(row[0]) for row in ids]

    def utilities(self) -> Dict[str, float]:
        connection = self._connect()
        try: rows = connection.execute("SELECT atom_id, utility FROM retrieval_utility").fetchall()
        finally: connection.close()
        return dict(rows)

    def record_feedback(
        self, retrieval_id: str, useful_atom_ids: Iterable[str] = (), harmful_atom_ids: Iterable[str] = (),
        irrelevant_atom_ids: Iterable[str] = (), cognitive_event_id: Optional[str] = None,
        outcome_id: Optional[str] = None, evidence_ids: Iterable[str] = (),
    ) -> Dict[str, Any]:
        useful, harmful, irrelevant, evidence = list(useful_atom_ids), list(harmful_atom_ids), list(irrelevant_atom_ids), list(evidence_ids)
        feedback_id, timestamp = str(uuid.uuid4()), TriTimestamp.now()
        changes: Dict[str, float] = {}
        for atom_id in useful: changes[atom_id] = changes.get(atom_id, 0.0) + 0.30
        for atom_id in harmful: changes[atom_id] = changes.get(atom_id, 0.0) - 0.30
        for atom_id in irrelevant: changes[atom_id] = changes.get(atom_id, 0.0) - 0.08
        connection = self._connect()
        try:
            connection.execute("INSERT INTO retrieval_feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (feedback_id, retrieval_id, timestamp.standard, cognitive_event_id, outcome_id, json.dumps(useful), json.dumps(harmful), json.dumps(irrelevant), json.dumps(evidence)))
            for atom_id, delta in changes.items():
                row = connection.execute("SELECT utility, useful_count, harmful_count, irrelevant_count FROM retrieval_utility WHERE atom_id = ?", (atom_id,)).fetchone() or (0.0, 0, 0, 0)
                utility = max(-1.0, min(1.0, row[0] + delta))
                connection.execute("INSERT OR REPLACE INTO retrieval_utility VALUES (?, ?, ?, ?, ?)", (atom_id, utility, row[1] + (atom_id in useful), row[2] + (atom_id in harmful), row[3] + (atom_id in irrelevant)))
            connection.commit()
        finally: connection.close()
        return {"feedback_id": feedback_id, "tri_timestamp": timestamp.to_dict(), "utility_changes": changes}
