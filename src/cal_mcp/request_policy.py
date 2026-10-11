from __future__ import annotations

import math
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class CacheRecord(Generic[T]):
    """A successfully parsed CAL result and its original upstream provenance."""

    value: T
    source_url: str
    retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class CacheHit(Generic[T]):
    """Metadata for a process-local cache hit."""

    record: CacheRecord[T]
    age_seconds: float
    cache_hit: bool = True


@dataclass(slots=True)
class _CacheEntry(Generic[T]):
    record: CacheRecord[T]
    stored_at: float


class MemoryResponseCache(Generic[T]):
    """Bounded process-local LRU cache with TTL expiry.

    A zero ``max_entries`` disables retention completely. The cache stores only
    values explicitly supplied through ``put``; callers decide which upstream
    states are safe to cache.
    """

    def __init__(
        self,
        *,
        max_entries: int,
        ttl_seconds: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if type(max_entries) is not int or max_entries < 0:
            raise ValueError("max_entries must be a nonnegative integer")
        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, (int, float))
            or ttl_seconds <= 0
        ):
            raise ValueError("ttl_seconds must be a finite positive number")
        try:
            finite_ttl = math.isfinite(ttl_seconds)
        except OverflowError:
            # Python cannot represent a huge integer TTL as finite monotonic time.
            finite_ttl = False
        if not finite_ttl:
            raise ValueError("ttl_seconds must be a finite positive number")
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[str, _CacheEntry[T]] = OrderedDict()

    def get(self, key: str) -> CacheHit[T] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None

        age = max(0.0, self._clock() - entry.stored_at)
        if age >= self._ttl_seconds:
            del self._entries[key]
            return None

        self._entries.move_to_end(key)
        return CacheHit(record=entry.record, age_seconds=age)

    def put(self, key: str, record: CacheRecord[T]) -> None:
        if self._max_entries == 0:
            return

        self._entries[key] = _CacheEntry(record=record, stored_at=self._clock())
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def __len__(self) -> int:
        return len(self._entries)
