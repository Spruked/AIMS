"""
skg.py
SKG — Self-Knowledge Graph.

The vault (vault.py) stores atoms and their individual confidence
mechanics. The SKG sits one layer above it and stores the *relations*
between atoms — derivation, support, contradiction — and uses graph
topology (not just per-atom history) to drive recursive self-evaluation.

This is the actual "source of truth" surface the rest of a host system
should query. It never stores raw event content (that is LongTermMemory's
job) and never invents confidence mechanics of its own (that is the
Vault's job) — it composes the two: which atoms currently cohere with
each other, which contradict, and what a recursive walk of that
structure implies for each atom's standing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .vault import Vault, VaultAtom, AtomStatus


class Relation(Enum):
    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


@dataclass
class Edge:
    source_id: str
    target_id: str
    relation: Relation
    weight: float = 1.0


class SelfKnowledgeGraph:
    def __init__(self, vault: Vault):
        self.vault = vault
        self._edges: List[Edge] = []

    # ---------- graph construction ----------

    def link(self, source_id: str, target_id: str, relation: Relation, weight: float = 1.0) -> Edge:
        edge = Edge(source_id=source_id, target_id=target_id, relation=relation, weight=weight)
        self._edges.append(edge)
        return edge

    def edges_for(self, atom_id: str) -> List[Edge]:
        return [e for e in self._edges if e.source_id == atom_id or e.target_id == atom_id]

    def neighbors(self, atom_id: str, relation: Optional[Relation] = None) -> List[VaultAtom]:
        out = []
        for e in self._edges:
            if relation and e.relation != relation:
                continue
            other_id = None
            if e.source_id == atom_id:
                other_id = e.target_id
            elif e.target_id == atom_id:
                other_id = e.source_id
            if other_id:
                atom = self.vault.get(other_id)
                if atom:
                    out.append(atom)
        return out

    # ---------- topology-driven recursive self-evaluation ----------

    def _graph_evaluator(self, atom: VaultAtom, others: List[VaultAtom]) -> Tuple[str, float]:
        """Default evaluator: look at what this atom's own graph edges
        say about it, weighted by the current confidence of whatever is
        on the other end. An atom heavily contradicted by high-confidence
        neighbors gets challenged; one heavily supported gets reinforced;
        otherwise it holds. `others` (all currently-active atoms) is
        accepted for signature symmetry with Vault.recursive_self_evaluate
        and for evaluator variants that want cross-atom context beyond
        direct edges.
        """
        support_weight = 0.0
        contradict_weight = 0.0
        for edge in self.edges_for(atom.atom_id):
            other_id = edge.target_id if edge.source_id == atom.atom_id else edge.source_id
            other = self.vault.get(other_id)
            if not other or other.status != AtomStatus.ACTIVE:
                continue
            if edge.relation == Relation.SUPPORTS:
                support_weight += edge.weight * other.confidence
            elif edge.relation == Relation.CONTRADICTS:
                contradict_weight += edge.weight * other.confidence

        net = support_weight - contradict_weight
        if net > 0.05:
            return "reinforce", min(0.2, net * 0.1)
        if net < -0.05:
            return "challenge", min(0.2, -net * 0.1)
        return "hold", 0.0

    def recursive_self_evaluate(self, max_passes: int = 3, evaluator_fn=None) -> Dict[str, Any]:
        """Run the vault's recursive self-evaluation using graph topology
        as the judge, unless a caller-supplied evaluator_fn is given
        (e.g. one that also consults LongTermMemory content or an
        external model). This is the mechanism by which prior memory
        gets recursively re-scored for improved future return: every
        newly admitted atom can retroactively change the standing of
        atoms already believed, purely by how it links into the graph.
        """
        fn = evaluator_fn or self._graph_evaluator
        return self.vault.recursive_self_evaluate(fn, max_passes=max_passes)

    def prune_and_improve(self) -> Dict[str, Any]:
        pruned = self.vault.self_prune()
        improved = self.vault.self_improve()
        return {"pruned": pruned, "improved": improved}

    # ---------- source of truth surface ----------

    def source_of_truth(self, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        atoms = self.vault.source_of_truth(min_confidence=min_confidence)
        out = []
        for atom in atoms:
            out.append(
                {
                    **atom.to_dict(),
                    "supports": [a.atom_id for a in self.neighbors(atom.atom_id, Relation.SUPPORTS)],
                    "contradicts": [a.atom_id for a in self.neighbors(atom.atom_id, Relation.CONTRADICTS)],
                    "derived_from_atoms": [a.atom_id for a in self.neighbors(atom.atom_id, Relation.DERIVED_FROM)],
                }
            )
        return out

    def stats(self) -> Dict[str, Any]:
        by_relation: Dict[str, int] = {}
        for e in self._edges:
            by_relation[e.relation.value] = by_relation.get(e.relation.value, 0) + 1
        return {"total_edges": len(self._edges), "by_relation": by_relation, **self.vault.stats()}
