from __future__ import annotations

import importlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.release_surface import V01_PUBLIC_TOOLS
from cal_mcp.texts import TextParseError, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
_RETRIEVED_AT = datetime(2026, 9, 10, tzinfo=UTC)
_COORDINATE = "8100110821"
_SOURCE_URL = f"https://cal.huc.edu/comment.php?coord={_COORDINATE}"
_ENTRY_HREF = "/oneentry.php?lemma=qbl+V&amp;cits=all"


class _StatusView(Protocol):
    value: str


class _RecordView(Protocol):
    reference: str
    source_text: str | None
    translation: str | None
    lemma_key: str
    headword: str
    part_of_speech: str | None
    gloss: str | None
    entry_url: str


class _PageView(Protocol):
    status: _StatusView
    records: tuple[_RecordView, ...]


class _ProvenanceView(Protocol):
    source: str
    source_url: str
    operation: str
    upstream_id: str | None


class _ResultView(Protocol):
    status: _StatusView
    coordinate: str
    records: tuple[_RecordView, ...]
    provenance: _ProvenanceView


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _response(
    name: str,
    *,
    url: str = _SOURCE_URL,
    body: str | None = None,
) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(body if body is not None else _fixture(name)).encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def _parser() -> Callable[..., object]:
    module = importlib.import_module("cal_mcp.texts")
    parser = getattr(module, "parse_text_line_comments_page", None)
    assert callable(parser), "texts must expose parse_text_line_comments_page"
    return cast(Callable[..., object], parser)


def _parse(response: CalResponse, *, coordinate: str = _COORDINATE) -> _PageView:
    result = _parser()(response, requested_coordinate=coordinate)
    return cast(_PageView, result)


def _service_method(service: TextService) -> Callable[..., Awaitable[_ResultView]]:
    method = getattr(service, "line_comments", None)
    assert callable(method), "TextService must expose line_comments"
    return cast(Callable[..., Awaitable[_ResultView]], method)


def test_found_line_comments_preserve_order_and_record_fields() -> None:
    page = _parse(_response("text_line_comments_pj_gen8_21.html"))

    assert page.status.value == "found"
    assert len(page.records) == 2

    first, second = page.records
    assert first.reference == "PJ Gen8:21"
    assert first.source_text == "וקבל ייי ברעוא קורבניה"
    assert first.translation is None
    assert first.lemma_key == "qbl V"
    assert first.headword == "qbl"
    assert first.part_of_speech == "vb."
    assert first.gloss == "to be opposed; D to receive"
    assert first.entry_url == "https://cal.huc.edu/oneentry.php?lemma=qbl+V&cits=all"

    assert second.reference == "PJ Gen8:21"
    assert second.source_text == "לא אוסיף למילט תוב ית ארעא"
    assert second.translation == "I shall not again curse the earth any more"
    assert second.lemma_key == "twb X"
    assert second.headword == "tūḇ"
    assert second.part_of_speech == "adv."
    assert second.gloss == "again"


def test_explicit_no_citations_marker_is_typed_empty_state() -> None:
    coordinate = "999999999999"
    page = _parse(
        _response(
            "text_line_comments_none.html",
            url=f"https://cal.huc.edu/comment.php?coord={coordinate}",
        ),
        coordinate=coordinate,
    )

    assert page.status.value == "no_citations"
    assert page.records == ()


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/comment.php?coord=8100110821",
        "https://cal.huc.edu/get_a_chapter.php?coord=8100110821",
        "https://cal.huc.edu/comment.php",
        "https://cal.huc.edu/comment.php?coord=999",
        "https://cal.huc.edu/comment.php?coord=8100110821&coord=8100110822",
        "https://cal.huc.edu/comment.php?coord=8100110821&extra=1",
        "https://cal.huc.edu/comment.php?coord=8100110821#fragment",
    ],
)
def test_response_route_and_coordinate_identity_fail_closed(url: str) -> None:
    with pytest.raises(TextParseError):
        _parse(_response("text_line_comments_pj_gen8_21.html", url=url))


@pytest.mark.parametrize(
    "body",
    [
        _fixture("text_line_comments_pj_gen8_21.html").replace(
            "<title>CAL: citations and comments for 8100110821</title>",
            "",
        ),
        _fixture("text_line_comments_pj_gen8_21.html").replace(
            "8100110821</title>",
            "999</title>",
        ),
        _fixture("text_line_comments_pj_gen8_21.html").replace(
            "</title>",
            "</title><title>CAL: citations and comments for 8100110821</title>",
            1,
        ),
    ],
)
def test_title_must_uniquely_identify_requested_coordinate(body: str) -> None:
    with pytest.raises(TextParseError):
        _parse(_response("text_line_comments_pj_gen8_21.html", body=body))


def test_marker_cannot_be_mixed_with_records_or_unknown_summary_content() -> None:
    found = _fixture("text_line_comments_pj_gen8_21.html")
    mixed = found.replace(
        '<div class="summary-card">',
        '<div class="summary-card"><p>NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED</p>',
        1,
    )
    with pytest.raises(TextParseError):
        _parse(_response("text_line_comments_pj_gen8_21.html", body=mixed))

    unknown = found.replace(
        '<div class="summary-card">',
        '<div class="summary-card"><p>unexpected replacement content</p>',
        1,
    )
    with pytest.raises(TextParseError):
        _parse(_response("text_line_comments_pj_gen8_21.html", body=unknown))

    empty = _fixture("text_line_comments_none.html")
    repeated = empty.replace(
        "</div>",
        "<p>NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED</p></div>",
        1,
    )
    coordinate = "999999999999"
    with pytest.raises(TextParseError):
        _parse(
            _response(
                "text_line_comments_none.html",
                url=f"https://cal.huc.edu/comment.php?coord={coordinate}",
                body=repeated,
            ),
            coordinate=coordinate,
        )


@pytest.mark.parametrize(
    "replacement",
    [
        "https://example.org/oneentry.php?lemma=qbl+V&amp;cits=all",
        "/cal_entry_web.php?lemma=qbl+V&amp;cits=all",
        "/oneentry.php?cits=all",
        "/oneentry.php?lemma=&amp;cits=all",
        "/oneentry.php?lemma=qbl+V&amp;lemma=twb+X&amp;cits=all",
        "/oneentry.php?lemma=not-a-key&amp;cits=all",
        "/oneentry.php?lemma=qbl+V",
        "/oneentry.php?lemma=qbl+V&amp;cits=one",
        "/oneentry.php?lemma=qbl+V&amp;cits=all&amp;extra=1",
        "/oneentry.php?lemma=qbl+V&amp;cits=all#fragment",
    ],
)
def test_lexical_entry_link_identity_fails_closed(replacement: str) -> None:
    body = _fixture("text_line_comments_pj_gen8_21.html").replace(_ENTRY_HREF, replacement, 1)

    with pytest.raises(TextParseError):
        _parse(_response("text_line_comments_pj_gen8_21.html", body=body))


class RecordingTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_service_accepts_current_alphanumeric_coordinate_and_makes_one_request() -> None:
    coordinate = "444015370A04"
    body = _fixture("text_line_comments_none.html").replace("999999999999", coordinate)
    source_url = f"https://cal.huc.edu/comment.php?coord={coordinate}"
    transport = RecordingTransport(
        _response("text_line_comments_none.html", url=source_url, body=body)
    )
    service = TextService(CalHttpClient(transport=transport))

    result = await _service_method(service)(coordinate)

    assert result.status.value == "no_citations"
    assert result.coordinate == coordinate
    assert result.records == ()
    assert result.provenance.source == "CAL"
    assert result.provenance.source_url == source_url
    assert result.provenance.operation == "line_comments"
    assert result.provenance.upstream_id == coordinate
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="comment.php",
            params=(("coord", coordinate),),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "coordinate",
    [
        "",
        " ",
        "8100 110821",
        "8100110821?x=1",
        "../8100110821",
        "אבג",
        "A" * 65,
    ],
)
async def test_invalid_public_coordinates_fail_before_transport(coordinate: str) -> None:
    transport = RecordingTransport(_response("text_line_comments_pj_gen8_21.html"))
    service = TextService(CalHttpClient(transport=transport))

    with pytest.raises(ValueError):
        await _service_method(service)(coordinate)

    assert transport.requests == []


def test_release_manifest_includes_line_comments_tool() -> None:
    assert "cal_text_line_comments" in V01_PUBLIC_TOOLS
    assert len(V01_PUBLIC_TOOLS) == 32


@pytest.mark.anyio
async def test_mcp_registry_exposes_coordinate_only_without_url_input() -> None:
    server_module = importlib.import_module("cal_mcp.server")
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert "cal_text_line_comments" in tools
    schema = tools["cal_text_line_comments"].model_dump(by_alias=True)["inputSchema"]
    properties = schema.get("properties", {})
    assert set(properties) == {"coordinate"}
    assert "comment_url" not in properties
