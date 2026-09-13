"""
memory_layer.py
CognitiveMemoryLayer — the single import a host system needs.

Wires the three tiers together into one interface:

    write(...)            -> STM (fast, cheap, may be forgotten)
    commit(...)            -> LTM (permanent, hash+glyph+tri-timestamp chained)
    judge(...)             -> Vault (distilled claim, a priori or a posteriori)
    link(...) / truth(...) -> SKG  (relations + the queryable source of truth)
    run_maintenance_cycle() -> sweeps STM, prunes/improves the Vault, and
                                runs a recursive self-evaluation pass over
                                the SKG — this is the "gets better over
                                time on its own" hook a host system should
                                call periodically (e.g. on an idle timer
                                or after N writes).

Nothing in this file assumes an LLM, an agent identity, a mission
system, or any external time/identity authority. Any system with
"things worth remembering, judging, and revisiting" can adopt it by
constructing one CognitiveMemoryLayer against a local directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from .long_term import LongTermMemory, EntryType, ImmutableEntry
from .short_term import ShortTermMemory, STMItem
from .vault import Vault, VaultAtom, VaultType
from .skg import SelfKnowledgeGraph, Relation


class AIMSMemorySystem:
    def __init__(
        self,
        store_path: Path,
        matrix_id: str = "long_term_matrix",
        stm_capacity: int = 500,
        stm_decay_half_life_seconds: float = 900.0,
        glyph_key: Optional[Union[str, bytes]] = None,
        glyph_key_id: Optional[str] = None,
        glyph_keys: Optional[Mapping[str, Union[str, bytes]]] = None,
    ):
        self.store_path = Path(store_path)
        self.long_term = LongTermMemory(
            self.store_path,
            matrix_id=matrix_id,
            glyph_key=glyph_key,
            glyph_key_id=glyph_key_id,
            glyph_keys=glyph_keys,
        )
        self.short_term = ShortTermMemory(
            capacity=stm_capacity, decay_half_life_seconds=stm_decay_half_life_seconds
        )
        self.vault = Vault()
        self.skg = SelfKnowledgeGraph(self.vault)

    # ---------- short-term ingress ----------

    def observe(self, content: Dict[str, Any], tags: Optional[List[str]] = None) -> STMItem:
        """Fast, cheap, possibly-forgotten intake. Use for raw perception
        / candidate facts that haven't earned permanence or judgment yet.
        """
        return self.short_term.put(content, tags=tags)

    def reinforce_observation(self, item_id: str) -> Optional[STMItem]:
        return self.short_term.touch(item_id)

    # ---------- long-term commit ----------

    def commit(
        self,
        entry_type: EntryType,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        writer_id: str = "system",
    ) -> ImmutableEntry:
        """Permanent, hash+glyph+tri-timestamp chained write. Use for
        anything that must never be silently forgotten, whether or not
        it has been judged true yet.
        """
        return self.long_term.write_entry(entry_type, content, metadata=metadata, writer_id=writer_id)

    # ---------- vault admission ----------

    def assert_apriori(self, statement: str, metadata: Optional[Dict[str, Any]] = None) -> VaultAtom:
        """Declare a foundational axiom. Not derived from any entry;
        asserted by design. Immune to pruning below its confidence floor.
        """
        return self.vault.add_apriori(statement, metadata=metadata)

    def derive_aposteriori(
        self,
        statement: str,
        source_entries: List[ImmutableEntry],
        metadata: Optional[Dict[str, Any]] = None,
        initial_confidence: float = 0.5,
    ) -> VaultAtom:
        """Distill a claim from one or more committed long-term entries.
        Starts on probation; earns ACTIVE status (and counts toward
        source_of_truth()) only through reinforcement over time.
        """
        atom = self.vault.add_aposteriori(
            statement,
            derived_from=[e.entry_id for e in source_entries],
            metadata=metadata,
            initial_confidence=initial_confidence,
        )
        for e in source_entries:
            self.skg.link(atom.atom_id, e.entry_id, Relation.DERIVED_FROM)
        return atom

    def promote_from_short_term(
        self,
        item: STMItem,
        statement: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VaultAtom:
        """Take an STM candidate (see ShortTermMemory.promotion_candidates)
        and give it a permanent home: commit it to long-term memory, then
        distill it into an a posteriori vault atom in one step.
        """
        entry = self.commit(
            EntryType.OBSERVATION,
            content=item.content,
            metadata={**(metadata or {}), "promoted_from_stm": item.item_id, "tags": item.tags},
        )
        return self.derive_aposteriori(statement, [entry], metadata=metadata)

    # ---------- relations ----------

    def link(self, source_atom_id: str, target_atom_id: str, relation: Relation, weight: float = 1.0):
        return self.skg.link(source_atom_id, target_atom_id, relation, weight=weight)

    # ---------- query surface ----------

    def truth(self, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """The current source of truth: active, sufficiently-confident
        vault atoms, with their support/contradiction/derivation edges.
        This is what the rest of a host system should consult when it
        needs to know 'what does this system currently believe.'
        """
        return self.skg.source_of_truth(min_confidence=min_confidence)

    def trace(self, atom_id: str) -> Dict[str, Any]:
        """Walk an atom back to the primary long-term entries it was
        derived from, for audit / explainability.
        """
        atom = self.vault.get(atom_id)
        if not atom:
            return {}
        entries = [
            self.long_term.read_entry(entry_id=eid).to_dict()
            for eid in atom.derived_from
            if self.long_term.read_entry(entry_id=eid)
        ]
        return {"atom": atom.to_dict(), "primary_entries": entries}

    # ---------- maintenance ----------

    def run_maintenance_cycle(self, self_eval_passes: int = 3) -> Dict[str, Any]:
        """The self-tending heartbeat: forget what STM no longer needs,
        prune/improve the vault, and recursively re-evaluate the SKG so
        that newer knowledge can retroactively change older standing.
        Call this periodically (idle timer, after N commits, etc.) —
        nothing about this layer requires it to run on any fixed clock.
        """
        stm_evicted = self.short_term.sweep()
        eval_summary = self.skg.recursive_self_evaluate(max_passes=self_eval_passes)
        return {
            "stm_evicted": stm_evicted,
            "stm_stats": self.short_term.stats(),
            "self_evaluation": eval_summary,
            "vault_stats": self.vault.stats(),
            "ltm_stats": self.long_term.get_statistics(),
        }

    def full_status(self) -> Dict[str, Any]:
        return {
            "long_term": self.long_term.get_statistics(),
            "short_term": self.short_term.stats(),
            "vault": self.vault.stats(),
            "skg": self.skg.stats(),
        }


# Compatibility alias for hosts using the pre-A.I.M.S. class name.
CognitiveMemoryLayer = AIMSMemorySystem
