import importlib.util
import tempfile
import unittest
from pathlib import Path

from memory_core import AIMSMemorySystem, Relation
from memory_core.skg import Edge, GraphQLiteSKGBackend, graphqlite_backend_factory


@unittest.skipUnless(importlib.util.find_spec("graphqlite"), "optional GraphQLite backend not installed")
class GraphQLiteBackendTests(unittest.TestCase):
    def test_mirrors_derived_edges_and_queries_them(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = GraphQLiteSKGBackend(str(Path(directory) / "derived.graphqlite"))
            backend.clear_derived_state()
            edge = Edge(source_id="first", target_id="second", relation=Relation.SUPPORTS)
            backend.upsert_edge(edge)
            self.assertEqual(backend.edge(edge.edge_id).edge_id, edge.edge_id)
            rows = backend.query(
                "MATCH (a:VaultAtom)-[:SUPPORTS]->(b:VaultAtom) "
                "RETURN a.atom_id, b.atom_id"
            )
            self.assertEqual(rows, [{"a.atom_id": "first", "b.atom_id": "second"}])
            backend.close()

    def test_full_trio_replays_from_vault(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            factory = graphqlite_backend_factory(root / "graphs")
            memory = AIMSMemorySystem(root / "aims", matrix_id="accelerated", skg_backend_factory=factory)
            first = memory.assert_apriori("first")
            second = memory.assert_apriori("second")
            edge = memory.link(first.atom_id, second.atom_id, Relation.SUPPORTS)
            memory.close()

            reopened = AIMSMemorySystem(root / "aims", matrix_id="accelerated", skg_backend_factory=factory)
            self.assertEqual(reopened.skg_trio.prior.edge(edge.edge_id).relation, Relation.SUPPORTS)
            reopened.close()


if __name__ == "__main__":
    unittest.main()
