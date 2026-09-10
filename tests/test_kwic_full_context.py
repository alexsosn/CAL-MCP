from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import ConcordanceParseError, ConcordanceService
from cal_mcp.release_surface import V01_PUBLIC_TOOLS

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
_RETRIEVED_AT = datetime(2026, 9, 10, tzinfo=UTC)


def _response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def _parser() -> Callable[..., object]:
    module = importlib.import_module("cal_mcp.concordance")
    parser = getattr(module, "parse_kwic_full_context_page", None)
    assert callable(parser), "concordance must expose parse_kwic_full_context_page"
    return cast(Callable[..., object], parser)


def _parse(
    response: CalResponse,
    *,
    file_id: str = "13250",
    subtext_id: str | None = None,
    target_coordinate: str = "1325003",
    charset: str = "R",
) -> object:
    return _parser()(
        response,
        requested_file_id=file_id,
        requested_subtext_id=subtext_id,
        requested_target_coordinate=target_coordinate,
        requested_charset=charset,
    )


def _roman_url(*, target: str = "1325003", file_id: str = "13250") -> str:
    return (
        "https://cal.huc.edu/get_a_kwicchapter.php?"
        f"file={file_id}&sub=&cset=R&target={target}"
    )


def test_roman_full_context_preserves_rows_tokens_and_target_relationship() -> None:
    page = _parse(
        _response("kwic_full_context_tel_dan_roman.html", _roman_url())
    )

    assert getattr(page, "status").value == "found"
    lines = getattr(page, "lines")
    assert [line.coordinate for line in lines] == ["1325002", "1325003", "1325004"]
    target = lines[1]
    assert target.display_coordinate == "03"
    assert target.text == "wy$kb )by yhk"
    assert [(token.word_index, token.text) for token in target.tokens] == [
        (0, "wy$kb"),
        (2, ")by"),
        (4, "yhk"),
    ]
    assert target.tokens[0].lexical_url == (
        "https://cal.huc.edu/getlex.php?coord=1325003&word=0&hasvariant=0"
    )
    assert target.comment_url == "https://cal.huc.edu/comment.php?coord=1325003"


def test_hebrew_terminal_empty_lexical_anchor_is_validated_but_not_exposed() -> None:
    url = "https://cal.huc.edu/get_a_kwicchapter.php?file=13250&sub=&cset=H&target=1325003"
    page = _parse(
        _response("kwic_full_context_tel_dan_hebrew.html", url),
        charset="H",
    )

    assert getattr(page, "status").value == "found"
    line = getattr(page, "lines")[0]
    assert line.text == "וישכב * אבי"
    assert [(token.word_index, token.text) for token in line.tokens] == [
        (0, "וישכב"),
        (1, "*"),
        (2, "אבי"),
    ]


@pytest.mark.parametrize(
    "body_change",
    [
        ('word=3&amp;hasvariant=0\"></a>', 'word=3&amp;hasvariant=0\"></a> <a href="getlex.php?coord=1325003&amp;word=4&amp;hasvariant=0"></a>'),
        ('word=3&amp;hasvariant=0\"></a>', 'word=1&amp;hasvariant=0\"></a>'),
        ('word=3&amp;hasvariant=0\"></a></td>', 'word=3&amp;hasvariant=0\"></a> <a href="getlex.php?coord=1325003&amp;word=4&amp;hasvariant=0">tail</a></td>'),
    ],
)
def test_malformed_hebrew_empty_lexical_anchor_is_parser_drift(body_change: tuple[str, str]) -> None:
    body = (FIXTURES / "kwic_full_context_tel_dan_hebrew.html").read_text()
    old, new = body_change
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/get_a_kwicchapter.php?file=13250&sub=&cset=H&target=1325003",
        body=body.replace(old, new, 1).encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )

    with pytest.raises(ConcordanceParseError):
        _parse(response, charset="H")


def test_non_hebrew_empty_lexical_anchor_is_parser_drift() -> None:
    body = (FIXTURES / "kwic_full_context_tel_dan_roman.html").read_text().replace(
        "</td></tr>\n<tr><td><a href=\"comment.php?coord=1325004\">",
        '<a href="getlex.php?coord=1325003&amp;word=5&amp;hasvariant=0"></a></td></tr>\n'
        '<tr><td><a href="comment.php?coord=1325004">',
        1,
    )
    response = CalResponse(
        status_code=200,
        url=_roman_url(),
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )

    with pytest.raises(ConcordanceParseError):
        _parse(response)


def test_matching_target_not_found_marker_is_typed_empty_result() -> None:
    target = "999999999999"
    page = _parse(
        _response("kwic_full_context_not_found.html", _roman_url(target=target)),
        target_coordinate=target,
    )

    assert getattr(page, "status").value == "not_found"
    assert getattr(page, "lines") == ()


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/get_a_kwicchapter.php?file=13250&sub=&cset=R&target=1325003",
        "https://cal.huc.edu/get_a_chapter.php?file=13250&sub=&cset=R&target=1325003",
        "https://cal.huc.edu/get_a_kwicchapter.php?file=99999&sub=&cset=R&target=1325003",
        "https://cal.huc.edu/get_a_kwicchapter.php?file=13250&sub=&cset=H&target=1325003",
        "https://cal.huc.edu/get_a_kwicchapter.php?file=13250&sub=&cset=R&target=1325003&target=1325004",
        "https://cal.huc.edu/get_a_kwicchapter.php?file=13250&sub=&cset=R&target=1325003&variants=0",
    ],
)
def test_response_route_and_selectors_must_match_request(url: str) -> None:
    response = _response("kwic_full_context_tel_dan_roman.html", url)

    with pytest.raises(ConcordanceParseError):
        _parse(response)


def test_missing_or_duplicate_requested_target_is_parser_drift() -> None:
    response = _response("kwic_full_context_tel_dan_roman.html", _roman_url(target="1325999"))
    with pytest.raises(ConcordanceParseError):
        _parse(response, target_coordinate="1325999")

    body = (FIXTURES / "kwic_full_context_tel_dan_roman.html").read_text().replace(
        "coord=1325004",
        "coord=1325003",
    )
    duplicate = CalResponse(
        status_code=200,
        url=_roman_url(),
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )
    with pytest.raises(ConcordanceParseError):
        _parse(duplicate)


def test_not_found_marker_cannot_contradict_rows_or_requested_target() -> None:
    roman = (FIXTURES / "kwic_full_context_tel_dan_roman.html").read_text()
    mixed = CalResponse(
        status_code=200,
        url=_roman_url(),
        body=roman.replace(
            "</body>",
            "<div>Target coordinate 1325003 not found.</div></body>",
        ).encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )
    with pytest.raises(ConcordanceParseError):
        _parse(mixed)

    wrong_marker = _response("kwic_full_context_not_found.html", _roman_url(target="1325003"))
    with pytest.raises(ConcordanceParseError):
        _parse(wrong_marker)


class RecordingTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_service_consumes_kwic_hit_selectors_with_exactly_one_request() -> None:
    response = _response("kwic_full_context_tel_dan_roman.html", _roman_url())
    transport = RecordingTransport(response)
    service = ConcordanceService(CalHttpClient(transport=transport))
    method = getattr(service, "kwic_full_context", None)
    assert callable(method), "ConcordanceService must expose kwic_full_context"

    result = await method("13250", "1325003", "R")

    assert result.status.value == "found"
    assert result.file_id == "13250"
    assert result.subtext_id is None
    assert result.target_coordinate == "1325003"
    assert result.charset == "R"
    assert result.provenance.operation == "kwic_full_context"
    assert result.provenance.text_id == "13250"
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_kwicchapter.php",
            params=(
                ("file", "13250"),
                ("sub", ""),
                ("cset", "R"),
                ("target", "1325003"),
            ),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        (("x", "1325003", "R"), {}),
        (("13250", "target", "R"), {}),
        (("13250", "1325003", "X"), {}),
        (("13250", "1325003", "roman"), {}),
        (("13250", "1325003", "R"), {"subtext_id": "bad"}),
    ],
)
async def test_invalid_full_context_selectors_fail_before_transport(
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> None:
    transport = RecordingTransport(
        _response("kwic_full_context_tel_dan_roman.html", _roman_url())
    )
    service = ConcordanceService(CalHttpClient(transport=transport))
    method = getattr(service, "kwic_full_context", None)
    assert callable(method), "ConcordanceService must expose kwic_full_context"

    with pytest.raises(ValueError):
        await method(*args, **kwargs)

    assert transport.requests == []


def test_v01_release_manifest_includes_explicit_full_context_tool() -> None:
    assert "cal_kwic_full_context" in V01_PUBLIC_TOOLS
    assert len(V01_PUBLIC_TOOLS) == 31


@pytest.mark.anyio
async def test_mcp_registry_exposes_typed_full_context_without_url_input() -> None:
    server_module = importlib.import_module("cal_mcp.server")
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert "cal_kwic_full_context" in tools
    schema = tools["cal_kwic_full_context"].inputSchema
    properties = schema.get("properties", {})
    assert set(properties) == {"file_id", "target_coordinate", "charset", "subtext_id"}
    assert "full_context_url" not in properties
