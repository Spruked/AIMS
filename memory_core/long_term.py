"""Append-only A.I.M.S. ledger with hash, Glyph, policy, and writer safety."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple, Union

from . import glyph_trace
from .temporal import TriTimestamp
from .writer_lock import LedgerWriterLock


KeyMaterial = Union[str, bytes]
SECURITY_VISUAL = "visual"
SECURITY_AUTHENTICATED = "authenticated"
_SECURITY_MODES = {SECURITY_VISUAL, SECURITY_AUTHENTICATED}


class EntryType(Enum):
    EXPERIENCE = "experience"
    DECISION = "decision"
    LEARNING = "learning"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    INTERACTION = "interaction"
    SYSTEM_EVENT = "system_event"


class IntegrityError(Exception):
    """Raised when policy, sequence, hash, Glyph, or persistence checks fail."""


@dataclass
class ImmutableEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence_number: int = 0
    tri_timestamp: TriTimestamp = field(default_factory=TriTimestamp.now)
    entry_type: EntryType = EntryType.EXPERIENCE
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""
    writer_id: str = "system"
    vault_id: str = "long_term_matrix"
    glyph_mode: str = SECURITY_VISUAL
    glyph_key_id: Optional[str] = None
    previous_glyph_mac: str = ""
    entry_hash: str = field(init=False, default="")
    glyph_mac: str = field(init=False, default="")
    glyph: str = field(init=False, default="")
    integrity_verified: bool = True
    _glyph_key: Optional[KeyMaterial] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        self.entry_hash = self._compute_hash()
        if self.glyph_mode == SECURITY_AUTHENTICATED:
            if not self.glyph_key_id or self._glyph_key is None:
                raise IntegrityError("Authenticated Glyph entry requires a runtime key and key_id")
            self.glyph_mac = glyph_trace.glyph_mac(self._glyph_key, self.entry_hash, self.previous_glyph_mac)
            self.glyph = glyph_trace.glyph_from_mac(self.glyph_mac)
        elif self.glyph_mode == SECURITY_VISUAL:
            self.glyph = glyph_trace.thread_glyph(self.previous_glyph_mac, self.entry_hash)
        else:
            raise IntegrityError(f"Unsupported Glyph mode: {self.glyph_mode}")

    def canonical_record(self) -> Dict[str, Any]:
        """All fields whose meaning must survive a hash-chain verification."""
        return {
            "entry_id": self.entry_id,
            "sequence_number": self.sequence_number,
            "tri_timestamp": self.tri_timestamp.to_dict(),
            "entry_type": self.entry_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
            "writer_id": self.writer_id,
            "vault_id": self.vault_id,
            "glyph_mode": self.glyph_mode,
            "glyph_key_id": self.glyph_key_id,
        }

    def _compute_hash(self) -> str:
        encoded = json.dumps(self.canonical_record(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Dict[str, Any], glyph_key: Optional[KeyMaterial]) -> "ImmutableEntry":
        entry = cls(
            entry_id=data["entry_id"], sequence_number=data["sequence_number"],
            tri_timestamp=TriTimestamp.from_dict(data["tri_timestamp"]),
            entry_type=EntryType(data["entry_type"]), content=data["content"],
            metadata=data["metadata"], previous_hash=data["previous_hash"],
            writer_id=data["writer_id"], vault_id=data["vault_id"],
            glyph_mode=data["glyph_mode"], glyph_key_id=data.get("glyph_key_id"),
            previous_glyph_mac=data.get("previous_glyph_mac", ""), _glyph_key=glyph_key,
        )
        expected_hash = data["entry_hash"]
        expected_mac = data.get("glyph_mac", "")
        expected_glyph = data.get("glyph", "")
        if entry.entry_hash != expected_hash:
            raise IntegrityError(f"Entry {entry.sequence_number} has an invalid canonical hash")
        if entry.glyph_mac != expected_mac or entry.glyph != expected_glyph:
            raise IntegrityError(f"Entry {entry.sequence_number} has invalid Glyph material")
        entry.integrity_verified = bool(data.get("integrity_verified", True))
        return entry

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.canonical_record(), "entry_hash": self.entry_hash,
            "previous_glyph_mac": self.previous_glyph_mac, "glyph_mac": self.glyph_mac,
            "glyph": self.glyph, "glyph_trace": {
                "version": 2, "mode": self.glyph_mode, "key_id": self.glyph_key_id,
                "previous_glyph_mac": self.previous_glyph_mac, "glyph_mac": self.glyph_mac,
                "glyph": self.glyph,
            }, "integrity_verified": self.integrity_verified,
        }

    @property
    def hash(self) -> str:
        return self.entry_hash

    def verify(
        self, expected_sequence: int, expected_previous_hash: str,
        expected_previous_glyph_mac: str, security_mode: str,
        glyph_key: Optional[KeyMaterial],
    ) -> bool:
        if self.sequence_number != expected_sequence or self.previous_hash != expected_previous_hash:
            return False
        if self.glyph_mode != security_mode or not self.tri_timestamp.verify_internal_consistency():
            return False
        if self._compute_hash() != self.entry_hash:
            return False
        if self.glyph_mode == SECURITY_AUTHENTICATED:
            valid = (
                self.previous_glyph_mac == expected_previous_glyph_mac
                and glyph_trace.verify_glyph_mac(glyph_key, self.entry_hash, self.previous_glyph_mac, self.glyph_mac)
                and self.glyph == glyph_trace.glyph_from_mac(self.glyph_mac)
            )
        else:
            valid = (
                not self.glyph_key_id and not self.glyph_mac and not self.previous_glyph_mac
                and self.glyph == glyph_trace.thread_glyph("", self.entry_hash)
            )
        self.integrity_verified = valid
        return valid


class LongTermMemory:
    """Single-writer append-only ledger with an immutable genesis policy."""

    def __init__(
        self, store_path: Path, matrix_id: str = "long_term_matrix",
        glyph_key: Optional[KeyMaterial] = None, glyph_key_id: Optional[str] = None,
        glyph_keys: Optional[Mapping[str, KeyMaterial]] = None,
        security_mode: Optional[str] = None,
    ):
        self.store_path = Path(store_path)
        self.matrix_id = matrix_id
        self.ledger_path = self.store_path / f"{matrix_id}.ledger"
        self.lock_path = self.store_path / f"{matrix_id}.writer.lock"
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.glyph_keys = dict(glyph_keys or {})
        if glyph_key is not None:
            if not glyph_key_id:
                raise ValueError("glyph_key_id is required when glyph_key is supplied")
            self.glyph_keys[glyph_key_id] = glyph_key
        self.glyph_key_id = glyph_key_id
        inferred_mode = SECURITY_AUTHENTICATED if glyph_key is not None else SECURITY_VISUAL
        self.required_security_mode = security_mode or inferred_mode
        if self.required_security_mode not in _SECURITY_MODES:
            raise ValueError("security_mode must be 'visual' or 'authenticated'")
        self.security_mode = self.required_security_mode
        self.entries: List[ImmutableEntry] = []
        self.entry_index: Dict[str, ImmutableEntry] = {}
        self.sequence_index: Dict[int, ImmutableEntry] = {}
        self.last_sequence = -1
        self.last_hash = "0" * 64
        self.last_glyph_mac = ""
        self.total_entries = 0
        self.lock = threading.RLock()
        self.ready = False
        self._self_check()

    def _reset(self):
        self.entries.clear(); self.entry_index.clear(); self.sequence_index.clear()
        self.last_sequence = -1; self.last_hash = "0" * 64; self.last_glyph_mac = ""; self.total_entries = 0

    def _self_check(self):
        self._reset()
        if self.ledger_path.exists() and self.ledger_path.stat().st_size:
            self._read_policy_and_replay()
        else:
            self._write_genesis()
        valid, corrupted = self.verify_chain()
        if not valid:
            raise IntegrityError(f"Startup self-check failed at sequences {corrupted}")
        self.ready = True

    def _read_policy_and_replay(self):
        first_line = next((line for line in self.ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()), None)
        if not first_line:
            self._write_genesis(); return
        try:
            genesis = json.loads(first_line)
            policy = genesis["content"]["security_policy"]
            declared_mode = policy["required_glyph_mode"]
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise IntegrityError("Ledger is missing a valid immutable genesis security policy") from error
        if declared_mode not in _SECURITY_MODES or declared_mode != self.required_security_mode:
            raise IntegrityError(f"Ledger security mode {declared_mode!r} does not match required mode {self.required_security_mode!r}")
        self.security_mode = declared_mode
        self._replay()

    def _write_genesis(self):
        if self.security_mode == SECURITY_AUTHENTICATED and (not self.glyph_key_id or self.glyph_key_id not in self.glyph_keys):
            raise IntegrityError("Authenticated ledger genesis requires an active Glyph keyring entry")
        entry = self._new_entry(
            EntryType.SYSTEM_EVENT,
            {"event": "ledger_genesis", "security_policy": {"version": 1, "required_glyph_mode": self.security_mode}},
            {"immutable_policy": True}, "system",
        )
        self._append_physical(entry); self._index(entry)

    def _replay(self):
        with open(self.ledger_path, "r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                    key_id = raw.get("glyph_key_id")
                    entry = ImmutableEntry.from_dict(raw, self.glyph_keys.get(key_id) if key_id else None)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError, IntegrityError) as error:
                    raise IntegrityError(f"Invalid ledger entry at line {line_number}") from error
                key = self.glyph_keys.get(entry.glyph_key_id) if entry.glyph_key_id else None
                if not entry.verify(self.last_sequence + 1, self.last_hash, self.last_glyph_mac, self.security_mode, key):
                    raise IntegrityError(f"Entry {entry.sequence_number} (line {line_number}) failed verification")
                self._index(entry)

    def _new_entry(self, entry_type: EntryType, content: Dict[str, Any], metadata: Optional[Dict[str, Any]], writer_id: str) -> ImmutableEntry:
        key = self.glyph_keys.get(self.glyph_key_id) if self.glyph_key_id else None
        return ImmutableEntry(
            sequence_number=self.last_sequence + 1, entry_type=entry_type, content=content,
            metadata=metadata or {}, previous_hash=self.last_hash, writer_id=writer_id,
            vault_id=self.matrix_id, glyph_mode=self.security_mode, glyph_key_id=self.glyph_key_id,
            previous_glyph_mac=self.last_glyph_mac, _glyph_key=key,
        )

    def _index(self, entry: ImmutableEntry):
        self.entries.append(entry); self.entry_index[entry.entry_id] = entry; self.sequence_index[entry.sequence_number] = entry
        self.last_sequence = entry.sequence_number; self.last_hash = entry.hash; self.last_glyph_mac = entry.glyph_mac
        self.total_entries = len(self.entries)

    def _append_physical(self, entry: ImmutableEntry):
        with open(self.ledger_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            handle.flush(); os.fsync(handle.fileno())

    def write_entry(self, entry_type: EntryType, content: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None, writer_id: str = "system") -> ImmutableEntry:
        with self.lock, LedgerWriterLock(self.lock_path):
            self._self_check()
            entry = self._new_entry(entry_type, content, metadata, writer_id)
            key = self.glyph_keys.get(entry.glyph_key_id) if entry.glyph_key_id else None
            if not entry.verify(self.last_sequence + 1, self.last_hash, self.last_glyph_mac, self.security_mode, key):
                raise IntegrityError("New entry failed verification before commit")
            self._append_physical(entry); self._index(entry)
            return entry

    def rotate_glyph_key(self, new_key: KeyMaterial, new_key_id: str, writer_id: str = "system") -> ImmutableEntry:
        if self.security_mode != SECURITY_AUTHENTICATED:
            raise IntegrityError("Glyph key rotation requires an authenticated ledger")
        if not new_key_id or new_key_id == self.glyph_key_id:
            raise ValueError("new_key_id must be a new non-empty key ID")
        old_key_id = self.glyph_key_id
        event = self.write_entry(EntryType.SYSTEM_EVENT, {"event": "glyph_key_rotation", "previous_key_id": old_key_id, "new_key_id": new_key_id}, None, writer_id)
        self.glyph_keys[new_key_id] = new_key
        self.glyph_key_id = new_key_id
        return event

    def read_entry(self, entry_id: Optional[str] = None, sequence_number: Optional[int] = None) -> Optional[ImmutableEntry]:
        if entry_id is not None: return self.entry_index.get(entry_id)
        if sequence_number is not None: return self.sequence_index.get(sequence_number)
        raise ValueError("Must provide entry_id or sequence_number")

    def read_range(self, start_sequence: int = 0, end_sequence: Optional[int] = None) -> List[ImmutableEntry]:
        finish = self.last_sequence if end_sequence is None else end_sequence
        return [entry for entry in self.entries if start_sequence <= entry.sequence_number <= finish]

    def iterate_entries(self, reverse: bool = False) -> Iterator[ImmutableEntry]:
        yield from (reversed(self.entries) if reverse else self.entries)

    def search_entries(self, entry_type: Optional[EntryType] = None, content_keyword: Optional[str] = None, writer_id: Optional[str] = None) -> List[ImmutableEntry]:
        return [entry for entry in self.entries if (
            (not entry_type or entry.entry_type == entry_type)
            and (not writer_id or entry.writer_id == writer_id)
            and (not content_keyword or content_keyword.lower() in json.dumps(entry.content).lower())
        )]

    def verify_chain(self) -> Tuple[bool, List[int]]:
        corrupted: List[int] = []
        sequence, previous_hash, previous_mac = 0, "0" * 64, ""
        for entry in self.entries:
            key = self.glyph_keys.get(entry.glyph_key_id) if entry.glyph_key_id else None
            if not entry.verify(sequence, previous_hash, previous_mac, self.security_mode, key):
                corrupted.append(entry.sequence_number)
            sequence += 1; previous_hash = entry.hash; previous_mac = entry.glyph_mac
        return not corrupted, corrupted

    def verify_physical_persistence(self) -> Dict[str, Any]:
        exists = self.ledger_path.exists()
        return {"ledger_exists": exists, "ledger_size_bytes": self.ledger_path.stat().st_size if exists else 0, "durable_commit": exists and self.total_entries > 0}

    def perform_manual_self_check(self) -> Dict[str, Any]:
        try:
            with self.lock, LedgerWriterLock(self.lock_path): self._self_check()
            return {"success": True, "entries_verified": self.total_entries, "ready": self.ready}
        except (IntegrityError, TimeoutError) as error:
            self.ready = False
            return {"success": False, "error": str(error), "ready": False}

    def get_statistics(self) -> Dict[str, Any]:
        valid, corrupted = self.verify_chain()
        return {
            "matrix_id": self.matrix_id, "security_mode": self.security_mode,
            "active_glyph_key_id": self.glyph_key_id, "ready_for_writes": self.ready,
            "total_entries": self.total_entries, "last_sequence": self.last_sequence,
            "last_hash": self.last_hash, "integrity_status": "verified" if valid else "corrupted",
            "corrupted_sequences": corrupted, **self.verify_physical_persistence(),
        }
