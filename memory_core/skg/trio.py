"""Coordinator and compatibility facade for the three A.I.M.S. SKGs."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional

from ..vault import Vault, VaultAtom, VaultType
from .backend import SKGBackend
from .domain import APrioriSKG, APosterioriSKG, CollectiveSKG, DomainSKG
from .types import Edge, Relation


class SKGTrio:
    def __init__(self, vault: Vault, backend_factory: Optional[Callable[[str], SKGBackend]] = None):
        self.vault = vault
        factory = backend_factory or (lambda _domain: None)
        self.prior = APrioriSKG(vault, backend=factory("a_priori"))
        self.posterior = APosterioriSKG(vault, backend=factory("a_posteriori"))
        self.collective = CollectiveSKG(vault, backend=factory("collective"))

    def _atom(self, atom_id: str) -> VaultAtom:
        atom = self.vault.get(atom_id)
        if atom is None:
            raise ValueError("SKG endpoints must be Vault atoms")
        return atom

    def route(self, source_id: str, target_id: str) -> DomainSKG:
        source, target = self._atom(source_id), self._atom(target_id)
        if source.vault_type is VaultType.A_PRIORI and target.vault_type is VaultType.A_PRIORI:
            return self.prior
        if source.vault_type is VaultType.A_POSTERIORI and target.vault_type is VaultType.A_POSTERIORI:
            return self.posterior
        return self.collective

    def link(self, source_id: str, target_id: str, relation: Relation, weight: float = 1.0) -> Edge:
        return self.route(source_id, target_id).link(source_id, target_id, relation, weight)

    def graph_for_edge(self, edge_id: str) -> DomainSKG:
        for graph in (self.prior, self.posterior, self.collective):
            if graph.edge(edge_id) is not None:
                return graph
        raise KeyError(edge_id)

    def edge(self, edge_id: str) -> Optional[Edge]:
        try:
            return self.graph_for_edge(edge_id).edge(edge_id)
        except KeyError:
            return None

    def all_edges(self) -> List[Edge]:
        return [*self.prior.all_edges(), *self.posterior.all_edges(), *self.collective.all_edges()]

    def active_edges(self) -> List[Edge]:
        return [*self.prior.active_edges(), *self.posterior.active_edges(), *self.collective.active_edges()]

    def resolve_node(self, atom_id: str) -> str:
        atom = self._atom(atom_id)
        graph = self.prior if atom.vault_type is VaultType.A_PRIORI else self.posterior
        return graph.resolve_node(atom_id)

    def relevance_weight(self, atom_id: str) -> float:
        atom = self._atom(atom_id)
        graph = self.prior if atom.vault_type is VaultType.A_PRIORI else self.posterior
        return round(0.6 * graph.relevance_weight(atom_id) + 0.4 * self.collective.relevance_weight(atom_id), 4)

    def strengthen_edge(self, edge_id: str, *args, **kwargs) -> Edge:
        return self.graph_for_edge(edge_id).strengthen_edge(edge_id, *args, **kwargs)

    def weaken_edge(self, edge_id: str, *args, **kwargs) -> Edge:
        return self.graph_for_edge(edge_id).weaken_edge(edge_id, *args, **kwargs)

    def retire_edge(self, edge_id: str, *args, **kwargs) -> Edge:
        return self.graph_for_edge(edge_id).retire_edge(edge_id, *args, **kwargs)

    def prune_edge(self, edge_id: str, *args, **kwargs) -> Edge:
        return self.graph_for_edge(edge_id).prune_edge(edge_id, *args, **kwargs)

    def update_edges_from_outcome(self, useful_atom_ids: Iterable[str], harmful_atom_ids: Iterable[str], evidence_ids: Iterable[str]) -> List[Edge]:
        return self.posterior.update_edges_from_outcome(useful_atom_ids, harmful_atom_ids, evidence_ids)

    def merge_nodes(self, canonical_atom_id: str, merged_atom_ids: Iterable[str], reason: str = "identity_reconciled") -> Dict[str, str]:
        graph = self.route(canonical_atom_id, canonical_atom_id)
        for atom_id in merged_atom_ids:
            if self.route(canonical_atom_id, atom_id) is not graph:
                raise ValueError("Node aliases may only merge atoms from the same epistemic domain")
        return graph.merge_nodes(canonical_atom_id, merged_atom_ids, reason)

    def rebuild_from_vault(self) -> None:
        self.prior.rebuild_from_vault()
        self.posterior.rebuild_from_vault()
        self.collective.rebuild_from_vault()

    def close(self) -> None:
        """Release optional backend resources without affecting Vault evidence."""
        for graph in (self.prior, self.posterior, self.collective):
            close = getattr(graph.backend, "close", None)
            if close:
                close()

    def recursive_self_evaluate(self, max_passes: int = 3) -> Dict[str, int]:
        maintenance = self.posterior.prune_and_improve()
        return {"passes_run": 1, "reinforced": 0, "challenged": 0, **maintenance}

    def source_of_truth(self, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        results = []
        for atom in self.vault.source_of_truth(min_confidence):
            graph = self.prior if atom.vault_type is VaultType.A_PRIORI else self.posterior
            results.append({
                **atom.to_dict(),
                "supports": [neighbor.atom_id for neighbor in graph.neighbors(atom.atom_id, Relation.SUPPORTS)],
                "contradicts": [neighbor.atom_id for neighbor in graph.neighbors(atom.atom_id, Relation.CONTRADICTS)],
                "collective_relationships": [edge.to_dict() for edge in self.collective.edges_for(atom.atom_id)],
            })
        return results

    def stats(self) -> Dict[str, Any]:
        return {
            "prior": self.prior.stats(),
            "posterior": self.posterior.stats(),
            "collective": self.collective.stats(),
            "total_edges": len(self.all_edges()),
            "active_edges": len(self.active_edges()),
        }


# Compatibility name for hosts written against the v0.2 single-SKG surface.
SelfKnowledgeGraph = SKGTrio
