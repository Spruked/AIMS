import tempfile
import unittest
from pathlib import Path

from memory_core import AIMSMemorySystem, EntryType, Relation
from memory_core.skg import EdgeState


class ThreeSKGTests(unittest.TestCase):
    def test_domain_routing_replay_and_collective_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = AIMSMemorySystem(Path(directory), matrix_id="three_skg")
            prior_a = memory.assert_apriori("Use the verified policy")
            prior_b = memory.assert_apriori("The policy is authoritative")
            source = memory.commit(EntryType.OBSERVATION, {"observation": "policy exception occurred"})
            posterior_a = memory.derive_aposteriori("An exception occurred", [source], initial_confidence=0.8)
            posterior_b = memory.derive_aposteriori("Exception evidence is reproducible", [source], initial_confidence=0.8)

            prior_edge = memory.link(prior_a.atom_id, prior_b.atom_id, Relation.SUPPORTS)
            posterior_edge = memory.link(posterior_a.atom_id, posterior_b.atom_id, Relation.CORROBORATES)
            collective_edge = memory.link(prior_a.atom_id, posterior_a.atom_id, Relation.CONTRADICTS)

            self.assertEqual(memory.skg_trio.prior.edge(prior_edge.edge_id).relation, Relation.SUPPORTS)
            self.assertEqual(memory.skg_trio.posterior.edge(posterior_edge.edge_id).relation, Relation.CORROBORATES)
            self.assertEqual(memory.skg_trio.collective.edge(collective_edge.edge_id).relation, Relation.CONTRADICTS)
            self.assertEqual(memory.skg_trio.prior.stats()["total_edges"], 1)
            self.assertEqual(memory.skg_trio.posterior.stats()["total_edges"], 1)
            self.assertEqual(memory.skg_trio.collective.stats()["total_edges"], 1)

            with self.assertRaises(ValueError):
                memory.skg_trio.prior.link(prior_a.atom_id, posterior_a.atom_id, Relation.SUPPORTS)
            with self.assertRaises(ValueError):
                memory.link(posterior_a.atom_id, source.entry_id, Relation.DERIVED_FROM)

            memory.skg_trio.collective.weaken_edge(collective_edge.edge_id, amount=0.97, evidence_ids=[source.entry_id])
            self.assertEqual(memory.skg_trio.collective.edge(collective_edge.edge_id).state, EdgeState.PRUNED)

            reopened = AIMSMemorySystem(Path(directory), matrix_id="three_skg")
            self.assertEqual(reopened.skg_trio.prior.edge(prior_edge.edge_id).relation, Relation.SUPPORTS)
            self.assertEqual(reopened.skg_trio.posterior.edge(posterior_edge.edge_id).relation, Relation.CORROBORATES)
            self.assertEqual(reopened.skg_trio.collective.edge(collective_edge.edge_id).state, EdgeState.PRUNED)
            domains = [event.get("skg_domain") for event in reopened.vault.skg_events() if "edge" in event]
            self.assertEqual(set(domains), {"a_priori", "a_posteriori", "collective"})

    def test_graph_mutation_follows_vault_event(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = AIMSMemorySystem(Path(directory), matrix_id="event_first")
            first = memory.assert_apriori("first")
            second = memory.assert_apriori("second")
            graph = memory.skg_trio.prior
            before = graph.stats()["total_edges"]
            original = memory.vault.record_skg_event

            def fail(*args, **kwargs):
                raise OSError("simulated vault failure")

            memory.vault.record_skg_event = fail
            try:
                with self.assertRaises(OSError):
                    graph.link(first.atom_id, second.atom_id, Relation.SUPPORTS)
            finally:
                memory.vault.record_skg_event = original
            self.assertEqual(graph.stats()["total_edges"], before)


if __name__ == "__main__":
    unittest.main()
