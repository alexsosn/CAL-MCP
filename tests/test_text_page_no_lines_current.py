"""Issue #196: current explicit no-lines page with inline variant toggle."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextParseError, TextService, parse_text_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
CURRENT = FIXTURES / "text_page_cpa_55002_no_lines_current.html"
LEGACY = FIXTURES / "text_page_missing.html"
FOUND = FIXTURES / "text_page_philemon_62057_current.html"
RETRIEVED_AT = datetime(2026, 9, 29, tzinfo=UTC)


def _response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _current(body: str | None = None) -> CalResponse:
    return _response(
        CURRENT.read_text(encoding="utf-8") if body is None else body,
        "https://cal.huc.edu/get_a_chapter.php?file=55002&cset=C&page=0",
    )


def test_current_cpa_inline_toggle_no_lines_is_not_found() -> None:
    assert (
        parse_text_page(
            _current(),
            requested_file_id="55002",
            requested_subtext_id=None,
            requested_page=1,
        )
        is None
    )


def test_legacy_numeric_subtext_no_lines_stays_not_found() -> None:
    assert (
        parse_text_page(
            _response(
                LEGACY.read_text(encoding="utf-8"),
                "https://cal.huc.edu/get_a_chapter.php?file=13250&sub=999",
            ),
            requested_file_id="13250",
            requested_subtext_id="999",
        )
        is None
    )


class StaticTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_service_serializes_current_cpa_no_lines_as_not_found() -> None:
    transport = StaticTransport(_current())
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("55002", page=1)
    finally:
        await client.aclose()

    assert result.status.value == "not_found"
    assert result.page is None
    assert result.to_dict()["page"] is None
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("file", "55002"), ("cset", "C"), ("page", "0")),
        )
    ]


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            "NO LINES FOR 55002 ARE CURRENTLY STORED",
            "NO LINES FOR 55003 ARE CURRENTLY STORED",
            "file|requested",
        ),
        (
            '<a href="get_a_chapter.php?file=55002&sub=&cset=C&variants=0">'
            "Hide manuscript variants</a>",
            "unexpected prefix ",
            "no recognizable|no .*rows|marker|drift",
        ),
        (
            "NO LINES FOR 55002 ARE CURRENTLY STORED",
            "NO LINES FOR 55002 ARE CURRENTLY STORED extra",
            "no recognizable|no .*rows|marker|drift",
        ),
    ],
)
def test_near_no_lines_shapes_fail_closed(old: str, new: str, message: str) -> None:
    body = CURRENT.read_text(encoding="utf-8")
    assert old in body
    with pytest.raises(TextParseError, match=message):
        parse_text_page(
            _current(body.replace(old, new, 1)),
            requested_file_id="55002",
            requested_subtext_id=None,
            requested_page=1,
        )


def test_repeated_exact_no_lines_markers_fail_closed() -> None:
    body = CURRENT.read_text(encoding="utf-8").replace(
        "</div>",
        "</div><div>NO LINES FOR 55002 ARE CURRENTLY STORED</div>",
        1,
    )
    with pytest.raises(TextParseError, match="no-lines|marker|repeated|multiple"):
        parse_text_page(
            _current(body),
            requested_file_id="55002",
            requested_subtext_id=None,
            requested_page=1,
        )


def test_normal_found_page_is_unchanged() -> None:
    page = parse_text_page(
        _response(
            FOUND.read_text(encoding="utf-8"),
            "https://cal.huc.edu/get_a_chapter.php?file=62057&page=0",
        ),
        requested_file_id="62057",
        requested_subtext_id=None,
        requested_page=1,
    )

    assert page is not None
    assert page.text.file_id == "62057"
    assert page.lines
    assert all(line.tokens for line in page.lines)
