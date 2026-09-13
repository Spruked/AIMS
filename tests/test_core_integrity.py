import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path

from memory_core import AIMSMemorySystem, EntryType, IntegrityError, LongTermMemory, TriTimestamp


def _concurrent_write(store_path: str, worker: int):
    ledger = LongTermMemory(Path(store_path), matrix_id="shared", security_mode="visual")
    ledger.write_entry(EntryType.OBSERVATION, {"worker": worker})


class CoreIntegrityTests(unittest.TestCase):
    def authenticated_system(self, root: Path):
        return AIMSMemorySystem(root, matrix_id="aims", glyph_key="key-one", glyph_key_id="k1", security_mode="authenticated")

    def test_vault_replays_authoritative_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = self.authenticated_system(root)
            atom = system.assert_apriori("An immutable assertion")
            reopened = self.authenticated_system(root)
            self.assertEqual(reopened.vault.get(atom.atom_id).statement, atom.statement)
            self.assertTrue(reopened.vault.event_ledger.verify_chain()[0])

    def test_authenticated_downgrade_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = self.authenticated_system(root)
            system.commit(EntryType.OBSERVATION, {"event": "protected"})
            path = root / "aims.ledger"
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[-1]["glyph_mode"] = "visual"
            rows[-1]["glyph_key_id"] = None
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            with self.assertRaises(IntegrityError):
                self.authenticated_system(root)

    def test_missing_keyring_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.authenticated_system(root)
            with self.assertRaises(IntegrityError):
                AIMSMemorySystem(root, matrix_id="aims", security_mode="authenticated")

    def test_rotation_reopens_with_historical_keyring(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = self.authenticated_system(root)
            system.rotate_glyph_key("key-two", "k2")
            system.commit(EntryType.LEARNING, {"event": "rotated"})
            reopened = AIMSMemorySystem(root, matrix_id="aims", glyph_key="key-two", glyph_key_id="k2", glyph_keys={"k1": "key-one", "k2": "key-two"}, security_mode="authenticated")
            self.assertTrue(reopened.long_term.verify_chain()[0])
            self.assertTrue(reopened.vault.event_ledger.verify_chain()[0])

    def test_secret_is_not_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = "never-write-this-secret"
            system = AIMSMemorySystem(root, matrix_id="aims", glyph_key=secret, glyph_key_id="k1", security_mode="authenticated")
            system.commit(EntryType.EXPERIENCE, {"event": "secret check"})
            self.assertNotIn(secret, (root / "aims.ledger").read_text(encoding="utf-8"))
            self.assertNotIn(secret, (root / "vault" / "aims_vault_events.ledger").read_text(encoding="utf-8"))

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = self.authenticated_system(root)
            system.commit(EntryType.EXPERIENCE, {"event": "original"})
            path = root / "aims.ledger"
            rows = path.read_text(encoding="utf-8").splitlines()
            rows[-1] = rows[-1].replace("original", "altered")
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            with self.assertRaises(IntegrityError):
                self.authenticated_system(root)

    def test_cross_process_writer_lock_preserves_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            LongTermMemory(root, matrix_id="shared", security_mode="visual")
            processes = [multiprocessing.Process(target=_concurrent_write, args=(str(root), index)) for index in range(4)]
            for process in processes: process.start()
            for process in processes: process.join(15)
            self.assertTrue(all(process.exitcode == 0 for process in processes))
            ledger = LongTermMemory(root, matrix_id="shared", security_mode="visual")
            self.assertTrue(ledger.verify_chain()[0])
            self.assertEqual(ledger.total_entries, 5)

    def test_tri_timestamp_is_internally_consistent(self):
        self.assertTrue(TriTimestamp.now().verify_internal_consistency())

    def test_indexes_and_retrieval_receipts_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = AIMSMemorySystem(root, matrix_id="retrieve")
            system.assert_apriori("The Vault preserves historical truth")
            receipt = system.retrieve("historical truth")
            self.assertEqual(receipt["result_count"], 1)
            reopened = AIMSMemorySystem(root, matrix_id="retrieve")
            self.assertEqual(reopened.retrieval(receipt["retrieval_id"])["retrieval_set_hash"], receipt["retrieval_set_hash"])
            self.assertEqual(reopened.indexes.status()["counts"]["a_priori"], 1)


if __name__ == "__main__":
    unittest.main()
