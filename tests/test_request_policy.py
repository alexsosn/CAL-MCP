from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cal_mcp.request_policy import CacheRecord, MemoryResponseCache


@dataclass
class FakeClock:
    now_value: float = 1000.0

    def __call__(self) -> float:
        return self.now_value

    def advance(self, seconds: float) -> None:
        self.now_value += seconds


def record(value: str, *, retrieved_at: datetime | None = None) -> CacheRecord[str]:
    return CacheRecord(
        value=value,
        source_url="https://cal.huc.edu/example",
        retrieved_at=retrieved_at or datetime(2026, 9, 4, tzinfo=UTC),
    )


def test_cache_is_bounded_lru_and_reads_refresh_recency() -> None:
    clock = FakeClock()
    cache = MemoryResponseCache[str](max_entries=2, ttl_seconds=60, clock=clock)

    cache.put("a", record("A"))
    cache.put("b", record("B"))
    assert cache.get("a") is not None  # a becomes most recently used

    cache.put("c", record("C"))

    assert cache.get("a") is not None
    assert cache.get("b") is None
    assert cache.get("c") is not None
    assert len(cache) == 2


def test_cache_ttl_expires_without_rewriting_upstream_retrieval_time() -> None:
    clock = FakeClock()
    retrieved_at = datetime(2026, 9, 4, 0, 0, tzinfo=UTC)
    cache = MemoryResponseCache[str](max_entries=2, ttl_seconds=10, clock=clock)
    cache.put("entry", record("value", retrieved_at=retrieved_at))

    hit = cache.get("entry")
    assert hit is not None
    assert hit.record.retrieved_at == retrieved_at
    assert hit.age_seconds == 0

    clock.advance(9)
    hit = cache.get("entry")
    assert hit is not None
    assert hit.record.retrieved_at == retrieved_at
    assert hit.age_seconds == 9

    clock.advance(2)
    assert cache.get("entry") is None
    assert len(cache) == 0


def test_cache_can_be_disabled_without_retaining_values() -> None:
    cache = MemoryResponseCache[str](max_entries=0, ttl_seconds=60)

    cache.put("entry", record("value"))

    assert cache.get("entry") is None
    assert len(cache) == 0


def test_cache_configuration_rejects_unbounded_or_invalid_values() -> None:
    for max_entries, ttl_seconds in [(-1, 60), (1, 0), (1, -1)]:
        try:
            MemoryResponseCache[str](max_entries=max_entries, ttl_seconds=ttl_seconds)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid cache bounds must be rejected")


def test_cache_record_is_process_memory_metadata_not_a_new_retrieval() -> None:
    retrieved_at = datetime.now(UTC) - timedelta(minutes=5)
    cache = MemoryResponseCache[str](max_entries=1, ttl_seconds=600)
    cache.put("entry", record("value", retrieved_at=retrieved_at))

    hit = cache.get("entry")

    assert hit is not None
    assert hit.record.retrieved_at == retrieved_at
    assert hit.cache_hit is True
