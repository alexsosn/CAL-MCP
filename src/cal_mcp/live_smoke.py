from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, TypeVar, cast

from cal_mcp.bibliography import BibliographyParseError, BibliographyService
from cal_mcp.client import (
    CalClientConfig,
    CalContentError,
    CalFetchResult,
    CalHttpClient,
    CalNetworkError,
    CalRequest,
    CalResponse,
    CalUpstreamError,
    Transport,
)
from cal_mcp.concordance import ConcordanceParseError, ConcordanceService
from cal_mcp.dictionary_collation import (
    DictionaryCollationParseError,
    DictionaryCollationService,
    DictionarySource,
)
from cal_mcp.external_citations import ExternalCitationParseError, ExternalCitationService
from cal_mcp.lexicon import LexiconLookupService, LexiconParseError
from cal_mcp.search import SearchParseError
from cal_mcp.syriac import SyriacParseError, SyriacService
from cal_mcp.targum import TargumParseError, TargumService
from cal_mcp.texts import TextParseError, TextService
from cal_mcp.token_analysis import TokenAnalysisParseError

T = TypeVar("T")
MAX_CAL_REQUESTS = 9
SmokeFailureCategory = Literal["drift", "upstream", "content", "harness"]
SmokeOperation = Callable[["BudgetCalHttpClient"], Awaitable[None]]


class LiveSmokeBudgetExceeded(RuntimeError):
    """Raised before a live smoke request would exceed the fixed CAL request budget."""


class LiveSmokeSemanticError(CalContentError):
    """Raised when a selected smoke operation no longer returns its expected success shape."""


class LiveSmokeFailure(RuntimeError):
    """Raised when one representative live-smoke operation fails."""

    def __init__(
        self,
        case_name: str,
        category: SmokeFailureCategory,
        cause: BaseException,
    ) -> None:
        self.case_name = case_name
        self.category = category
        self.cause = cause
        super().__init__(f"live smoke {case_name!r} failed [{category}]: {cause}")


@dataclass(frozen=True, slots=True)
class SmokeCase:
    name: str
    operation: SmokeOperation


@dataclass(frozen=True, slots=True)
class LiveSmokeReport:
    completed_cases: tuple[str, ...]
    request_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "completed_cases": list(self.completed_cases),
            "request_count": self.request_count,
            "max_cal_requests": MAX_CAL_REQUESTS,
        }


class BudgetCalHttpClient(CalHttpClient):
    """CAL client with the stricter fixed release-smoke request policy."""

    def __init__(self, *, transport: Transport | None = None) -> None:
        super().__init__(
            config=CalClientConfig(
                max_concurrency=1,
                max_retries=0,
                cache_enabled=False,
            ),
            transport=transport,
        )
        self.request_count = 0

    async def fetch(
        self,
        request: CalRequest,
        *,
        parser: Callable[[CalResponse], T],
        cache_namespace: str,
    ) -> CalFetchResult[T]:
        if self.request_count >= MAX_CAL_REQUESTS:
            raise LiveSmokeBudgetExceeded(
                f"CAL request budget exhausted at {MAX_CAL_REQUESTS} requests"
            )
        self.request_count += 1
        return await super().fetch(
            request,
            parser=parser,
            cache_namespace=cache_namespace,
        )


_PARSER_ERRORS = (
    LiveSmokeSemanticError,
    LexiconParseError,
    SearchParseError,
    TextParseError,
    TokenAnalysisParseError,
    ConcordanceParseError,
    BibliographyParseError,
    DictionaryCollationParseError,
    ExternalCitationParseError,
    TargumParseError,
    SyriacParseError,
)


def classify_smoke_exception(exc: BaseException) -> SmokeFailureCategory:
    """Classify a smoke failure without collapsing parser drift into availability failure."""

    if isinstance(exc, _PARSER_ERRORS):
        return "drift"
    if isinstance(exc, (CalNetworkError, CalUpstreamError)):
        return "upstream"
    if isinstance(exc, CalContentError):
        return "content"
    return "harness"


def _require_provenance(payload: dict[str, object], case_name: str) -> None:
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise LiveSmokeSemanticError(f"{case_name} returned no provenance object")
    typed = cast(dict[str, object], provenance)
    source_url = typed.get("source_url")
    retrieved_at = typed.get("retrieved_at")
    if not isinstance(source_url, str) or not source_url.startswith("https://cal.huc.edu/"):
        raise LiveSmokeSemanticError(f"{case_name} returned invalid CAL source provenance")
    if not isinstance(retrieved_at, str) or not retrieved_at:
        raise LiveSmokeSemanticError(f"{case_name} returned no retrieval timestamp")


def _require_nonempty_list(payload: dict[str, object], key: str, case_name: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise LiveSmokeSemanticError(f"{case_name} returned no {key}")
    return cast(list[object], value)


async def _probe_lexicon(client: BudgetCalHttpClient) -> None:
    result = await LexiconLookupService(client).lookup("br", lemma_key="br N")
    payload = result.to_dict()
    if payload.get("status") != "found" or payload.get("entry") is None:
        raise LiveSmokeSemanticError("lexicon representative entry is no longer found")
    _require_provenance(payload, "lexicon")


async def _probe_text_search(client: BudgetCalHttpClient) -> None:
    result = await TextService(client).search("Tel Dan")
    payload = result.to_dict()
    matches = _require_nonempty_list(payload, "matches", "text_search")
    if not any(isinstance(item, dict) and item.get("file_id") == "13250" for item in matches):
        raise LiveSmokeSemanticError("text_search no longer returns CAL file 13250 for Tel Dan")
    _require_provenance(payload, "text_search")


async def _probe_text_concordance(client: BudgetCalHttpClient) -> None:
    result = await ConcordanceService(client).text_concordance("13250")
    payload = result.to_dict()
    _require_nonempty_list(payload, "lemmas", "text_concordance")
    _require_provenance(payload, "text_concordance")


async def _probe_bibliography(client: BudgetCalHttpClient) -> None:
    result = await BibliographyService(client).lemma("cly V")
    payload = result.to_dict()
    _require_nonempty_list(payload, "records", "bibliography")
    _require_provenance(payload, "bibliography")


async def _probe_dictionary_collation(client: BudgetCalHttpClient) -> None:
    result = await DictionaryCollationService(client).collate(DictionarySource.JASTROW, "705")
    payload = result.to_dict()
    _require_nonempty_list(payload, "entries", "dictionary_collation")
    _require_provenance(payload, "dictionary_collation")


async def _probe_external_citations(client: BudgetCalHttpClient) -> None:
    result = await ExternalCitationService(client).dialects()
    payload = result.to_dict()
    _require_nonempty_list(payload, "dialects", "external_citations")
    _require_provenance(payload, "external_citations")


async def _probe_targum(client: BudgetCalHttpClient) -> None:
    result = await TargumService(client).parallel("Gen", 1, 1)
    payload = result.to_dict()
    if payload.get("status") != "found":
        raise LiveSmokeSemanticError("Targum Gen 1:1 is no longer a found comparison")
    _require_provenance(payload, "targum")


async def _probe_syriac(client: BudgetCalHttpClient) -> None:
    result = await SyriacService(client).peshitta_parallel("Gen", 1, 1)
    payload = result.to_dict()
    if payload.get("status") != "found":
        raise LiveSmokeSemanticError("Peshitta Gen 1:1 is no longer a found comparison")
    _require_provenance(payload, "syriac")


DEFAULT_SMOKE_CASES = (
    SmokeCase("lexicon", _probe_lexicon),
    SmokeCase("text_search", _probe_text_search),
    SmokeCase("text_concordance", _probe_text_concordance),
    SmokeCase("bibliography", _probe_bibliography),
    SmokeCase("dictionary_collation", _probe_dictionary_collation),
    SmokeCase("external_citations", _probe_external_citations),
    SmokeCase("targum", _probe_targum),
    SmokeCase("syriac", _probe_syriac),
)


async def run_live_smoke(
    *,
    cases: tuple[SmokeCase, ...] = DEFAULT_SMOKE_CASES,
    client: BudgetCalHttpClient | None = None,
) -> LiveSmokeReport:
    """Run the fixed representative smoke cases sequentially with a hard request budget."""

    smoke_client = client or BudgetCalHttpClient()
    owns_client = client is None
    completed: list[str] = []
    try:
        for case in cases:
            try:
                await case.operation(smoke_client)
            except BaseException as exc:
                if isinstance(exc, asyncio.CancelledError):
                    raise
                raise LiveSmokeFailure(
                    case.name,
                    classify_smoke_exception(exc),
                    exc,
                ) from exc
            completed.append(case.name)
        return LiveSmokeReport(tuple(completed), smoke_client.request_count)
    finally:
        if owns_client:
            await smoke_client.aclose()


async def _async_main() -> None:
    report = await run_live_smoke()
    print(json.dumps(report.to_dict(), sort_keys=True))


def main() -> None:
    """Run the capped live smoke from the command line."""

    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
