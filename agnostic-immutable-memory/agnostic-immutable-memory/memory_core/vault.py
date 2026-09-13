"""
vault.py
A Priori / A Posteriori Vault Memory.

Two partitions of judged (not merely recorded) memory:

    A PRIORI  - foundational atoms asserted by design, not derived from
                any single observed entry. Axioms, invariants, declared
                identity/constraints. High confidence floor; cannot be
                pruned below that floor no matter how much contradicting
                evidence accumulates (a system should have to be
                re-designed, not statistically out-voted, to change its
                axioms). Can still be reinforced further.

    A POSTERIORI - atoms derived from observed entries (long-term memory
                writes, promoted short-term items, or other atoms).
                Start on probation at moderate confidence. Confidence
                moves up with reinforcement (repeated, corroborating
                re-challenge) and down with contradiction. Subject to
                self-pruning if confidence collapses.

Neither partition stores raw event content — that stays in
LongTermMemory. A vault atom is a *claim distilled from* one or more
entries (or other atoms), plus a lineage back to what it was distilled
from. This is what lets the layer above (the SKG) treat the vault as
the running "source of truth" without re-deriving it from scratch on
every query, while still being able to walk back to primary evidence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .temporal import TriTimestamp


class VaultType(Enum):
    A_PRIORI = "a_priori"
    A_POSTERIORI = "a_posteriori"


class AtomStatus(Enum):
    PROBATION = "probation"   # newly admitted a posteriori atom, unproven
    ACTIVE = "active"          # trusted, counted as source of truth
    PRUNED = "pruned"          # confidence collapsed; retained for audit, excluded from truth


@dataclass
class VaultAtom:
    atom_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vault_type: VaultType = VaultType.A_POSTERIORI
    statement: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    derived_from: List[str] = field(default_factory=list)  # LTM entry_ids and/or atom_ids
    confidence: float = 0.5
    status: AtomStatus = AtomStatus.PROBATION
    support_count: int = 0
    challenge_count: int = 0
    created: TriTimestamp = field(default_factory=TriTimestamp.now)
    last_evaluated: TriTimestamp = field(default_factory=TriTimestamp.now)
    evaluation_passes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "atom_id": self.atom_id,
            "vault_type": self.vault_type.value,
            "statement": self.statement,
            "metadata": self.metadata,
            "derived_from": self.derived_from,
            "confidence": self.confidence,
            "status": self.status.value,
            "support_count": self.support_count,
            "challenge_count": self.challenge_count,
            "created": self.created.to_dict(),
            "last_evaluated": self.last_evaluated.to_dict(),
            "evaluation_passes": self.evaluation_passes,
        }


# A priori confidence can never be pruned below this floor.
A_PRIORI_FLOOR = 0.55
# A posteriori atoms are pruned once confidence drops below this.
A_POSTERIORI_PRUNE_FLOOR = 0.20
# Confidence an a posteriori atom needs to graduate PROBATION -> ACTIVE.
PROMOTION_CONFIDENCE = 0.65
PROMOTION_SUPPORT_COUNT = 3


class Vault:
    def __init__(self):
        self._atoms: Dict[str, VaultAtom] = {}

    # ---------- admission ----------

    def add_apriori(self, statement: str, metadata: Optional[Dict[str, Any]] = None) -> VaultAtom:
        atom = VaultAtom(
            vault_type=VaultType.A_PRIORI,
            statement=statement,
            metadata=metadata or {},
            confidence=1.0,
            status=AtomStatus.ACTIVE,
        )
        self._atoms[atom.atom_id] = atom
        return atom

    def add_aposteriori(
        self,
        statement: str,
        derived_from: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        initial_confidence: float = 0.5,
    ) -> VaultAtom:
        atom = VaultAtom(
            vault_type=VaultType.A_POSTERIORI,
            statement=statement,
            metadata=metadata or {},
            derived_from=list(derived_from),
            confidence=initial_confidence,
            status=AtomStatus.PROBATION,
        )
        self._atoms[atom.atom_id] = atom
        return atom

    # ---------- confidence mechanics ----------

    def reinforce(self, atom_id: str, weight: float = 0.1) -> Optional[VaultAtom]:
        atom = self._atoms.get(atom_id)
        if not atom:
            return None
        atom.confidence = min(1.0, atom.confidence + weight)
        atom.support_count += 1
        atom.last_evaluated = TriTimestamp.now()
        self._maybe_promote(atom)
        return atom

    def challenge(self, atom_id: str, weight: float = 0.1) -> Optional[VaultAtom]:
        atom = self._atoms.get(atom_id)
        if not atom:
            return None
        floor = A_PRIORI_FLOOR if atom.vault_type == VaultType.A_PRIORI else 0.0
        atom.confidence = max(floor, atom.confidence - weight)
        atom.challenge_count += 1
        atom.last_evaluated = TriTimestamp.now()
        return atom

    def _maybe_promote(self, atom: VaultAtom):
        if (
            atom.vault_type == VaultType.A_POSTERIORI
            and atom.status == AtomStatus.PROBATION
            and atom.confidence >= PROMOTION_CONFIDENCE
            and atom.support_count >= PROMOTION_SUPPORT_COUNT
        ):
            atom.status = AtomStatus.ACTIVE

    # ---------- self-pruning ----------

    def self_prune(self, min_confidence: float = A_POSTERIORI_PRUNE_FLOOR) -> List[str]:
        """Demote (never delete — audit trail stays) a posteriori atoms
        whose confidence has collapsed. A priori atoms are structurally
        exempt: they have a hard floor and no prune path.
        """
        pruned_ids = []
        for atom in self._atoms.values():
            if atom.vault_type != VaultType.A_POSTERIORI:
                continue
            if atom.status == AtomStatus.PRUNED:
                continue
            if atom.confidence < min_confidence:
                atom.status = AtomStatus.PRUNED
                pruned_ids.append(atom.atom_id)
        return pruned_ids

    # ---------- self-improvement ----------

    def self_improve(self, sustained_support: int = 5, boost: float = 0.05) -> List[str]:
        """Atoms that keep getting reinforced without being challenged in
        between earn a standing confidence boost — repeated, unrebutted
        corroboration is itself evidence worth compounding, not just
        counting once.
        """
        improved_ids = []
        for atom in self._atoms.values():
            if atom.status != AtomStatus.ACTIVE:
                continue
            if atom.support_count >= sustained_support and atom.challenge_count == 0:
                atom.confidence = min(1.0, atom.confidence + boost)
                improved_ids.append(atom.atom_id)
        return improved_ids

    # ---------- recursive self-evaluation ----------

    def recursive_self_evaluate(
        self,
        evaluator_fn: Callable[[VaultAtom, List[VaultAtom]], Tuple[str, float]],
        max_passes: int = 3,
    ) -> Dict[str, Any]:
        """Re-score prior atoms against each other and against the
        evaluator's judgment, iterating until stable or max_passes.

        evaluator_fn(atom, other_active_atoms) -> (outcome, weight)
            outcome in {"reinforce", "challenge", "hold"}
            weight  in [0, 1]

        This is the mechanism that turns the vault into a system that
        improves its own future returns: every pass can surface a
        previously-active atom as newly contradicted by atoms admitted
        later, or newly corroborated by them, without needing a fresh
        external event to trigger the re-look.
        """
        summary = {"passes_run": 0, "reinforced": 0, "challenged": 0, "pruned": 0, "promoted": 0}

        for _ in range(max_passes):
            active_atoms = [a for a in self._atoms.values() if a.status == AtomStatus.ACTIVE]
            if not active_atoms:
                break

            changed = False
            for atom in list(active_atoms):
                others = [a for a in active_atoms if a.atom_id != atom.atom_id]
                outcome, weight = evaluator_fn(atom, others)
                atom.evaluation_passes += 1
                if outcome == "reinforce" and weight > 0:
                    self.reinforce(atom.atom_id, weight)
                    summary["reinforced"] += 1
                    changed = True
                elif outcome == "challenge" and weight > 0:
                    self.challenge(atom.atom_id, weight)
                    summary["challenged"] += 1
                    changed = True
                # "hold" -> no-op, contributes to stability check

            pruned = self.self_prune()
            summary["pruned"] += len(pruned)
            promoted_before = sum(1 for a in self._atoms.values() if a.status == AtomStatus.ACTIVE)
            self.self_improve()
            promoted_after = sum(1 for a in self._atoms.values() if a.status == AtomStatus.ACTIVE)
            summary["promoted"] += max(0, promoted_after - promoted_before)

            summary["passes_run"] += 1
            if not changed and not pruned:
                break  # stable — no point burning further passes

        return summary

    # ---------- source of truth ----------

    def source_of_truth(self, min_confidence: float = 0.0) -> List[VaultAtom]:
        return [
            a for a in self._atoms.values()
            if a.status == AtomStatus.ACTIVE and a.confidence >= min_confidence
        ]

    def get(self, atom_id: str) -> Optional[VaultAtom]:
        return self._atoms.get(atom_id)

    def all_atoms(self) -> List[VaultAtom]:
        return list(self._atoms.values())

    def stats(self) -> Dict[str, Any]:
        atoms = self.all_atoms()
        by_status: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for a in atoms:
            by_status[a.status.value] = by_status.get(a.status.value, 0) + 1
            by_type[a.vault_type.value] = by_type.get(a.vault_type.value, 0) + 1
        return {"total_atoms": len(atoms), "by_status": by_status, "by_type": by_type}
