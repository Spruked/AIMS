"""
temporal.py
Tri-Timestamp Model — agnostic, dependency-free.

Every memory event in this system is stamped with three parallel,
mutually-derivable representations of "when":

    epoch     - Unix epoch seconds (float), the machine-native anchor
    standard  - ISO-8601 local/UTC string, the human-native anchor
    julian    - Julian Day Number (float), the astronomical/continuity anchor

No single calendar is authoritative. The triad exists so that any
downstream system — regardless of its own notion of time — can verify
"when" against at least one representation it understands, and so that
clock or calendar bugs in one representation are caught by disagreement
with the other two (see TriTimestamp.verify_internal_consistency).

This replaces any mission-specific stardate/ISS timestamp source. It has
no dependency on an external time authority: it is computed purely from
the local system clock (or an injected datetime for deterministic tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Julian Day Number of the Unix epoch (1970-01-01T00:00:00Z)
_UNIX_EPOCH_JDN = 2440587.5


@dataclass(frozen=True)
class TriTimestamp:
    epoch: float
    standard: str
    julian: float

    @classmethod
    def now(cls, tz: Optional[timezone] = timezone.utc) -> "TriTimestamp":
        return cls.from_datetime(datetime.now(tz))

    @classmethod
    def from_datetime(cls, dt: datetime) -> "TriTimestamp":
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        epoch = dt.timestamp()
        standard = dt.isoformat()
        julian = _UNIX_EPOCH_JDN + (epoch / 86400.0)
        return cls(epoch=epoch, standard=standard, julian=julian)

    @classmethod
    def from_epoch(cls, epoch: float) -> "TriTimestamp":
        dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        return cls.from_datetime(dt)

    def verify_internal_consistency(self, tolerance_seconds: float = 1.0) -> bool:
        """Cross-check all three representations against each other.

        Recomputes epoch/julian from `standard` and julian from `epoch`;
        flags drift beyond tolerance as a sign of tampering or clock skew.
        """
        try:
            reparsed = datetime.fromisoformat(self.standard)
        except ValueError:
            return False
        if reparsed.tzinfo is None:
            reparsed = reparsed.replace(tzinfo=timezone.utc)
        recomputed_epoch = reparsed.timestamp()
        recomputed_julian = _UNIX_EPOCH_JDN + (self.epoch / 86400.0)

        epoch_ok = abs(recomputed_epoch - self.epoch) <= tolerance_seconds
        julian_ok = abs(recomputed_julian - self.julian) <= (tolerance_seconds / 86400.0)
        return epoch_ok and julian_ok

    def to_dict(self) -> Dict[str, Any]:
        return {"epoch": self.epoch, "standard": self.standard, "julian": self.julian}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriTimestamp":
        return cls(epoch=data["epoch"], standard=data["standard"], julian=data["julian"])

    def __str__(self) -> str:  # human-friendly default
        return f"{self.standard} (epoch={self.epoch:.3f}, JD={self.julian:.6f})"
