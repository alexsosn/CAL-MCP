"""Bounded, opt-in positive external citation diagnostic for issue #345.

This manual installed-wheel research probe never exports CAL citation or lexical text.
Importing the module has no network side effects.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Protocol

from cal_mcp.client import CalClientConfig, CalHttpClient, CalUpstreamError
from cal_mcp.external_citations import (
    ExternalCitationResult,
    ExternalCitationService,
    ExternalCitationSourceResult,
)

_CANDIDATE = "EbPar"
_CANONICAL_URL = "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar"
_MAX_ATTEMPTS = 2


class _SourceLike(Protocol):
    abbreviation: str
    citations_url: str


class _SourceResultLike(Protocol):
    dialect_id: str
    sources: tuple[_SourceLike, ...]


def choose_candidate(result: _SourceResultLike) -> str | None:
    """Require a source-backed exact CAL navigation target; duplicates must agree."""
    if result.dialect_id != "6":
        return None
    matches = [source for source in result.sources if source.abbreviation == _CANDIDATE]
    if not matches:
        return None
    if not all(source.citations_url == _CANONICAL_URL for source in matches):
        return None
    return _CANDIDATE


def is_positive(result: ExternalCitationResult, requested_source: str) -> bool:
    """An explicit CAL empty page can be valid but cannot prove a positive case."""
    return (
        requested_source == _CANDIDATE
        and result.source_abbrev == requested_source
        and type(result.total) is int
        and result.total > 0
        and result.total == len(result.citations)
    )


async def diagnose_once(*, sleep: Callable[[float], object] = asyncio.sleep) -> dict[str, object]:
    """At most two non-retried CAL starts, with one 60s completion-based pause."""
    attempts = 0

    def before_attempt() -> None:
        nonlocal attempts
        if attempts >= _MAX_ATTEMPTS:
            raise RuntimeError("issue 345 diagnostic exceeded approved transport starts")
        attempts += 1

    config = CalClientConfig(
        max_concurrency=1,
        max_retries=0,
        cache_enabled=False,
        min_request_interval_seconds=3.0,
        max_cal_attempts_per_60s=2,
    )
    try:
        async with CalHttpClient(config=config, before_transport_attempt=before_attempt) as http:
            service = ExternalCitationService(http)
            sources: ExternalCitationSourceResult = await service.sources("6")
            chosen = choose_candidate(sources)
            if chosen is None:
                return {
                    "status": "blocked",
                    "category": "no_verified_source",
                    "actual_cal_transport_attempts": attempts,
                }
            await sleep(60.0)
            result = await service.citations(chosen)
    except CalUpstreamError as exc:
        return {
            "status": "blocked",
            "category": "upstream_http",
            "http_status": exc.status_code,
            "actual_cal_transport_attempts": attempts,
        }
    except Exception:
        return {
            "status": "blocked",
            "category": "harness_or_parser",
            "actual_cal_transport_attempts": attempts,
        }

    return {
        "status": "positive" if is_positive(result, chosen) else "explicit_empty",
        "source_abbrev": chosen,
        "total_citations": result.total,
        "actual_cal_transport_attempts": attempts,
        "max_cal_transport_attempts": _MAX_ATTEMPTS,
    }


def main() -> None:
    report = asyncio.run(diagnose_once())
    print(json.dumps(report, sort_keys=True))
    if report["status"] != "positive":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
