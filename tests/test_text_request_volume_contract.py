from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextService

ROOT = Path(__file__).resolve().parents[1]
TEXT_DOCS = ROOT / "docs" / "tools" / "texts.md"
_RETRIEVED_AT = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
_INFORMATION_BODY = b"""<html><body>
<h1>Text Information</h1>
<p>Ephrem Hymns on Paradise</p>
<p>Beck / CSCO edition information</p>
</body></html>"""


@pytest.mark.anyio
async def test_text_information_public_description_is_cache_aware() -> None:
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    description = tools["cal_text_information"].description or ""
    lowered = description.lower()
    assert "at most one new logical cal request" in lowered
    assert "completed" in lowered and "cache hit" in lowered
    assert "no new upstream i/o" in lowered
    assert "follows no metadata links" in lowered


def test_text_tool_docs_distinguish_request_identity_cache_and_single_flight() -> None:
    docs = TEXT_DOCS.read_text(encoding="utf-8")
    lowered = docs.lower()

    assert "at most one new logical cal request" in lowered
    assert "completed cache hit" in lowered
    assert "zero new upstream i/o" in lowered
    assert "single-flight" in lowered
    assert "bounded retry" in lowered
    assert "every public text tool performs exactly one user-initiated cal request" not in lowered


class InformationTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        coord = dict(request.params)["coord"]
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/get_file_info.php?coord={coord}",
            body=_INFORMATION_BODY,
            content_type="text/html; charset=UTF-8",
            retrieved_at=_RETRIEVED_AT,
        )


@pytest.mark.anyio
async def test_identical_text_information_calls_reuse_shared_client_cache() -> None:
    transport = InformationTransport()
    client = CalHttpClient(transport=transport)
    service = TextService(client)

    first = await service.information("6042013")
    second = await service.information("6042013")

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_file_info.php",
            params=(("coord", "6042013"),),
        )
    ]
    assert second == first
    assert second.provenance.retrieved_at == _RETRIEVED_AT
    assert second.provenance.source_url == first.provenance.source_url
