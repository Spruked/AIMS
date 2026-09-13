"""
glyph_trace.py
Glyph Trace — a second, independently-computed lineage marker that rides
alongside the SHA-256 hash chain.

Why a second chain:
    The hash chain proves machine-verifiable integrity, but a corrupted or
    substituted entry is invisible to a human scanning a log. The glyph
    trace maps each entry onto a short sequence of visually distinct
    symbols, derived independently from the entry's own hash. A human (or
    a lightweight monitor with no crypto library) can scan a column of
    glyphs and notice a break in the visual pattern before any hash
    verification runs. Because the glyph chain is threaded (each glyph
    depends on the prior glyph, not just the prior hash), a tampered entry
    breaks visual continuity even if the attacker manages to patch the
    hash chain.

This module has zero dependencies on the memory matrix itself — it is a
pure function of (previous_glyph, entry_hash) -> new_glyph, so it can be
dropped into any system that produces a hash per event.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Mapping, Optional, Union


DOMAIN_SEPARATOR = "AIML-GLYPH-V1"
KeyMaterial = Union[str, bytes]

# 64 visually distinct symbols. Deliberately avoids look-alike glyphs
# (no 0/O, 1/l/I confusion, etc.) since this trace is meant to be scanned
# by eye, not just by machine.
GLYPH_ALPHABET = (
    "\u25B2\u25B3\u25BC\u25BD\u25C6\u25C7\u25CF\u25CB"  # ▲△▼▽◆◇●○
    "\u2605\u2606\u2660\u2661\u2662\u2663\u2664\u2665"  # ★☆♠♡♢♣♤♥
    "\u2666\u2667\u2669\u266A\u266B\u26A0\u2708\u2716"  # ♦♧♩♪♫⚠✈✖
    "\u2728\u272A\u272D\u2731\u2733\u2734\u2735\u2736"  # ✨✪✭✱✳✴✵✶
    "\u2737\u2738\u2739\u273A\u273B\u273C\u273D\u2742"  # ✷✸✹✺✻✼✽❂
    "\u2743\u2744\u2745\u2746\u2747\u2748\u2749\u274A"  # ❃❄❅❆❇❈❉❊
    "\u274D\u2751\u2752\u2756\u2764\u27A1\u2B24\u2B25"  # ❍❑❒❖❤➡⬤⬥
    "\u2B26\u2B27\u2B28\u2B29\u2B2A\u2B2B\u2B2C\u2B2D"  # ⬦⬧⬨⬩⬪⬫⬬⬭
)
_BASE = len(GLYPH_ALPHABET)


def _hash_to_glyphs(digest_hex: str, width: int) -> str:
    """Map a hex digest onto `width` glyphs from GLYPH_ALPHABET."""
    value = int(digest_hex, 16)
    out = []
    for _ in range(width):
        value, idx = divmod(value, _BASE)
        out.append(GLYPH_ALPHABET[idx])
    return "".join(reversed(out))


def derive_glyph(entry_hash: str, width: int = 5) -> str:
    """Independent, single-entry glyph derived only from this entry's own
    content hash. Two entries with identical content hashes always render
    the same glyph — this is intentional and used as a duplicate-content
    tripwire.
    """
    return _hash_to_glyphs(entry_hash, width)


def thread_glyph(previous_glyph: str, entry_hash: str, width: int = 5) -> str:
    """Chain the previous glyph into the next one, producing the actual
    lineage marker stored on each entry. This is what makes the glyph
    trace a *chain* rather than a set of independent fingerprints:
    tampering with entry N without also correctly re-deriving every
    glyph from N onward breaks the visible pattern.
    """
    seed = hashlib.sha256((previous_glyph + entry_hash).encode("utf-8")).hexdigest()
    return _hash_to_glyphs(seed, width)


def glyph_mac(
    key: KeyMaterial,
    vault_id: str,
    record_id: str,
    sequence: int,
    entry_hash: str,
    previous_glyph_mac: str,
    tri_timestamp: Mapping[str, object],
) -> str:
    """Create the authenticated Glyph lineage value.

    The key is runtime-only. This function deliberately accepts the
    timestamp as structured data and canonicalizes it before authentication.
    """
    key_bytes = key.encode("utf-8") if isinstance(key, str) else key
    payload = "|".join(
        (
            DOMAIN_SEPARATOR,
            vault_id,
            record_id,
            str(sequence),
            entry_hash,
            previous_glyph_mac,
            json.dumps(dict(tri_timestamp), sort_keys=True, separators=(",", ":")),
        )
    ).encode("utf-8")
    return hmac.new(key_bytes, payload, hashlib.sha256).hexdigest()


def verify_glyph_mac(
    key: Optional[KeyMaterial],
    expected: str,
    vault_id: str,
    record_id: str,
    sequence: int,
    entry_hash: str,
    previous_glyph_mac: str,
    tri_timestamp: Mapping[str, object],
) -> bool:
    """Verify a keyed Glyph value using constant-time comparison."""
    if key is None or not expected:
        return False
    actual = glyph_mac(
        key, vault_id, record_id, sequence, entry_hash,
        previous_glyph_mac, tri_timestamp,
    )
    return hmac.compare_digest(actual, expected)


def glyph_from_mac(mac: str, width: int = 5) -> str:
    """Render authenticated bytes as human-readable glyph symbols."""
    return _hash_to_glyphs(mac, width)


def verify_glyph_chain(glyphs_in_order: list) -> bool:
    """Sanity check: no two adjacent entries in a healthy chain should
    ever render the identical glyph token (astronomically unlikely
    unless something upstream duplicated an entry_hash + previous_glyph
    pair). Not a substitute for hash verification — a cheap, fast,
    human-legible pre-check.
    """
    for a, b in zip(glyphs_in_order, glyphs_in_order[1:]):
        if a == b:
            return False
    return True
