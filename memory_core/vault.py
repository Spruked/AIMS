"""Persistent immutable Vault evidence and reconstructed atom state."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from .long_term import EntryType, KeyMaterial, LongTermMemory
from .temporal import TriTimestamp


class VaultType(Enum):
    A_PRIORI = "a_priori"
    A_POSTERIORI = "a_posteriori"


class AtomStatus(Enum):
    PROBATION = "probation"
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass
class VaultAtom:
    atom_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vault_type: VaultType = VaultType.A_POSTERIORI
    statement: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    derived_from: List[str] = field(default_factory=list)
    confidence: float = 0.5
    status: AtomStatus = AtomStatus.PROBATION
    support_count: int = 0
    challenge_count: int = 0
    created: TriTimestamp = field(default_factory=TriTimestamp.now)
    last_evaluated: TriTimestamp = field(default_factory=TriTimestamp.now)
    evaluation_passes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "atom_id": self.atom_id, "vault_type": self.vault_type.value,
            "statement": self.statement, "metadata": self.metadata,
            "derived_from": self.derived_from, "confidence": self.confidence,
            "status": self.status.value, "support_count": self.support_count,
            "challenge_count": self.challenge_count, "created": self.created.to_dict(),
            "last_evaluated": self.last_evaluated.to_dict(), "evaluation_passes": self.evaluation_passes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VaultAtom":
        return cls(
            atom_id=data["atom_id"], vault_type=VaultType(data["vault_type"]),
            statement=data["statement"], metadata=data.get("metadata", {}),
            derived_from=list(data.get("derived_from", [])), confidence=float(data["confidence"]),
            status=AtomStatus(data["status"]), support_count=int(data.get("support_count", 0)),
            challenge_count=int(data.get("challenge_count", 0)),
            created=TriTimestamp.from_dict(data["created"]),
            last_evaluated=TriTimestamp.from_dict(data["last_evaluated"]),
            evaluation_passes=int(data.get("evaluation_passes", 0)),
        )


A_PRIORI_FLOOR = 0.55
A_POSTERIORI_PRUNE_FLOOR = 0.20
PROMOTION_CONFIDENCE = 0.65
PROMOTION_SUPPORT_COUNT = 3


class Vault:
    """Authoritative atom evidence. Current state is replayed, never overwritten."""

    def __init__(
        self, store_path: Optional[Path] = None, matrix_id: str = "aims",
        glyph_key: Optional[KeyMaterial] = None, glyph_key_id: Optional[str] = None,
        glyph_keys: Optional[Mapping[str, KeyMaterial]] = None, security_mode: Optional[str] = None,
    ):
        self._atoms: Dict[str, VaultAtom] = {}
        self._relationships: List[Dict[str, Any]] = []
        self._skg_events: List[Dict[str, Any]] = []
        self._atom_provenance: Dict[str, Dict[str, Any]] = {}
        self.event_ledger: Optional[LongTermMemory] = None
        if store_path is not None:
            self.event_ledger = LongTermMemory(
                Path(store_path) / "vault", matrix_id=f"{matrix_id}_vault_events",
                glyph_key=glyph_key, glyph_key_id=glyph_key_id, glyph_keys=glyph_keys,
                security_mode=security_mode,
            )
            self._replay()

    def _record(self, event: str, payload: Dict[str, Any]):
        if self.event_ledger is not None:
            return self.event_ledger.write_entry(EntryType.SYSTEM_EVENT, {"event": event, **payload}, writer_id="vault")
        return None

    @staticmethod
    def _provenance(entry) -> Dict[str, Any]:
        return {
            "source_record_id": entry.entry_id if entry else None,
            "source_glyph": entry.glyph if entry else None,
            "record_hash": entry.entry_hash if entry else None,
        }

    def _replay(self):
        assert self.event_ledger is not None
        for entry in self.event_ledger.entries:
            content = entry.content
            event = content.get("event")
            if event in {"ledger_genesis", None}:
                continue
            if event in {"vault.atom_added", "vault.evaluated", "vault.retired"}:
                atom = VaultAtom.from_dict(content["atom"])
                self._atoms[atom.atom_id] = atom
                if event == "vault.atom_added":
                    self._atom_provenance[atom.atom_id] = self._provenance(entry)
            elif event == "vault.relationship":
                self._relationships.append(content["relationship"])
            elif event and event.startswith("skg."):
                self._skg_events.append({"event": event, **content})

    def _admit(self, atom: VaultAtom, event: str) -> VaultAtom:
        entry = self._record(event, {"atom": atom.to_dict()})
        self._atoms[atom.atom_id] = atom
        self._atom_provenance[atom.atom_id] = self._provenance(entry)
        return atom

    def add_apriori(self, statement: str, metadata: Optional[Dict[str, Any]] = None) -> VaultAtom:
        return self._admit(VaultAtom(vault_type=VaultType.A_PRIORI, statement=statement, metadata=metadata or {}, confidence=1.0, status=AtomStatus.ACTIVE), "vault.atom_added")

    def add_aposteriori(self, statement: str, derived_from: List[str], metadata: Optional[Dict[str, Any]] = None, initial_confidence: float = 0.5) -> VaultAtom:
        return self._admit(VaultAtom(vault_type=VaultType.A_POSTERIORI, statement=statement, metadata=metadata or {}, derived_from=list(derived_from), confidence=initial_confidence, status=AtomStatus.PROBATION), "vault.atom_added")

    def reinforce(self, atom_id: str, weight: float = 0.1) -> Optional[VaultAtom]:
        atom = self._atoms.get(atom_id)
        if not atom: return None
        atom.confidence = min(1.0, atom.confidence + weight); atom.support_count += 1
        atom.last_evaluated = TriTimestamp.now(); atom.evaluation_passes += 1
        if atom.vault_type == VaultType.A_POSTERIORI and atom.status == AtomStatus.PROBATION and atom.confidence >= PROMOTION_CONFIDENCE and atom.support_count >= PROMOTION_SUPPORT_COUNT:
            atom.status = AtomStatus.ACTIVE
        self._record("vault.evaluated", {"outcome": "reinforce", "weight": weight, "atom": atom.to_dict()})
        return atom

    def challenge(self, atom_id: str, weight: float = 0.1) -> Optional[VaultAtom]:
        atom = self._atoms.get(atom_id)
        if not atom: return None
        floor = A_PRIORI_FLOOR if atom.vault_type == VaultType.A_PRIORI else 0.0
        atom.confidence = max(floor, atom.confidence - weight); atom.challenge_count += 1
        atom.last_evaluated = TriTimestamp.now(); atom.evaluation_passes += 1
        self._record("vault.evaluated", {"outcome": "challenge", "weight": weight, "atom": atom.to_dict()})
        return atom

    def retire(self, atom_id: str, reason: str = "low_confidence") -> Optional[VaultAtom]:
        atom = self._atoms.get(atom_id)
        if not atom or atom.vault_type == VaultType.A_PRIORI or atom.status == AtomStatus.RETIRED: return None
        atom.status = AtomStatus.RETIRED; atom.last_evaluated = TriTimestamp.now()
        self._record("vault.retired", {"reason": reason, "atom": atom.to_dict()})
        return atom

    def record_relationship(self, source_id: str, target_id: str, relation: str, weight: float) -> Dict[str, Any]:
        relationship = {"source_id": source_id, "target_id": target_id, "relation": relation, "weight": weight}
        self._record("vault.relationship", {"relationship": relationship})
        self._relationships.append(relationship)
        return relationship

    def record_skg_event(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not event.startswith("skg."):
            raise ValueError("SKG event names must begin with 'skg.'")
        entry = self._record(event, payload)
        record = {"event": event, **payload, "vault_event_id": entry.entry_id if entry else None}
        self._skg_events.append(record)
        return record

    def record_cognitive_evaluation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        entry = self._record("vault.cognitive_evaluation", payload)
        return {"vault_event_id": entry.entry_id if entry else None, **payload}

    def relationships(self) -> List[Dict[str, Any]]:
        return list(self._relationships)

    def skg_events(self) -> List[Dict[str, Any]]:
        return list(self._skg_events)

    def provenance_for(self, atom_id: str) -> Dict[str, Any]:
        return dict(self._atom_provenance.get(atom_id, {}))

    def source_of_truth(self, min_confidence: float = 0.0) -> List[VaultAtom]:
        return [atom for atom in self._atoms.values() if atom.status == AtomStatus.ACTIVE and atom.confidence >= min_confidence]

    def get(self, atom_id: str) -> Optional[VaultAtom]: return self._atoms.get(atom_id)
    def all_atoms(self) -> List[VaultAtom]: return list(self._atoms.values())

    def stats(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}; by_type: Dict[str, int] = {}
        for atom in self._atoms.values():
            by_status[atom.status.value] = by_status.get(atom.status.value, 0) + 1
            by_type[atom.vault_type.value] = by_type.get(atom.vault_type.value, 0) + 1
        return {"total_atoms": len(self._atoms), "by_status": by_status, "by_type": by_type, "persistent": self.event_ledger is not None, "event_count": self.event_ledger.total_entries if self.event_ledger else 0}
