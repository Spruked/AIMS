"""Replayable, mutable Structured Knowledge Graph derived from Vault evidence."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .temporal import TriTimestamp
from .vault import A_POSTERIORI_PRUNE_FLOOR, AtomStatus, Vault, VaultAtom, VaultType


class Relation(Enum):
    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


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
            "edge_id": self.edge_id, "source_atom_id": self.source_id, "target_atom_id": self.target_id,
            "relationship_type": self.relation.value, "weight": self.weight, "confidence": self.confidence,
            "state": self.state.value, "created_at": self.created_at.to_dict(),
            "last_reinforced_at": self.last_reinforced_at.to_dict() if self.last_reinforced_at else None,
            "last_challenged_at": self.last_challenged_at.to_dict() if self.last_challenged_at else None,
            "reinforcement_count": self.reinforcement_count, "challenge_count": self.challenge_count,
            "supporting_evidence": self.supporting_evidence, "contradicting_evidence": self.contradicting_evidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        return cls(
            edge_id=data["edge_id"], source_id=data["source_atom_id"], target_id=data["target_atom_id"],
            relation=Relation(data["relationship_type"]), weight=float(data["weight"]),
            confidence=float(data.get("confidence", 1.0)), state=EdgeState(data["state"]),
            created_at=TriTimestamp.from_dict(data["created_at"]),
            last_reinforced_at=TriTimestamp.from_dict(data["last_reinforced_at"]) if data.get("last_reinforced_at") else None,
            last_challenged_at=TriTimestamp.from_dict(data["last_challenged_at"]) if data.get("last_challenged_at") else None,
            reinforcement_count=int(data.get("reinforcement_count", 0)), challenge_count=int(data.get("challenge_count", 0)),
            supporting_evidence=list(data.get("supporting_evidence", [])), contradicting_evidence=list(data.get("contradicting_evidence", [])),
        )


class SelfKnowledgeGraph:
    """Mutable graph state. Every lifecycle transition is preserved by Vault."""

    def __init__(self, vault: Vault):
        self.vault = vault
        self._edges: Dict[str, Edge] = {}
        self._node_aliases: Dict[str, str] = {}

    def link(self, source_id: str, target_id: str, relation: Relation, weight: float = 1.0, persist: bool = True) -> Edge:
        edge = Edge(source_id=source_id, target_id=target_id, relation=relation, weight=max(0.0, min(1.0, weight)))
        self._edges[edge.edge_id] = edge
        if persist:
            self.vault.record_skg_event("skg.edge_created", {"edge": edge.to_dict(), "reason": "relationship_declared"})
        return edge

    def rebuild_from_vault(self):
        self._edges.clear(); self._node_aliases.clear()
        for relationship in self.vault.relationships():
            self.link(relationship["source_id"], relationship["target_id"], Relation(relationship["relation"]), float(relationship["weight"]), persist=False)
        for event in self.vault.skg_events():
            if "edge" in event:
                edge = Edge.from_dict(event["edge"])
                self._edges[edge.edge_id] = edge
            if event["event"] == "skg.node_merged":
                self._node_aliases.update(event["aliases"])

    def resolve_node(self, atom_id: str) -> str:
        while atom_id in self._node_aliases:
            atom_id = self._node_aliases[atom_id]
        return atom_id

    def edge(self, edge_id: str) -> Optional[Edge]: return self._edges.get(edge_id)
    def all_edges(self) -> List[Edge]: return list(self._edges.values())
    def active_edges(self) -> List[Edge]: return [edge for edge in self._edges.values() if edge.state not in {EdgeState.RETIRED, EdgeState.PRUNED}]

    def edges_for(self, atom_id: str, relation: Optional[Relation] = None, include_inactive: bool = False) -> List[Edge]:
        atom_id = self.resolve_node(atom_id)
        source = self._edges.values() if include_inactive else self.active_edges()
        return [edge for edge in source if (not relation or edge.relation == relation) and (self.resolve_node(edge.source_id) == atom_id or self.resolve_node(edge.target_id) == atom_id)]

    def neighbors(self, atom_id: str, relation: Optional[Relation] = None) -> List[VaultAtom]:
        neighbors = []
        for edge in self.edges_for(atom_id, relation):
            other = edge.target_id if self.resolve_node(edge.source_id) == self.resolve_node(atom_id) else edge.source_id
            atom = self.vault.get(self.resolve_node(other))
            if atom: neighbors.append(atom)
        return neighbors

    @staticmethod
    def _state_for_weight(weight: float) -> EdgeState:
        if weight >= 0.70: return EdgeState.ACTIVE
        if weight >= 0.40: return EdgeState.WEAKENED
        if weight >= 0.15: return EdgeState.DORMANT
        if weight >= 0.05: return EdgeState.RETIRED
        return EdgeState.PRUNED

    def _transition(self, edge: Edge, event: str, reason: str, evidence_ids: Iterable[str] = ()) -> Edge:
        previous_state, previous_weight = edge.state, edge.weight
        self.vault.record_skg_event(event, {
            "edge": edge.to_dict(), "previous_state": previous_state.value, "new_state": edge.state.value,
            "previous_weight": previous_weight, "new_weight": edge.weight, "reason": reason,
            "evidence_ids": list(evidence_ids), "evaluation_id": str(uuid.uuid4()),
        })
        return edge

    def strengthen_edge(self, edge_id: str, amount: float = 0.1, evidence_ids: Iterable[str] = (), reason: str = "supporting_outcome") -> Edge:
        edge = self._edges[edge_id]; previous_state, previous_weight = edge.state, edge.weight
        edge.weight = min(1.0, edge.weight + amount); edge.confidence = min(1.0, edge.confidence + amount / 2)
        edge.reinforcement_count += 1; edge.last_reinforced_at = TriTimestamp.now()
        edge.supporting_evidence = list(dict.fromkeys([*edge.supporting_evidence, *evidence_ids]))
        edge.state = self._state_for_weight(edge.weight)
        self.vault.record_skg_event("skg.edge_strengthened", {"edge": edge.to_dict(), "previous_state": previous_state.value, "new_state": edge.state.value, "previous_weight": previous_weight, "new_weight": edge.weight, "reason": reason, "evidence_ids": list(evidence_ids), "evaluation_id": str(uuid.uuid4())})
        return edge

    def weaken_edge(self, edge_id: str, amount: float = 0.1, evidence_ids: Iterable[str] = (), reason: str = "contradicting_outcome") -> Edge:
        edge = self._edges[edge_id]; previous_state, previous_weight = edge.state, edge.weight
        edge.weight = max(0.0, edge.weight - amount); edge.confidence = max(0.0, edge.confidence - amount / 2)
        edge.challenge_count += 1; edge.last_challenged_at = TriTimestamp.now()
        edge.contradicting_evidence = list(dict.fromkeys([*edge.contradicting_evidence, *evidence_ids]))
        edge.state = self._state_for_weight(edge.weight)
        name = "skg.edge_pruned" if edge.state == EdgeState.PRUNED else "skg.edge_retired" if edge.state == EdgeState.RETIRED else "skg.edge_weakened"
        self.vault.record_skg_event(name, {"edge": edge.to_dict(), "previous_state": previous_state.value, "new_state": edge.state.value, "previous_weight": previous_weight, "new_weight": edge.weight, "reason": reason, "evidence_ids": list(evidence_ids), "evaluation_id": str(uuid.uuid4())})
        return edge

    def retire_edge(self, edge_id: str, reason: str = "explicit_retirement", evidence_ids: Iterable[str] = ()) -> Edge:
        edge = self._edges[edge_id]; previous_state, previous_weight = edge.state, edge.weight; edge.state = EdgeState.RETIRED
        self.vault.record_skg_event("skg.edge_retired", {"edge": edge.to_dict(), "previous_state": previous_state.value, "new_state": edge.state.value, "previous_weight": previous_weight, "new_weight": edge.weight, "reason": reason, "evidence_ids": list(evidence_ids), "evaluation_id": str(uuid.uuid4())})
        return edge

    def prune_edge(self, edge_id: str, reason: str = "cognitive_weight_pruned", evidence_ids: Iterable[str] = ()) -> Edge:
        edge = self._edges[edge_id]; previous_state, previous_weight = edge.state, edge.weight; edge.state = EdgeState.PRUNED
        self.vault.record_skg_event("skg.edge_pruned", {"edge": edge.to_dict(), "previous_state": previous_state.value, "new_state": edge.state.value, "previous_weight": previous_weight, "new_weight": edge.weight, "reason": reason, "evidence_ids": list(evidence_ids), "evaluation_id": str(uuid.uuid4())})
        return edge

    def merge_nodes(self, canonical_atom_id: str, merged_atom_ids: Iterable[str], reason: str = "identity_reconciled") -> Dict[str, str]:
        aliases = {atom_id: canonical_atom_id for atom_id in merged_atom_ids if atom_id != canonical_atom_id}
        self._node_aliases.update(aliases)
        self.vault.record_skg_event("skg.node_merged", {"canonical_atom_id": canonical_atom_id, "aliases": aliases, "reason": reason})
        return aliases

    def relevance_weight(self, atom_id: str) -> float:
        edges = self.edges_for(atom_id)
        return sum(edge.weight for edge in edges) / len(edges) if edges else 0.5

    def update_edges_from_outcome(self, useful_atom_ids: Iterable[str], harmful_atom_ids: Iterable[str], evidence_ids: Iterable[str]) -> List[Edge]:
        updated = []
        useful, harmful = set(useful_atom_ids), set(harmful_atom_ids)
        for edge in list(self.active_edges()):
            related = {self.resolve_node(edge.source_id), self.resolve_node(edge.target_id)}
            if related & useful: updated.append(self.strengthen_edge(edge.edge_id, evidence_ids=evidence_ids))
            if related & harmful: updated.append(self.weaken_edge(edge.edge_id, evidence_ids=evidence_ids))
        return updated

    def _graph_evaluator(self, atom: VaultAtom, others: List[VaultAtom]) -> Tuple[str, float]:
        support, contradiction = 0.0, 0.0
        for edge in self.edges_for(atom.atom_id):
            other_id = edge.target_id if edge.source_id == atom.atom_id else edge.source_id
            other = self.vault.get(self.resolve_node(other_id))
            if not other or other.status != AtomStatus.ACTIVE: continue
            if edge.relation == Relation.SUPPORTS: support += edge.weight * other.confidence
            elif edge.relation == Relation.CONTRADICTS: contradiction += edge.weight * other.confidence
        net = support - contradiction
        return ("reinforce", min(0.2, net * 0.1)) if net > 0.05 else ("challenge", min(0.2, -net * 0.1)) if net < -0.05 else ("hold", 0.0)

    def recursive_self_evaluate(self, max_passes: int = 3, evaluator_fn=None) -> Dict[str, Any]:
        fn = evaluator_fn or self._graph_evaluator
        summary = {"passes_run": 0, "reinforced": 0, "challenged": 0, "retired": 0}
        for _ in range(max_passes):
            active_atoms, changed = self.vault.source_of_truth(), False
            for atom in active_atoms:
                outcome, weight = fn(atom, [other for other in active_atoms if other.atom_id != atom.atom_id])
                if outcome == "reinforce" and weight > 0: self.vault.reinforce(atom.atom_id, weight); summary["reinforced"] += 1; changed = True
                elif outcome == "challenge" and weight > 0: self.vault.challenge(atom.atom_id, weight); summary["challenged"] += 1; changed = True
            summary["passes_run"] += 1
            if not changed: break
        return summary

    def prune_and_improve(self) -> Dict[str, Any]:
        retired = []
        for atom in self.vault.all_atoms():
            if atom.vault_type == VaultType.A_POSTERIORI and atom.status != AtomStatus.RETIRED and atom.confidence < A_POSTERIORI_PRUNE_FLOOR:
                if self.vault.retire(atom.atom_id): retired.append(atom.atom_id)
        return {"retired": retired}

    def source_of_truth(self, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        return [{**atom.to_dict(), "supports": [neighbor.atom_id for neighbor in self.neighbors(atom.atom_id, Relation.SUPPORTS)], "contradicts": [neighbor.atom_id for neighbor in self.neighbors(atom.atom_id, Relation.CONTRADICTS)], "derived_from_atoms": [neighbor.atom_id for neighbor in self.neighbors(atom.atom_id, Relation.DERIVED_FROM)]} for atom in self.vault.source_of_truth(min_confidence)]

    def stats(self) -> Dict[str, Any]:
        by_relation: Dict[str, int] = {}; by_state: Dict[str, int] = {}
        for edge in self._edges.values():
            by_relation[edge.relation.value] = by_relation.get(edge.relation.value, 0) + 1
            by_state[edge.state.value] = by_state.get(edge.state.value, 0) + 1
        return {"total_edges": len(self._edges), "active_edges": len(self.active_edges()), "by_relation": by_relation, "by_state": by_state, "merged_node_aliases": len(self._node_aliases), **self.vault.stats()}
