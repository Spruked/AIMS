"""
short_term.py
Short-Term Memory (STM) — volatile working cache.

Purpose: hold recent, not-yet-judged material cheaply and fast, without
paying the fsync cost of the long-term ledger on every touch. Nothing
here is permanent by default. STM entries either:
    (a) decay and get evicted, or
    (b) get promoted into the vault (see vault.py) once they survive
        enough recurrence/confidence to be worth judging for long-term
        placement.

This is intentionally the only layer in the system that is allowed to
forget silently. Long-term memory and the vault never do.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class STMItem:
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_touched: float = field(default_factory=time.time)
    touch_count: int = 1
    vivacity: float = 1.0  # 1.0 = fresh, decays toward 0

    def touch(self):
        self.last_touched = time.time()
        self.touch_count += 1
        self.vivacity = min(1.0, self.vivacity + 0.15)


class ShortTermMemory:
    """
    Capacity-bounded, vivacity-decayed working cache.

    decay_half_life_seconds: how fast un-touched items fade toward 0
    capacity: hard cap; when exceeded, lowest-vivacity items are evicted
    promotion_threshold: touch_count/vivacity combination that marks an
        item as a *candidate* for vault admission (actual admission is a
        decision made by the caller / vault layer, not by STM itself)
    """

    def __init__(
        self,
        capacity: int = 500,
        decay_half_life_seconds: float = 900.0,
        promotion_touch_count: int = 3,
        promotion_vivacity: float = 0.6,
    ):
        self.capacity = capacity
        self.decay_half_life_seconds = decay_half_life_seconds
        self.promotion_touch_count = promotion_touch_count
        self.promotion_vivacity = promotion_vivacity
        self._items: Dict[str, STMItem] = {}

    def _decay(self, item: STMItem) -> float:
        elapsed = time.time() - item.last_touched
        half_lives = elapsed / self.decay_half_life_seconds
        item.vivacity = item.vivacity * (0.5 ** half_lives)
        return item.vivacity

    def put(self, content: Dict[str, Any], tags: Optional[List[str]] = None) -> STMItem:
        item = STMItem(content=content, tags=tags or [])
        self._items[item.item_id] = item
        if len(self._items) > self.capacity:
            self._evict_lowest_vivacity()
        return item

    def touch(self, item_id: str) -> Optional[STMItem]:
        item = self._items.get(item_id)
        if item:
            self._decay(item)
            item.touch()
        return item

    def get(self, item_id: str) -> Optional[STMItem]:
        item = self._items.get(item_id)
        if item:
            self._decay(item)
        return item

    def sweep(self, min_vivacity: float = 0.05) -> int:
        """Evict everything that has decayed below min_vivacity. Returns
        the number evicted. This is the only place forgetting happens."""
        to_evict = []
        for item_id, item in self._items.items():
            if self._decay(item) < min_vivacity:
                to_evict.append(item_id)
        for item_id in to_evict:
            del self._items[item_id]
        return len(to_evict)

    def _evict_lowest_vivacity(self):
        if not self._items:
            return
        for item in self._items.values():
            self._decay(item)
        weakest_id = min(self._items, key=lambda k: self._items[k].vivacity)
        del self._items[weakest_id]

    def promotion_candidates(self) -> List[STMItem]:
        """Items that have earned a look from the vault layer: repeated
        enough, and still vivid enough, to be worth judging for
        long-term placement. STM does not decide admission — it only
        surfaces candidates.
        """
        candidates = []
        for item in self._items.values():
            self._decay(item)
            if item.touch_count >= self.promotion_touch_count and item.vivacity >= self.promotion_vivacity:
                candidates.append(item)
        return candidates

    def all_items(self) -> List[STMItem]:
        for item in self._items.values():
            self._decay(item)
        return list(self._items.values())

    def stats(self) -> Dict[str, Any]:
        items = self.all_items()
        return {
            "count": len(items),
            "capacity": self.capacity,
            "avg_vivacity": (sum(i.vivacity for i in items) / len(items)) if items else 0.0,
            "promotion_candidates": len(self.promotion_candidates()),
        }
