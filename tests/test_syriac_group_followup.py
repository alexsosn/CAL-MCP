from __future__ import annotations

import importlib
import socket
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.syriac import SyriacParseError, SyriacService, SyriacTextNavigationKind

RETRIEVED_AT = datetime(2026, 9, 9, 18, 0, tzinfo=UTC)
GROUP_ID = "60420"
GROUP_URL = f"https://cal.huc.edu/showsubtexts.php?keyword={GROUP_ID}"

_GROUP_BODY = """
<!doctype html>
<html><body>
  <h1>Select a Text</h1>
  <ul>
    <li><a href="/get_a_chapter.php?file=70001&amp;cset=S">70001</a> Direct child
        <a href="/get_file_info.php?coord=70001">ⓘ</a></li>
    <li><a href="/showsubtexts.php?keyword=70002">70002</a> Nested group</li>
    <li><a href="/showsubtexts.php?subtext=70003&amp;cset=S">70003</a> Child catalogue</li>
  </ul>
</body></html>
"""


class RecordingTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


def _response(body: str = _GROUP_BODY, url: str = GROUP_URL) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _group_method(service: SyriacService) -> Callable[[object], Awaitable[Any]]:
    method = getattr(service, "group", None)
    assert callable(method), "SyriacService.group must expose returned GROUP selectors"
    return cast(Callable[[object], Awaitable[Any]], method)


@pytest.mark.anyio
async def test_group_followup_uses_exact_keyword_request_and_preserves_child_navigation() -> None:
    transport = RecordingTransport(_response())
    service = SyriacService(CalHttpClient(transport=transport))

    result = await _group_method(service)(GROUP_ID)

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="showsubtexts.php",
            params=(("keyword", GROUP_ID),),
        )
    ]
    assert result.group_id == GROUP_ID
    assert [(item.upstream_id, item.label, item.navigation_kind) for item in result.items] == [
        ("70001", "Direct child", SyriacTextNavigationKind.TEXT),
        ("70002", "Nested group", SyriacTextNavigationKind.GROUP),
        ("70003", "Child catalogue", SyriacTextNavigationKind.CATALOGUE),
    ]
    assert result.items[0].info_url == "https://cal.huc.edu/get_file_info.php?coord=70001"
    assert result.provenance.operation == "syriac_group"
    assert result.provenance.group_id == GROUP_ID
    assert result.provenance.source_url == GROUP_URL


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", ["", "abc", "0", "-1", " 60420", 60420, None])
async def test_invalid_group_identifiers_fail_before_transport(group_id: object) -> None:
    transport = RecordingTransport(_response())
    service = SyriacService(CalHttpClient(transport=transport))

    with pytest.raises(ValueError):
        await _group_method(service)(group_id)

    assert transport.requests == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "url",
    [
        "https://cal.huc.edu/show_Syriac_categories.php?keyword=60420",
        "https://cal.huc.edu/showsubtexts.php?keyword=63400",
        "https://cal.huc.edu/showsubtexts.php?keyword=60420&keyword=63400",
        "https://cal.huc.edu/showsubtexts.php?keyword=60420&cset=S",
        "https://cal.huc.edu/showsubtexts.php?subtext=60420",
    ],
)
async def test_group_followup_rejects_response_route_or_selector_contradictions(url: str) -> None:
    transport = RecordingTransport(_response(url=url))
    service = SyriacService(CalHttpClient(transport=transport))

    with pytest.raises(SyriacParseError):
        await _group_method(service)(GROUP_ID)

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="showsubtexts.php",
            params=(("keyword", GROUP_ID),),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        "<h1>Select a Text</h1><p>No recognizable child rows</p>",
        (
            '<a href="https://example.org/get_a_chapter.php?file=70001">70001</a> foreign'
        ),
        (
            '<a href="/showsubtexts.php?keyword=70002&amp;subtext=70003">70002</a> ambiguous'
        ),
        (
            '<p><a href="/get_a_chapter.php?file=70001">70001</a> first</p>'
            '<p><a href="/get_a_chapter.php?file=70001">70001</a> duplicate</p>'
        ),
        (
            '<p><a href="/get_a_chapter.php?file=70001">70001</a> direct '
            '<a href="/get_file_info.php?coord=99999">ⓘ</a></p>'
        ),
    ],
)
async def test_group_followup_fails_closed_on_unusable_child_navigation(body: str) -> None:
    transport = RecordingTransport(_response(body=body))
    service = SyriacService(CalHttpClient(transport=transport))

    with pytest.raises(SyriacParseError):
        await _group_method(service)(GROUP_ID)

    assert len(transport.requests) == 1


@pytest.mark.anyio
async def test_group_mcp_schema_is_bounded_and_private_route_controls_stay_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("MCP introspection must remain offline")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert "cal_syriac_group" in tools
    tool = tools["cal_syriac_group"]
    properties = tool.inputSchema.get("properties", {})
    assert set(properties) == {"group_id"}
    description = " ".join((tool.description or "").lower().split())
    assert "returned" in description and "group" in description
    assert "at most one new logical cal request" in description
    assert "cache hit" in description and "no new upstream i/o" in description
    for private_name in ("keyword", "cset", "script", "file", "subtext", "url"):
        assert private_name not in properties


def test_server_instructions_name_the_explicit_syriac_group_followup() -> None:
    source = (importlib.import_module("cal_mcp.server").__file__ or "")
    assert source
    text = open(source, encoding="utf-8").read()
    instructions = text.split("instructions=(", 1)[1].split("version=__version__", 1)[0]

    assert "cal_syriac_group" in instructions
