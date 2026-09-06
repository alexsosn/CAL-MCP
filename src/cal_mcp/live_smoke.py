from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeVar
from unittest.mock import patch

from mcp import Client

from cal_mcp.client import (
    CalClientConfig,
    CalFetchResult,
    CalHttpClient,
    CalNetworkError,
    CalRequest,
    CalResponse,
    CalUpstreamError,
)

FailureKind = Literal["upstream_unavailable", "adapter_or_parser_drift"]
MAX_CAL_REQUESTS = 9
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class SmokeCase:
    tool_name: str
    arguments: dict[str, object]


SMOKE_CASES = (
    SmokeCase("cal_lexicon_lookup", {"query": "br", "lemma_key": "br N"}),
    SmokeCase("cal_text_search", {"query": "Tel Dan"}),
    SmokeCase("cal_text_concordance", {"text_id": "13250"}),
    SmokeCase("cal_bibliography_lemma", {"lemma_key": "cly V"}),
    SmokeCase("cal_dictionary_collation", {"source": "jastrow", "page": "705"}),
    SmokeCase("cal_external_citation_dialects", {}),
    SmokeCase("cal_targum_parallel", {"book": "Gen", "chapter": 1, "verse": 1}),
    SmokeCase("cal_syriac_peshitta_parallel", {"book": "Gen", "chapter": 1, "verse": 1}),
)


class SmokeFailure(RuntimeError):
    """A live-smoke result cannot be trusted as a successful CAL operation."""

    def __init__(
        self,
        kind: FailureKind,
        tool_name: str,
        message: str,
        *,
        request_count: int | None = None,
    ) -> None:
        self.kind = kind
        self.tool_name = tool_name
        self.request_count = request_count
        super().__init__(message)


class SmokeBudgetExceeded(RuntimeError):
    """The live smoke attempted to exceed its fixed CAL request budget."""


@dataclass(slots=True)
class RequestBudget:
    max_requests: int = MAX_CAL_REQUESTS
    request_count: int = 0

    def claim(self) -> None:
        if self.request_count >= self.max_requests:
            raise SmokeBudgetExceeded(
                f"CAL live-smoke request budget exceeded: {self.request_count + 1}>{self.max_requests}"
            )
        self.request_count += 1


def classify_fetch_failure(exc: BaseException) -> FailureKind:
    """Classify failures conservatively for release diagnostics."""
    if isinstance(exc, CalNetworkError):
        return "upstream_unavailable"
    if isinstance(exc, CalUpstreamError) and exc.status_code in {429, 500, 502, 503, 504}:
        return "upstream_unavailable"
    return "adapter_or_parser_drift"


def _result_text(result: object) -> str:
    parts: list[str] = []
    for item in getattr(result, "content", ()):
        text = getattr(item, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return " ".join(parts)


def validate_tool_result(
    tool_name: str,
    result: object,
    *,
    failure_kind: FailureKind = "adapter_or_parser_drift",
) -> None:
    """Reject MCP error values and success payloads without CAL provenance."""
    if bool(getattr(result, "is_error", False)):
        detail = _result_text(result) or f"MCP tool {tool_name} returned an error result"
        raise SmokeFailure(failure_kind, tool_name, detail)

    structured = getattr(result, "structured_content", None)
    if not isinstance(structured, dict):
        raise SmokeFailure(
            "adapter_or_parser_drift",
            tool_name,
            f"MCP tool {tool_name} returned no structured result",
        )
    provenance = structured.get("provenance")
    source_url = provenance.get("source_url") if isinstance(provenance, dict) else None
    if not isinstance(source_url, str) or not source_url.startswith("https://cal.huc.edu/"):
        raise SmokeFailure(
            "adapter_or_parser_drift",
            tool_name,
            f"MCP tool {tool_name} returned no CAL provenance",
        )


class BudgetCalHttpClient(CalHttpClient):
    """Production CAL client with release-smoke policy fixed to the researched bounds."""

    def __init__(self, *, max_requests: int = MAX_CAL_REQUESTS) -> None:
        super().__init__(
            config=CalClientConfig(
                max_concurrency=1,
                max_retries=0,
                cache_enabled=False,
            )
        )
        self.budget = RequestBudget(max_requests=max_requests)
        self.last_failure_kind: FailureKind | None = None

    async def fetch(
        self,
        request: CalRequest,
        *,
        parser: Callable[[CalResponse], T],
        cache_namespace: str,
    ) -> CalFetchResult[T]:
        self.budget.claim()
        try:
            return await super().fetch(
                request,
                parser=parser,
                cache_namespace=cache_namespace,
            )
        except BaseException as exc:
            self.last_failure_kind = classify_fetch_failure(exc)
            raise


@dataclass(frozen=True, slots=True)
class SmokeSummary:
    completed_tools: tuple[str, ...]
    request_count: int


async def run_live_smoke() -> SmokeSummary:
    """Run the fixed v0.1 public-tool smoke sequentially against live CAL."""
    import cal_mcp.server as server

    budget_client = BudgetCalHttpClient()
    completed: list[str] = []
    with patch.object(server, "CalHttpClient", return_value=budget_client):
        async with Client(server.mcp, raise_exceptions=True) as client:
            for case in SMOKE_CASES:
                budget_client.last_failure_kind = None
                try:
                    result = await client.call_tool(case.tool_name, case.arguments)
                    validate_tool_result(
                        case.tool_name,
                        result,
                        failure_kind=budget_client.last_failure_kind
                        or "adapter_or_parser_drift",
                    )
                except SmokeFailure as exc:
                    exc.request_count = budget_client.budget.request_count
                    raise
                except Exception as exc:
                    raise SmokeFailure(
                        budget_client.last_failure_kind or "adapter_or_parser_drift",
                        case.tool_name,
                        str(exc),
                        request_count=budget_client.budget.request_count,
                    ) from exc
                completed.append(case.tool_name)

    return SmokeSummary(
        completed_tools=tuple(completed),
        request_count=budget_client.budget.request_count,
    )


async def _async_main() -> None:
    try:
        summary = await run_live_smoke()
    except SmokeFailure as exc:
        request_count = "unknown" if exc.request_count is None else str(exc.request_count)
        print(
            f"SMOKE_FAILURE kind={exc.kind} tool={exc.tool_name} "
            f"TOTAL_CAL_REQUESTS={request_count}: {exc}"
        )
        raise
    print(
        f"SMOKE_OK tools={len(summary.completed_tools)} "
        f"TOTAL_CAL_REQUESTS={summary.request_count}"
    )


def main() -> None:
    """CLI entry for the opt-in/scheduled release drift smoke."""
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
