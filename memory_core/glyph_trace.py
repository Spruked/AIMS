"""Visual and authenticated Glyph Trace primitives for A.I.M.S."""

from __future__ import annotations

import hashlib
import hmac
from typing import Optional, Union


DOMAIN_SEPARATOR = b"AIMS-GLYPH-V1\x00"
KeyMaterial = Union[str, bytes]
GLYPH_ALPHABET = (
    "▲△▼▽◆◇●○★☆♠♡♢♣♤♥"
    "♦♧♪♫♬⚠✈✖✨✪✭✱✳✴✵✶"
    "✷✸✹✺✻✼✽❂❃❄❅❆❇❈❉❊"
    "❍❑❒❖❤➡⬤⬥⬦⬧⬨⬩⬪⬫⬬⬭"
)
_BASE = len(GLYPH_ALPHABET)


def _hash_to_glyphs(digest_hex: str, width: int = 5) -> str:
    value = int(digest_hex, 16)
    symbols = []
    for _ in range(width):
        value, index = divmod(value, _BASE)
        symbols.append(GLYPH_ALPHABET[index])
    return "".join(reversed(symbols))


def derive_glyph(entry_hash: str, width: int = 5) -> str:
    return _hash_to_glyphs(entry_hash, width)


def thread_glyph(previous_glyph: str, entry_hash: str, width: int = 5) -> str:
    digest = hashlib.sha256(f"{previous_glyph}\x00{entry_hash}".encode("utf-8")).hexdigest()
    return _hash_to_glyphs(digest, width)


def glyph_mac(key: KeyMaterial, entry_hash: str, previous_glyph_mac: str) -> str:
    """Authenticate a previously canonicalized entry hash and MAC predecessor."""
    key_bytes = key.encode("utf-8") if isinstance(key, str) else key
    material = DOMAIN_SEPARATOR + entry_hash.encode("ascii") + b"\x00" + previous_glyph_mac.encode("ascii")
    return hmac.new(key_bytes, material, hashlib.sha256).hexdigest()


def verify_glyph_mac(
    key: Optional[KeyMaterial], entry_hash: str, previous_glyph_mac: str, expected: str
) -> bool:
    if key is None or not expected:
        return False
    return hmac.compare_digest(glyph_mac(key, entry_hash, previous_glyph_mac), expected)


def glyph_from_mac(mac: str, width: int = 5) -> str:
    return _hash_to_glyphs(mac, width)


def verify_glyph_chain(glyphs_in_order: list) -> bool:
    return all(left != right for left, right in zip(glyphs_in_order, glyphs_in_order[1:]))
