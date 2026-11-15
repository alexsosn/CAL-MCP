"""Bounded, opt-in positive external citation diagnostic for issue #345.

This manual installed-wheel research probe never exports CAL citation or lexical text.
Importing the module has no network side effects.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from cal_mcp.client import CalClientConfig, CalHttpClient, CalUpstreamError
from cal_mcp.external_citations import (
    ExternalCitationDialectResult,
    ExternalCitationResult,
    ExternalCitationService,
    ExternalCitationSourceResult,
)

_CANDIDATE = "EbPar"
_CANONICAL_URL = "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar"
_MAX_ATTEMPTS = 2


def choose_syriac_dialect(result: ExternalCitationDialectResult) -> str | None:
    """Only accept one distinct current CAL Syriac selector with the correct label."""
    selected = [item for item in result.dialects if item.dialect_id == "6"]
    if len(selected) == 1 and selected[0].label == "Syriac":
        return "6"
    return None


def choose_candidate(result: ExternalCitationSourceResult) -> str | None:
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


async def diagnose_once(*, include_dialects: bool = False) -> dict[str, object]:
    """Opt-in two/three non-retried CAL starts, >=60s completion-based spacing."""
    attempts = 0
    budget = 3 if include_dialects else 2

    def before_attempt() -> None:
        nonlocal attempts
        if attempts >= budget:
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
            if include_dialects:
                discovered = await service.dialects()
                dialect_id = choose_syriac_dialect(discovered)
                if dialect_id is None:
                    return {
                        "status": "blocked",
                        "category": "no_verified_dialect",
                        "actual_cal_transport_attempts": attempts,
                    }
                await asyncio.sleep(60.0)
            else:
                dialect_id = "6"
            sources: ExternalCitationSourceResult = await service.sources(dialect_id)
            chosen = choose_candidate(sources)
            if chosen is None:
                return {
                    "status": "blocked",
                    "category": "no_verified_source",
                    "actual_cal_transport_attempts": attempts,
                }
            await asyncio.sleep(60.0)
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
        "max_cal_transport_attempts": budget,
        "included_dialects": include_dialects,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded external citation CAL diagnostic")
    parser.add_argument("--with-dialects", action="store_true")
    args = parser.parse_args()
    report = asyncio.run(diagnose_once(include_dialects=args.with_dialects))
    print(json.dumps(report, sort_keys=True))
    if report["status"] != "positive":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
