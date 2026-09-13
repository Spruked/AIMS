"""Persistent, rebuildable Vault indexes. They are never authoritative."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

from .vault import AtomStatus, Vault, VaultAtom, VaultType


class VaultIndexes:
    INDEXES = ("a_priori", "a_posteriori", "collective")

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS vault_index (
                    index_name TEXT NOT NULL, atom_id TEXT NOT NULL, statement TEXT NOT NULL,
                    status TEXT NOT NULL, confidence REAL NOT NULL, PRIMARY KEY(index_name, atom_id)
                )
            """)
            connection.commit()
        finally:
            connection.close()

    def _connect(self):
        return sqlite3.connect(self.path)

    def rebuild(self, vault: Vault):
        connection = self._connect()
        try:
            connection.execute("DELETE FROM vault_index")
            for atom in vault.all_atoms():
                self.upsert(atom, connection)
            connection.commit()
        finally:
            connection.close()

    def upsert(self, atom: VaultAtom, connection=None):
        names = ["collective", atom.vault_type.value]
        owns_connection = connection is None
        if owns_connection: connection = self._connect()
        try:
            for index_name in names:
                connection.execute(
                    "INSERT OR REPLACE INTO vault_index(index_name, atom_id, statement, status, confidence) VALUES (?, ?, ?, ?, ?)",
                    (index_name, atom.atom_id, atom.statement, atom.status.value, atom.confidence),
                )
            if owns_connection: connection.commit()
        finally:
            if owns_connection: connection.close()

    def search(
        self, vault: Vault, query: str, index_name: str = "collective", limit: int = 20,
        utilities: Optional[Mapping[str, float]] = None,
        skg_weight_for: Optional[Callable[[str], float]] = None,
    ) -> List[Dict[str, Any]]:
        if index_name not in self.INDEXES: raise ValueError(f"Unknown index: {index_name}")
        tokens = [token.casefold() for token in query.split() if token]
        connection = self._connect()
        try:
            rows = connection.execute("SELECT atom_id FROM vault_index WHERE index_name = ? AND status = ? ORDER BY confidence DESC", (index_name, AtomStatus.ACTIVE.value)).fetchall()
        finally:
            connection.close()
        results = []
        utilities = utilities or {}
        for (atom_id,) in rows:
            atom = vault.get(atom_id)
            if not atom: continue
            statement = atom.statement.casefold()
            if tokens and not all(token in statement for token in tokens): continue
            semantic_relevance = (sum(statement.count(token) for token in tokens) / max(1, len(tokens))) if tokens else 1.0
            utility = float(utilities.get(atom_id, 0.0))
            skg_weight = float(skg_weight_for(atom_id) if skg_weight_for else 0.5)
            relevance_score = (0.35 * semantic_relevance) + (0.35 * atom.confidence) + (0.20 * ((utility + 1.0) / 2.0)) + (0.10 * skg_weight)
            results.append({
                **atom.to_dict(), "source_index": index_name, **vault.provenance_for(atom_id),
                "semantic_relevance": semantic_relevance, "retrieval_utility": utility,
                "skg_weight": skg_weight, "relevance_score": relevance_score,
            })
        return sorted(results, key=lambda item: (-item["relevance_score"], item["atom_id"]))[:limit]

    def status(self) -> Dict[str, Any]:
        connection = self._connect()
        try:
            counts = dict(connection.execute("SELECT index_name, COUNT(*) FROM vault_index GROUP BY index_name").fetchall())
        finally:
            connection.close()
        return {"persistent": True, "path": str(self.path), "counts": {name: counts.get(name, 0) for name in self.INDEXES}}
