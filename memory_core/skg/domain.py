"""Three domain-isolated SKGs derived from immutable Vault evidence."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable, List, Optional

from ..temporal import TriTimestamp
from ..vault import A_POSTERIORI_PRUNE_FLOOR, AtomStatus, Vault, VaultAtom, VaultType
from .backend import PythonSKGBackend, SKGBackend
from .types import Edge, EdgeState, Relation, state_for_weight, transition_event


class DomainSKG:
    """A logical SKG domain with event-first derived-state mutations."""

    name = ""

    def __init__(self, vault: Vault, backend: Optional[SKGBackend] = None):
        self.vault = vault
        self.backend = backend or PythonSKGBackend()
        self.rebuild_from_vault()

    def owns(self, source_id: str, target_id: str) -> bool:
        raise NotImplementedError

    def _require_owned(self, source_id: str, target_id: str) -> None:
        if not self.owns(source_id, target_id):
            raise ValueError(f"{self.name} does not own this relationship")

    def _persist(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.vault.record_skg_event(event, {"skg_domain": self.name, **payload})

    def link(self, source_id: str, target_id: str, relation: Relation, weight: float = 1.0) -> Edge:
        self._require_owned(source_id, target_id)
        edge = Edge(source_id=source_id, target_id=target_id, relation=relation, weight=max(0.0, min(1.0, weight)))
        # Authority event first. If it fails, the backend remains unchanged.
        self._persist("skg.edge_created", {"edge": edge.to_dict(), "reason": "relationship_declared"})
        self.backend.upsert_edge(edge)
        return edge

    def edge(self, edge_id: str) -> Optional[Edge]:
        return self.backend.edge(edge_id)

    def all_edges(self) -> List[Edge]:
        return self.backend.all_edges()

    def active_edges(self) -> List[Edge]:
        return [edge for edge in self.all_edges() if edge.state not in {EdgeState.RETIRED, EdgeState.PRUNED}]

    def resolve_node(self, atom_id: str) -> str:
        return self.backend.resolve(atom_id)

    def edges_for(self, atom_id: str, relation: Optional[Relation] = None, include_inactive: bool = False) -> List[Edge]:
        atom_id = self.resolve_node(atom_id)
        source = self.all_edges() if include_inactive else self.active_edges()
        return [
            edge for edge in source
            if (relation is None or edge.relation is relation)
            and (self.resolve_node(edge.source_id) == atom_id or self.resolve_node(edge.target_id) == atom_id)
        ]

    def neighbors(self, atom_id: str, relation: Optional[Relation] = None) -> List[VaultAtom]:
        resolved = self.resolve_node(atom_id)
        neighbors = []
        for edge in self.edges_for(resolved, relation):
            other = edge.target_id if self.resolve_node(edge.source_id) == resolved else edge.source_id
            atom = self.vault.get(self.resolve_node(other))
            if atom:
                neighbors.append(atom)
        return neighbors

    def relevance_weight(self, atom_id: str) -> float:
        edges = self.edges_for(atom_id)
        return sum(edge.weight for edge in edges) / len(edges) if edges else 0.5

    def _transition(self, edge_id: str, reason: str, evidence_ids: Iterable[str], operation: str, amount: float = 0.0) -> Edge:
        previous = self.edge(edge_id)
        if previous is None:
            raise KeyError(edge_id)
        candidate = previous.copy()
        if operation == "strengthen":
            candidate.weight = min(1.0, candidate.weight + amount)
            candidate.confidence = min(1.0, candidate.confidence + amount / 2)
            candidate.reinforcement_count += 1
            candidate.last_reinforced_at = TriTimestamp.now()
            candidate.supporting_evidence = list(dict.fromkeys([*candidate.supporting_evidence, *evidence_ids]))
            candidate.state = state_for_weight(candidate.weight)
        elif operation == "weaken":
            candidate.weight = max(0.0, candidate.weight - amount)
            candidate.confidence = max(0.0, candidate.confidence - amount / 2)
            candidate.challenge_count += 1
            candidate.last_challenged_at = TriTimestamp.now()
            candidate.contradicting_evidence = list(dict.fromkeys([*candidate.contradicting_evidence, *evidence_ids]))
            candidate.state = state_for_weight(candidate.weight)
        elif operation == "retire":
            candidate.state = EdgeState.RETIRED
        elif operation == "prune":
            candidate.state = EdgeState.PRUNED
        else:
            raise ValueError(f"Unknown graph operation: {operation}")
        event = transition_event(previous.state, candidate.state, previous.weight, candidate.weight)
        self._persist(event, {
            "edge": candidate.to_dict(),
            "previous_state": previous.state.value,
            "new_state": candidate.state.value,
            "previous_weight": previous.weight,
            "new_weight": candidate.weight,
            "reason": reason,
            "evidence_ids": list(evidence_ids),
            "evaluation_id": str(uuid.uuid4()),
        })
        self.backend.upsert_edge(candidate)
        return candidate

    def strengthen_edge(self, edge_id: str, amount: float = 0.1, evidence_ids: Iterable[str] = (), reason: str = "supporting_outcome") -> Edge:
        return self._transition(edge_id, reason, evidence_ids, "strengthen", amount)

    def weaken_edge(self, edge_id: str, amount: float = 0.1, evidence_ids: Iterable[str] = (), reason: str = "contradicting_outcome") -> Edge:
        return self._transition(edge_id, reason, evidence_ids, "weaken", amount)

    def retire_edge(self, edge_id: str, reason: str = "explicit_retirement", evidence_ids: Iterable[str] = ()) -> Edge:
        return self._transition(edge_id, reason, evidence_ids, "retire")

    def prune_edge(self, edge_id: str, reason: str = "cognitive_weight_pruned", evidence_ids: Iterable[str] = ()) -> Edge:
        return self._transition(edge_id, reason, evidence_ids, "prune")

    def merge_nodes(self, canonical_atom_id: str, merged_atom_ids: Iterable[str], reason: str = "identity_reconciled") -> Dict[str, str]:
        aliases = {atom_id: canonical_atom_id for atom_id in merged_atom_ids if atom_id != canonical_atom_id}
        if not aliases:
            return {}
        for atom_id in [canonical_atom_id, *aliases]:
            if self.vault.get(atom_id) is None:
                raise ValueError("Merged nodes must exist in the Vault")
        self._persist("skg.node_merged", {"canonical_atom_id": canonical_atom_id, "aliases": aliases, "reason": reason})
        self.backend.merge_aliases(aliases)
        return aliases

    def rebuild_from_vault(self) -> None:
        self.backend.clear_derived_state()
        for event in self.vault.skg_events():
            try:
                event_domain = event.get("skg_domain")
                if event_domain not in {None, self.name}:
                    continue
                if "edge" in event:
                    edge = Edge.from_dict(event["edge"])
                    if self.owns(edge.source_id, edge.target_id):
                        self.backend.upsert_edge(edge)
                elif event.get("event") == "skg.node_merged":
                    aliases = event.get("aliases", {})
                    canonical = event.get("canonical_atom_id")
                    if canonical and all(self.owns(canonical, alias) for alias in aliases):
                        self.backend.merge_aliases(aliases)
            except (KeyError, TypeError, ValueError):
                # Derived state must remain recoverable even when a foreign or
                # malformed historical event cannot be interpreted.
                continue

    def stats(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = {}
        by_relation: Dict[str, int] = {}
        for edge in self.all_edges():
            by_state[edge.state.value] = by_state.get(edge.state.value, 0) + 1
            by_relation[edge.relation.value] = by_relation.get(edge.relation.value, 0) + 1
        return {
            "skg": self.name,
            "total_edges": len(self.all_edges()),
            "active_edges": len(self.active_edges()),
            "by_state": by_state,
            "by_relation": by_relation,
            "state_digest": self.backend.state_digest(),
        }


class APrioriSKG(DomainSKG):
    name = "a_priori"

    def owns(self, source_id: str, target_id: str) -> bool:
        source, target = self.vault.get(source_id), self.vault.get(target_id)
        return bool(source and target and source.vault_type is VaultType.A_PRIORI and target.vault_type is VaultType.A_PRIORI)


class APosterioriSKG(DomainSKG):
    name = "a_posteriori"

    def owns(self, source_id: str, target_id: str) -> bool:
        source, target = self.vault.get(source_id), self.vault.get(target_id)
        return bool(source and target and source.vault_type is VaultType.A_POSTERIORI and target.vault_type is VaultType.A_POSTERIORI)

    def update_edges_from_outcome(self, useful_atom_ids: Iterable[str], harmful_atom_ids: Iterable[str], evidence_ids: Iterable[str]) -> List[Edge]:
        useful, harmful = set(useful_atom_ids), set(harmful_atom_ids)
        updated = []
        for edge in self.active_edges():
            related = {self.resolve_node(edge.source_id), self.resolve_node(edge.target_id)}
            if related & useful:
                updated.append(self.strengthen_edge(edge.edge_id, evidence_ids=evidence_ids))
            if related & harmful:
                updated.append(self.weaken_edge(edge.edge_id, evidence_ids=evidence_ids))
        return updated

    def prune_and_improve(self) -> Dict[str, List[str]]:
        retired_atoms, pruned_edges = [], []
        for atom in self.vault.all_atoms():
            if atom.vault_type is VaultType.A_POSTERIORI and atom.status is not AtomStatus.RETIRED and atom.confidence < A_POSTERIORI_PRUNE_FLOOR:
                if self.vault.retire(atom.atom_id):
                    retired_atoms.append(atom.atom_id)
                    for edge in self.edges_for(atom.atom_id, include_inactive=True):
                        if edge.state not in {EdgeState.RETIRED, EdgeState.PRUNED}:
                            self.prune_edge(edge.edge_id, reason="atom_retired_below_floor", evidence_ids=[atom.atom_id])
                            pruned_edges.append(edge.edge_id)
        return {"retired_atoms": retired_atoms, "pruned_edges": pruned_edges}


class CollectiveSKG(DomainSKG):
    name = "collective"

    def owns(self, source_id: str, target_id: str) -> bool:
        source, target = self.vault.get(source_id), self.vault.get(target_id)
        return bool(source and target and source.vault_type is not target.vault_type)

    def detect_contradiction(self, first_atom_id: str, second_atom_id: str, evidence_ids: Iterable[str] = ()) -> Edge:
        self._require_owned(first_atom_id, second_atom_id)
        source = self.vault.get(first_atom_id)
        target = self.vault.get(second_atom_id)
        edge = self.link(first_atom_id, second_atom_id, Relation.CONTRADICTS, weight=min(1.0, max(source.confidence, target.confidence)))
        if evidence_ids:
            return self.weaken_edge(edge.edge_id, amount=0.0, evidence_ids=evidence_ids, reason="cross_domain_contradiction")
        return edge
