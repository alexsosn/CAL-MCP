from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime
from typing import Any

import pytest
from mcp import Client

import cal_mcp.texts as texts_module
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextParseError, TextService

_RETRIEVED_AT = datetime(2026, 9, 9, tzinfo=UTC)
_VALID_BODY = b"""<html><body>
<h1>Text Information</h1>
<p>Ephrem Hymns on Paradise</p>
<p>Beck / CSCO edition information</p>
<p>CAL corrections are ongoing</p>
<p>Transcription and vocalization warning</p>
</body></html>"""
_HATRAN_BODY = b"""<html><body>
<h1>Text Information</h1>
<p>Hatran Texts</p>
<p>H 336</p>
<p>Corpus-level editorial note</p>
<p>Item and findspot note</p>
<p>Bibliography note</p>
</body></html>"""


def _response(body: bytes, url: str = "https://cal.huc.edu/get_file_info.php?coord=6042013") -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def _parser() -> Any:
    parser = getattr(texts_module, "parse_text_information_page", None)
    assert callable(parser), "text-information parser is not implemented"
    return parser


def test_text_information_parser_preserves_ordered_metadata() -> None:
    page = _parser()(_response(_VALID_BODY))

    assert page.metadata == (
        "Ephrem Hymns on Paradise",
        "Beck / CSCO edition information",
        "CAL corrections are ongoing",
        "Transcription and vocalization warning",
    )


def test_text_information_heading_without_metadata_fails_closed() -> None:
    response = _response(b"<html><body><h1>Text Information</h1></body></html>")

    with pytest.raises(TextParseError):
        _parser()(response)


def test_text_information_anti_scrape_page_fails_closed() -> None:
    response = _response(
        b"<html><body><h1>The Comprehensive Aramaic Lexicon</h1>"
        b"<p>Please do not try to scrape our site.</p></body></html>"
    )

    with pytest.raises(TextParseError):
        _parser()(response)


def test_text_information_unrelated_success_html_fails_closed() -> None:
    response = _response(b"<html><body><h1>CAL</h1><p>changed upstream markup</p></body></html>")

    with pytest.raises(TextParseError):
        _parser()(response)


class InformationTransport:
    def __init__(self, body: bytes = _VALID_BODY) -> None:
        self.body = body
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        coord = dict(request.params).get("coord", "missing")
        body = _HATRAN_BODY if coord == "43200336" else self.body
        return _response(self.body if coord != "43200336" else body, f"https://cal.huc.edu/get_file_info.php?coord={coord}")


def _information_method(service: TextService) -> Any:
    method = getattr(service, "information", None)
    assert callable(method), "text-information service operation is not implemented"
    return method


@pytest.mark.anyio
async def test_text_information_direct_selector_uses_one_request_and_provenance() -> None:
    transport = InformationTransport()
    service = TextService(CalHttpClient(transport=transport))

    result = await _information_method(service)("6042013")

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_file_info.php",
            params=(("coord", "6042013"),),
        )
    ]
    assert result.file_id == "6042013"
    assert result.subtext_id is None
    assert result.metadata == (
        "Ephrem Hymns on Paradise",
        "Beck / CSCO edition information",
        "CAL corrections are ongoing",
        "Transcription and vocalization warning",
    )
    assert result.provenance.operation == "text_information"
    assert result.provenance.upstream_id == "6042013"
    assert result.provenance.subtext_id is None
    assert result.provenance.source_url.endswith("get_file_info.php?coord=6042013")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("file_id", "subtext_id", "expected_coord"),
    [
        ("43200", "336", "43200336"),
        ("56000", "128", "56000128"),
        ("06042", "013", "06042013"),
    ],
)
async def test_text_information_composes_subdivided_selector_as_exact_strings(
    file_id: str,
    subtext_id: str,
    expected_coord: str,
) -> None:
    transport = InformationTransport()
    service = TextService(CalHttpClient(transport=transport))

    result = await _information_method(service)(file_id, subtext_id=subtext_id)

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_file_info.php",
            params=(("coord", expected_coord),),
        )
    ]
    assert result.file_id == file_id
    assert result.subtext_id == subtext_id
    assert result.provenance.upstream_id == file_id
    assert result.provenance.subtext_id == subtext_id


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("file_id", "subtext_id"),
    [
        ("", None),
        ("abc", None),
        ("../1", None),
        ("60420", ""),
        ("60420", "x"),
        ("60420", "../1"),
    ],
)
async def test_invalid_text_information_identifiers_fail_before_transport(
    file_id: str,
    subtext_id: str | None,
) -> None:
    transport = InformationTransport()
    service = TextService(CalHttpClient(transport=transport))

    with pytest.raises(ValueError):
        await _information_method(service)(file_id, subtext_id=subtext_id)

    assert transport.requests == []


@pytest.mark.anyio
async def test_text_information_is_discoverable_without_private_selector_escape_hatches() -> None:
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert "cal_text_information" in tools
    schema = tools["cal_text_information"].input_schema
    assert set(schema["properties"]) == {"file_id", "subtext_id"}
    assert schema["required"] == ["file_id"]
    encoded = str(schema).lower()
    for forbidden in ("coord", "url", "page", "recursive", "fetch_all"):
        assert forbidden not in encoded
