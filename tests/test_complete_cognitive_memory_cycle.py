import tempfile
import unittest
from pathlib import Path

from memory_core import AIMSMemorySystem, EntryType, Relation
from memory_core.skg import EdgeState


class CompleteCognitiveMemoryCycleTests(unittest.TestCase):
    def test_complete_cognitive_memory_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = AIMSMemorySystem(root, matrix_id="cognitive_cycle")

            prior = memory.assert_apriori("shared memory should be preferred")
            prior_alias = memory.assert_apriori("immutable evidence remains authoritative")
            source = memory.commit(EntryType.OBSERVATION, {"outcome": "shared memory succeeded"})
            learned = memory.derive_aposteriori("shared memory succeeded in practice", [source], initial_confidence=0.70)
            for _ in range(3):
                memory.vault.reinforce(learned.atom_id, 0.01)
            memory.indexes.upsert(learned)
            edge = memory.link(learned.atom_id, prior.atom_id, Relation.SUPPORTS, weight=0.90)

            prior_only = memory.retrieve("shared memory", "PRIOR_ONLY")
            posterior_only = memory.retrieve("shared memory", "POSTERIOR_ONLY")
            collective_before = memory.retrieve("shared memory", "COLLECTIVE")
            self.assertEqual(prior_only["result_count"], 1)
            self.assertEqual(posterior_only["result_count"], 1)
            self.assertEqual(collective_before["result_count"], 2)
            self.assertEqual(memory.retrieval(collective_before["retrieval_id"]), collective_before)

            for index in range(4):
                memory.evaluate_cognitive_outcome(
                    collective_before["retrieval_id"], cognitive_event_id=f"decision-{index}",
                    outcome_id=f"outcome-{index}", useful_atom_ids=[learned.atom_id],
                    harmful_atom_ids=[prior.atom_id], evidence_ids=[source.entry_id],
                )
            collective_after = memory.retrieve("shared memory", "COLLECTIVE")
            self.assertEqual(collective_after["results"][0]["atom_id"], learned.atom_id)

            memory.skg.weaken_edge(edge.edge_id, 0.25, [source.entry_id])
            self.assertEqual(memory.skg.edge(edge.edge_id).state, EdgeState.WEAKENED)
            memory.skg.weaken_edge(edge.edge_id, 0.30, [source.entry_id])
            self.assertEqual(memory.skg.edge(edge.edge_id).state, EdgeState.DORMANT)
            memory.skg.weaken_edge(edge.edge_id, 0.25, [source.entry_id])
            self.assertEqual(memory.skg.edge(edge.edge_id).state, EdgeState.RETIRED)
            memory.skg.prune_edge(edge.edge_id, evidence_ids=[source.entry_id])
            self.assertEqual(memory.skg.edge(edge.edge_id).state, EdgeState.PRUNED)
            self.assertNotIn(edge.edge_id, [item.edge_id for item in memory.skg.active_edges()])

            aliases = memory.merge_skg_nodes(prior.atom_id, [prior_alias.atom_id])
            self.assertEqual(aliases[prior_alias.atom_id], prior.atom_id)

            restarted = AIMSMemorySystem(root, matrix_id="cognitive_cycle")
            replayed = restarted.retrieval(collective_before["retrieval_id"])
            self.assertEqual(replayed, collective_before)
            ranking_after_restart = restarted.retrieve("shared memory", "COLLECTIVE")
            self.assertEqual(ranking_after_restart["results"][0]["atom_id"], learned.atom_id)
            self.assertEqual(restarted.skg.edge(edge.edge_id).state, EdgeState.PRUNED)
            self.assertEqual(restarted.skg.resolve_node(prior_alias.atom_id), prior.atom_id)
            self.assertTrue(all(entry.tri_timestamp.verify_internal_consistency() for entry in restarted.long_term.entries))
            self.assertTrue(all(entry.tri_timestamp.verify_internal_consistency() for entry in restarted.vault.event_ledger.entries))
            vault_event_names = [entry.content["event"] for entry in restarted.vault.event_ledger.entries]
            self.assertIn("vault.cognitive_evaluation", vault_event_names)
            self.assertIn("skg.edge_pruned", vault_event_names)


if __name__ == "__main__":
    unittest.main()
