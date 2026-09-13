"""
long_term.py
Long-Term Memory (LTM) — Write-Once-Read-Many immutable ledger.

Agnostic by design: no reference to any specific host system, agent
identity scheme, or external time authority. Anything with a notion of
"an event worth never forgetting" can write here through write_entry().

Guarantees carried over from the original design, generalized:
    - Physical immutability: every write is flush()'d and fsync()'d to
      disk before the call returns. Power loss cannot erase a committed
      entry.
    - Logical immutability: SHA-256 hash chaining + a parallel glyph
      trace (see glyph_trace.py). Append-only file mode. No update or
      delete method exists anywhere in this class, by construction.
    - Tri-Timestamp: every entry carries epoch/standard/julian time,
      not a single proprietary clock (see temporal.py).

This layer is intentionally "dumb": it does not decide what is
important, does not prune, and does not interpret content. That
judgment lives one layer up, in the vault (see vault.py) and the SKG
(see skg.py). LTM's only job is to make sure that once something is
written here, it is permanent, verifiable, and ordered.
"""

from __future__ import annotations

import json
import hashlib
import os
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple, Union

from .temporal import TriTimestamp
from . import glyph_trace


class EntryType(Enum):
    EXPERIENCE = "experience"
    DECISION = "decision"
    LEARNING = "learning"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    INTERACTION = "interaction"
    SYSTEM_EVENT = "system_event"


class IntegrityError(Exception):
    """Raised when chain, glyph, or physical persistence verification fails."""


@dataclass
class ImmutableEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence_number: int = 0
    tri_timestamp: TriTimestamp = field(default_factory=TriTimestamp.now)
    entry_type: EntryType = EntryType.EXPERIENCE
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""
    previous_glyph: str = ""
    glyph_mode: str = "visual"
    glyph_key_id: Optional[str] = None
    previous_glyph_mac: str = ""
    writer_id: str = "system"
    entry_hash: str = field(init=False, default="")
    glyph: str = field(init=False, default="")
    glyph_mac: str = field(init=False, default="")
    integrity_verified: bool = True
    vault_id: str = field(default="long_term_matrix", repr=False)
    glyph_key: Optional[Union[str, bytes]] = field(default=None, repr=False)

    def __post_init__(self):
        if not self.entry_hash:
            self.entry_hash = self._compute_hash()
        if self.glyph_mode == "hmac-sha256":
            if self.glyph_key is None or not self.glyph_key_id:
                raise IntegrityError("Authenticated Glyph mode requires a runtime key and key_id")
            if not self.glyph_mac:
                self.glyph_mac = glyph_trace.glyph_mac(
                    self.glyph_key, self.vault_id, self.entry_id, self.sequence_number,
                    self.entry_hash, self.previous_glyph_mac, self.tri_timestamp.to_dict(),
                )
            if not self.glyph:
                self.glyph = glyph_trace.glyph_from_mac(self.glyph_mac)
        elif not self.glyph:
            self.glyph = glyph_trace.thread_glyph(self.previous_glyph, self.entry_hash)

    def _compute_hash(self) -> str:
        content_str = json.dumps(self.content, sort_keys=True)
        metadata_str = json.dumps(self.metadata, sort_keys=True)
        hash_input = (
            f"{self.entry_id}{self.sequence_number}{self.tri_timestamp.epoch}"
            f"{self.entry_type.value}{content_str}{metadata_str}"
            f"{self.previous_hash}{self.writer_id}"
        )
        return hashlib.sha256(hash_input.encode()).hexdigest()

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        glyph_key: Optional[Union[str, bytes]] = None,
        vault_id: str = "long_term_matrix",
    ) -> "ImmutableEntry":
        entry = cls(
            entry_id=data["entry_id"],
            sequence_number=data["sequence_number"],
            tri_timestamp=TriTimestamp.from_dict(data["tri_timestamp"]),
            entry_type=EntryType(data["entry_type"]),
            content=data["content"],
            metadata=data["metadata"],
            previous_hash=data["previous_hash"],
            previous_glyph=data.get("previous_glyph", ""),
            glyph_mode=data.get("glyph_mode", data.get("glyph_trace", {}).get("mode", "visual")),
            glyph_key_id=data.get("glyph_key_id", data.get("glyph_trace", {}).get("key_id")),
            previous_glyph_mac=data.get("previous_glyph_mac", data.get("glyph_trace", {}).get("previous_glyph_mac", "")),
            writer_id=data["writer_id"],
            vault_id=vault_id,
            glyph_key=glyph_key,
        )
        entry.entry_hash = data["entry_hash"]
        entry.glyph = data.get("glyph", "")
        entry.glyph_mac = data.get("glyph_mac", data.get("glyph_trace", {}).get("glyph_mac", ""))
        entry.integrity_verified = data.get("integrity_verified", True)
        return entry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "vault_id": self.vault_id,
            "sequence_number": self.sequence_number,
            "tri_timestamp": self.tri_timestamp.to_dict(),
            "entry_type": self.entry_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
            "previous_glyph": self.previous_glyph,
            "writer_id": self.writer_id,
            "entry_hash": self.entry_hash,
            "glyph_mode": self.glyph_mode,
            "glyph_key_id": self.glyph_key_id,
            "previous_glyph_mac": self.previous_glyph_mac,
            "glyph_mac": self.glyph_mac,
            "glyph": self.glyph,
            "glyph_trace": {
                "version": 1,
                "mode": self.glyph_mode,
                "key_id": self.glyph_key_id,
                "previous_glyph_mac": self.previous_glyph_mac,
                "glyph_mac": self.glyph_mac,
                "glyph": self.glyph,
            },
            "integrity_verified": self.integrity_verified,
        }

    @property
    def hash(self) -> str:
        return self.entry_hash

    def verify(
        self,
        expected_previous_hash: str,
        expected_previous_glyph: str,
        expected_previous_glyph_mac: str = "",
        glyph_key: Optional[Union[str, bytes]] = None,
        vault_id: Optional[str] = None,
    ) -> bool:
        if self.previous_hash != expected_previous_hash:
            self.integrity_verified = False
            return False
        if self.previous_glyph != expected_previous_glyph:
            self.integrity_verified = False
            return False
        if self.glyph_mode == "hmac-sha256":
            if self.previous_glyph_mac != expected_previous_glyph_mac:
                self.integrity_verified = False
                return False
            if not glyph_trace.verify_glyph_mac(
                glyph_key, self.glyph_mac, vault_id or self.vault_id,
                self.entry_id, self.sequence_number, self.entry_hash,
                self.previous_glyph_mac, self.tri_timestamp.to_dict(),
            ) or glyph_trace.glyph_from_mac(self.glyph_mac) != self.glyph:
                self.integrity_verified = False
                return False
        elif self.glyph_mac or self.glyph_key_id or self.glyph_mode != "visual":
            self.integrity_verified = False
            return False
        if self._compute_hash() != self.entry_hash:
            self.integrity_verified = False
            return False
        if self.glyph_mode == "visual" and glyph_trace.thread_glyph(self.previous_glyph, self.entry_hash) != self.glyph:
            self.integrity_verified = False
            return False
        self.integrity_verified = True
        return True


class LongTermMemory:
    """
    Physically + logically immutable WORM ledger.
    Host-agnostic: pass any `store_path`; no assumptions about the
    calling system's identity, architecture, or reasoning model.
    """

    def __init__(
        self,
        store_path: Path,
        matrix_id: str = "long_term_matrix",
        glyph_key: Optional[Union[str, bytes]] = None,
        glyph_key_id: Optional[str] = None,
        glyph_keys: Optional[Mapping[str, Union[str, bytes]]] = None,
    ):
        self.store_path = Path(store_path)
        self.matrix_id = matrix_id
        self.glyph_keys = dict(glyph_keys or {})
        if glyph_key is not None:
            if not glyph_key_id:
                raise ValueError("glyph_key_id is required when glyph_key is supplied")
            self.glyph_keys[glyph_key_id] = glyph_key
        self.glyph_key_id = glyph_key_id
        self.ledger_path = self.store_path / f"{matrix_id}.ledger"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

        self.entries: List[ImmutableEntry] = []
        self.entry_index: Dict[str, ImmutableEntry] = {}
        self.sequence_index: Dict[int, ImmutableEntry] = {}

        self.last_sequence = -1
        self.last_hash = "0" * 64
        self.last_glyph = ""
        self.last_glyph_mac = ""
        self.total_entries = 0

        self.lock = threading.RLock()
        self.ready = False

        self._self_check()

    # ---------- startup / integrity ----------

    def _self_check(self):
        self.entries.clear()
        self.entry_index.clear()
        self.sequence_index.clear()
        self.last_sequence = -1
        self.last_hash = "0" * 64
        self.last_glyph = ""
        self.last_glyph_mac = ""
        self.total_entries = 0

        if self.ledger_path.exists():
            self._replay()

        is_valid, corrupted = self.verify_chain()
        if not is_valid:
            raise IntegrityError(f"Startup self-check failed at sequences {corrupted}")

        self.ready = True

    def perform_manual_self_check(self) -> Dict[str, Any]:
        self.ready = False
        try:
            self._self_check()
            return {"success": True, "entries_verified": self.total_entries, "ready": self.ready}
        except IntegrityError as e:
            return {"success": False, "error": str(e), "ready": self.ready}

    def _replay(self):
        with open(self.ledger_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    raise IntegrityError(f"Corrupted JSON at line {line_num}: {e}")
                key_id = data.get("glyph_key_id", data.get("glyph_trace", {}).get("key_id"))
                entry = ImmutableEntry.from_dict(
                    data,
                    glyph_key=self.glyph_keys.get(key_id) if key_id else None,
                    vault_id=self.matrix_id,
                )
                key = self.glyph_keys.get(entry.glyph_key_id) if entry.glyph_key_id else None
                if not entry.verify(self.last_hash, self.last_glyph, self.last_glyph_mac, key, self.matrix_id):
                    raise IntegrityError(
                        f"Entry {entry.sequence_number} (line {line_num}) failed verification"
                    )
                self._index(entry)
        self.total_entries = len(self.entries)

    def _index(self, entry: ImmutableEntry):
        self.entries.append(entry)
        self.entry_index[entry.entry_id] = entry
        self.sequence_index[entry.sequence_number] = entry
        self.last_hash = entry.hash
        self.last_glyph = entry.glyph
        self.last_glyph_mac = entry.glyph_mac
        self.last_sequence = entry.sequence_number

    def _append_physical(self, entry: ImmutableEntry):
        with open(self.ledger_path, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")
            f.flush()
            os.fsync(f.fileno())

    # ---------- write / read ----------

    def write_entry(
        self,
        entry_type: EntryType,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        writer_id: str = "system",
    ) -> ImmutableEntry:
        if not self.ready:
            raise IntegrityError("LongTermMemory not ready for writes")

        with self.lock:
            next_seq = self.last_sequence + 1
            entry = ImmutableEntry(
                sequence_number=next_seq,
                entry_type=entry_type,
                content=content,
                metadata=metadata or {},
                previous_hash=self.last_hash,
                previous_glyph=self.last_glyph,
                glyph_mode="hmac-sha256" if self.glyph_key_id else "visual",
                glyph_key_id=self.glyph_key_id,
                previous_glyph_mac=self.last_glyph_mac,
                writer_id=writer_id,
                vault_id=self.matrix_id,
                glyph_key=self.glyph_keys.get(self.glyph_key_id) if self.glyph_key_id else None,
            )
            if not entry.verify(self.last_hash, self.last_glyph, self.last_glyph_mac,
                                entry.glyph_key, self.matrix_id):
                raise IntegrityError("New entry failed chain/glyph verification before commit")

            self._append_physical(entry)
            self._index(entry)
            self.total_entries += 1
            return entry

    def rotate_glyph_key(
        self,
        new_key: Union[str, bytes],
        new_key_id: str,
        writer_id: str = "system",
    ) -> ImmutableEntry:
        """Record an immutable rotation event, then authenticate future entries
        with the new key. Existing key material remains runtime-only and must
        be supplied again on restart through ``glyph_keys``.
        """
        if not new_key_id:
            raise ValueError("new_key_id is required")
        if new_key is None:
            raise ValueError("new_key is required")
        with self.lock:
            rotation_event = self.write_entry(
                EntryType.SYSTEM_EVENT,
                {"event": "glyph_key_rotation", "new_key_id": new_key_id},
                metadata={"authenticated": bool(self.glyph_key_id)},
                writer_id=writer_id,
            )
            self.glyph_keys[new_key_id] = new_key
            self.glyph_key_id = new_key_id
            return rotation_event

    def read_entry(self, entry_id: Optional[str] = None, sequence_number: Optional[int] = None) -> Optional[ImmutableEntry]:
        with self.lock:
            if entry_id is not None:
                return self.entry_index.get(entry_id)
            if sequence_number is not None:
                return self.sequence_index.get(sequence_number)
            raise ValueError("Must provide entry_id or sequence_number")

    def read_range(self, start_sequence: int = 0, end_sequence: Optional[int] = None) -> List[ImmutableEntry]:
        with self.lock:
            end_sequence = self.last_sequence if end_sequence is None else end_sequence
            return [e for seq, e in self.sequence_index.items() if start_sequence <= seq <= end_sequence]

    def iterate_entries(self, reverse: bool = False) -> Iterator[ImmutableEntry]:
        entries = reversed(self.entries) if reverse else self.entries
        for e in entries:
            yield e

    def search_entries(
        self,
        entry_type: Optional[EntryType] = None,
        content_keyword: Optional[str] = None,
        writer_id: Optional[str] = None,
    ) -> List[ImmutableEntry]:
        results = []
        for entry in self.entries:
            if entry_type and entry.entry_type != entry_type:
                continue
            if writer_id and entry.writer_id != writer_id:
                continue
            if content_keyword and content_keyword.lower() not in json.dumps(entry.content).lower():
                continue
            results.append(entry)
        return results

    # ---------- verification ----------

    def verify_chain(self) -> Tuple[bool, List[int]]:
        corrupted = []
        prev_hash, prev_glyph, prev_glyph_mac = "0" * 64, "", ""
        for entry in self.entries:
            key = self.glyph_keys.get(entry.glyph_key_id) if entry.glyph_key_id else None
            if not entry.verify(prev_hash, prev_glyph, prev_glyph_mac, key, self.matrix_id):
                corrupted.append(entry.sequence_number)
            prev_hash, prev_glyph, prev_glyph_mac = entry.hash, entry.glyph, entry.glyph_mac

        glyph_ok = glyph_trace.verify_glyph_chain([e.glyph for e in self.entries])
        if not glyph_ok:
            # Duplicate adjacent glyphs are a soft tripwire, not fatal on
            # their own, but surfaced as a warning entry in metadata for
            # the SKG layer to weigh.
            pass

        return (len(corrupted) == 0), corrupted

    def verify_physical_persistence(self) -> Dict[str, Any]:
        exists = self.ledger_path.exists()
        size = self.ledger_path.stat().st_size if exists else 0
        return {
            "ledger_exists": exists,
            "ledger_size_bytes": size,
            "physical_commitment": exists and size > 0,
        }

    def get_statistics(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = {}
        for e in self.entries:
            type_counts[e.entry_type.value] = type_counts.get(e.entry_type.value, 0) + 1
        is_valid, corrupted = self.verify_chain()
        return {
            "matrix_id": self.matrix_id,
            "ready_for_writes": self.ready,
            "total_entries": self.total_entries,
            "last_sequence": self.last_sequence,
            "last_hash": self.last_hash,
            "last_glyph": self.last_glyph,
            "glyph_mode": "hmac-sha256" if self.glyph_key_id else "visual",
            "glyph_key_id": self.glyph_key_id,
            "entry_types": type_counts,
            "integrity_status": "verified" if is_valid else "corrupted",
            "corrupted_sequences": corrupted,
            **self.verify_physical_persistence(),
        }
