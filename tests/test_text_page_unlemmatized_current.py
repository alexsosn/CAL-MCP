"""Issue #185: current CAL text pages with plain/unlemmatized two-cell rows."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageResult, TextParseError, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
MANDAIC = FIXTURES / "text_page_plain_mandaic_74420_structural.html"
CPA = FIXTURES / "text_page_plain_cpa_55430_structural.html"
PHILEMON = FIXTURES / "text_page_philemon_62057_current.html"


class FixtureTransport:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        query = "&".join(f"{name}={value}" for name, value in request.params)
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/{request.path}?{query}",
            body=self.body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 28, tzinfo=UTC),
        )


async def _page(body: bytes, file_id: str) -> tuple[TextPageResult, list[CalRequest]]:
    transport = FixtureTransport(body)
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page(file_id)
    finally:
        await client.aclose()
    return result, transport.requests


@pytest.mark.anyio
async def test_plain_mandaic_rows_keep_text_and_nullable_comment_coordinate() -> None:
    result, requests = await _page(MANDAIC.read_bytes(), "74420")

    assert result.page is not None
    first, second = result.page.lines
    assert first.coordinate is None
    assert first.display_coordinate == "par. 104"
    assert first.text == "fixture plain Mandaic text one"
    assert first.tokens == ()
    assert first.empty_word_indexes == ()
    assert first.comment_url is None

    assert second.coordinate == "744202129"
    assert second.display_coordinate == "par. 129"
    assert second.text == "fixture plain Mandaic text two"
    assert second.tokens == ()
    assert second.empty_word_indexes == ()
    assert second.comment_url == "https://cal.huc.edu/comment.php?coord=744202129"

    structured = result.to_dict()
    assert structured["page"]["lines"][0]["coordinate"] is None
    assert structured["page"]["lines"][1]["coordinate"] == "744202129"

    assert requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74420")),
        )
    ]


@pytest.mark.anyio
async def test_plain_cpa_row_keeps_nested_span_text_without_tokenizing() -> None:
    result, requests = await _page(CPA.read_bytes(), "55430")

    assert result.page is not None
    [line] = result.page.lines
    assert line.coordinate is None
    assert line.display_coordinate == "187:03"
    assert line.text == "fixture plain CPA text"
    assert line.tokens == ()
    assert line.empty_word_indexes == ()
    assert line.comment_url is None
    assert requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("file", "55430"), ("cset", "C"), ("page", "0")),
        )
    ]


@pytest.mark.anyio
async def test_existing_linked_page_remains_tokenized() -> None:
    result, _requests = await _page(PHILEMON.read_bytes(), "62057")

    assert result.page is not None
    assert all(line.coordinate is not None for line in result.page.lines)
    assert all(line.tokens for line in result.page.lines)
    assert result.page.lines[0].coordinate == "620570101"


@pytest.mark.anyio
async def test_mixed_linked_and_plain_rows_fail_closed() -> None:
    body = MANDAIC.read_text(encoding="utf-8").replace(
        "fixture plain Mandaic text two",
        '<a href="getlex.php?coord=744202129&word=0&hasvariant=0">fixture-token</a>',
        1,
    )
    with pytest.raises(TextParseError, match="linked.*plain|plain.*linked"):
        await _page(body.encode(), "74420")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("<td>par. 104</td>", "<td></td>", "plain.*display|display.*plain"),
        (
            "<td>fixture plain Mandaic text one</td>",
            "<td></td>",
            "plain.*text|text.*plain",
        ),
        (
            "<td>fixture plain Mandaic text one</td>",
            '<td><a href="oneentry.php?lemma=x+N">fixture</a></td>',
            "plain.*link|link.*plain",
        ),
        (
            "<td>par. 104</td>",
            '<td><a href="oneentry.php?lemma=x+N">par. 104</a></td>',
            "plain.*coordinate|coordinate.*plain",
        ),
        (
            'href="comment.php?coord=744202129"',
            'href="comment.php?coord=744202129&extra=1"',
            "selector|plain",
        ),
        (
            'href="comment.php?coord=744202129"',
            'href="comment.php?coord=not-decimal"',
            "coordinate|plain",
        ),
        (
            'href="comment.php?coord=744202129"',
            'href="comment.php?coord=999999"',
            "requested text|identity|prefix",
        ),
        (
            '<td><a href="comment.php?coord=744202129">par. 129</a></td>',
            '<td>extra <a href="comment.php?coord=744202129">par. 129</a></td>',
            "outside|loose|plain",
        ),
        (
            '<td><a href="comment.php?coord=744202129">par. 129</a></td>',
            '<td><a href="comment.php?coord=744202129">par. 129</a>'
            '<a href="comment.php?coord=744202129">again</a></td>',
            "multiple|exactly one|plain",
        ),
        (
            "<tr><td>par. 104</td><td>fixture plain Mandaic text one</td></tr>",
            "<tr><td>par. 104</td><td>fixture plain Mandaic text one</td><td>extra</td></tr>",
            "two cells",
        ),
    ],
)
async def test_malformed_plain_rows_fail_closed(old: str, new: str, message: str) -> None:
    body = MANDAIC.read_text(encoding="utf-8")
    assert old in body
    with pytest.raises(TextParseError, match=message):
        await _page(body.replace(old, new, 1).encode(), "74420")


@pytest.mark.anyio
async def test_empty_text_display_shell_is_not_plain_success() -> None:
    body = (
        '<html><body><a href="/get_file_info.php?coord=55002">55002: fixture</a>'
        '<table class="text-display"><tr><bdo dir="rtl"></bdo></tr></table>'
        "</body></html>"
    )
    with pytest.raises(TextParseError, match="no recognizable|no .*rows|empty"):
        await _page(body.encode(), "55002")
