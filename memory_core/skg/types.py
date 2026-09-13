"""Deterministic, serializable SKG types shared by all graph backends."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..temporal import TriTimestamp


class Relation(Enum):
    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    CORROBORATES = "corroborates"
    CONTEXT_DEPENDENT = "context_dependent"
    TEMPORALLY_PRECEDES = "temporally_precedes"
    CAUSALLY_RELATED = "causally_related"
    SAME_ENTITY = "same_entity"


class EdgeState(Enum):
    ACTIVE = "active"
    WEAKENED = "weakened"
    DORMANT = "dormant"
    RETIRED = "retired"
    PRUNED = "pruned"


@dataclass
class Edge:
    source_id: str
    target_id: str
    relation: Relation
    weight: float = 1.0
    confidence: float = 1.0
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: EdgeState = EdgeState.ACTIVE
    created_at: TriTimestamp = field(default_factory=TriTimestamp.now)
    last_reinforced_at: Optional[TriTimestamp] = None
    last_challenged_at: Optional[TriTimestamp] = None
    reinforcement_count: int = 0
    challenge_count: int = 0
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_atom_id": self.source_id,
            "target_atom_id": self.target_id,
            "relationship_type": self.relation.value,
            "weight": self.weight,
            "confidence": self.confidence,
            "state": self.state.value,
            "created_at": self.created_at.to_dict(),
            "last_reinforced_at": self.last_reinforced_at.to_dict() if self.last_reinforced_at else None,
            "last_challenged_at": self.last_challenged_at.to_dict() if self.last_challenged_at else None,
            "reinforcement_count": self.reinforcement_count,
            "challenge_count": self.challenge_count,
            "supporting_evidence": list(self.supporting_evidence),
            "contradicting_evidence": list(self.contradicting_evidence),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        return cls(
            edge_id=data["edge_id"],
            source_id=data["source_atom_id"],
            target_id=data["target_atom_id"],
            relation=Relation(data["relationship_type"]),
            weight=float(data["weight"]),
            confidence=float(data.get("confidence", 1.0)),
            state=EdgeState(data.get("state", EdgeState.ACTIVE.value)),
            created_at=TriTimestamp.from_dict(data["created_at"]),
            last_reinforced_at=TriTimestamp.from_dict(data["last_reinforced_at"]) if data.get("last_reinforced_at") else None,
            last_challenged_at=TriTimestamp.from_dict(data["last_challenged_at"]) if data.get("last_challenged_at") else None,
            reinforcement_count=int(data.get("reinforcement_count", 0)),
            challenge_count=int(data.get("challenge_count", 0)),
            supporting_evidence=list(data.get("supporting_evidence", [])),
            contradicting_evidence=list(data.get("contradicting_evidence", [])),
        )

    def copy(self) -> "Edge":
        return Edge.from_dict(self.to_dict())


def state_for_weight(weight: float) -> EdgeState:
    if weight >= 0.70:
        return EdgeState.ACTIVE
    if weight >= 0.40:
        return EdgeState.WEAKENED
    if weight >= 0.15:
        return EdgeState.DORMANT
    if weight >= 0.05:
        return EdgeState.RETIRED
    return EdgeState.PRUNED


def transition_event(previous: EdgeState, resulting: EdgeState, previous_weight: float, resulting_weight: float) -> str:
    if resulting is EdgeState.PRUNED:
        return "skg.edge_pruned"
    if resulting is EdgeState.RETIRED:
        return "skg.edge_retired"
    if resulting_weight > previous_weight:
        return "skg.edge_strengthened"
    return "skg.edge_weakened"
