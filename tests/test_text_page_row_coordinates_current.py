"""Issue #182: display coordinate and comment link on CAL's table-layout text pages.

See docs/research/issue-182-text-row-coordinates.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageResult, TextParseError, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
SAMARITAN = FIXTURES / "text_page_samaritan_56000_112_current.html"
GINZA = FIXTURES / "text_page_ginza_right_001_current.html"
PHILEMON = FIXTURES / "text_page_philemon_62057_current.html"


class FixtureTransport:
    def __init__(self, body: bytes) -> None:
        self.body = body

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        query = "&".join(f"{name}={value}" for name, value in request.params)
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/get_a_chapter.php?{query}",
            body=self.body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )


async def _page(body: bytes, file_id: str, subtext_id: str | None = None) -> TextPageResult:
    client = CalHttpClient(transport=FixtureTransport(body))
    try:
        return await TextService(client).page(file_id, subtext_id=subtext_id)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_comment_link_rows_keep_display_coordinate_and_comment_url() -> None:
    result = await _page(SAMARITAN.read_bytes(), "56000", "112")

    assert result.page is not None
    first = result.page.lines[0]
    assert first.coordinate == "56000112010"
    assert first.display_coordinate == "Gen12:01)0("
    assert first.comment_url == "https://cal.huc.edu/comment.php?coord=56000112010"
    assert first.text.startswith("w)mr yhwh l)brM")
    assert [line.display_coordinate for line in result.page.lines] == [
        "Gen12:01)0(",
        "Gen12:02)0(",
    ]


@pytest.mark.anyio
async def test_plain_coordinate_rows_keep_display_coordinate_without_comment() -> None:
    result = await _page(GINZA.read_bytes(), "74410")

    assert result.page is not None
    assert [(line.display_coordinate, line.comment_url) for line in result.page.lines] == [
        ("001:01", None),
        ("001:02", None),
    ]
    assert result.page.lines[0].text == "mšaba marai bliba dakia"


@pytest.mark.anyio
async def test_ask_ai_link_is_not_part_of_the_display_coordinate() -> None:
    result = await _page(PHILEMON.read_bytes(), "62057")

    assert result.page is not None
    assert [line.display_coordinate for line in result.page.lines] == ["01", "02"]
    assert all("[ai]" not in line.text for line in result.page.lines)
    assert result.page.lines[0].tokens[0].text == "p.awlAws"


_SAM_ROW = '<tr><td valign="top"><a href="comment.php?coord=56000112010"'
_SAM_TOKENS = '<td><a href="getlex.php?coord=56000112010&word=0&hasvariant=0">w)mr</a>'


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        # Comment link for a different line.
        (
            'href="comment.php?coord=56000112010"',
            'href="comment.php?coord=56000112020"',
            "comment",
        ),
        # An unknown link in the coordinate cell.
        (
            'href="comment.php?coord=56000112010"',
            'href="oneentry.php?lemma=)mr+V"',
            "coordinate cell",
        ),
        # A third cell in a text row.
        (_SAM_TOKENS, "<td>extra</td>" + _SAM_TOKENS, "two cells"),
        # A lexical link inside the coordinate cell.
        (
            _SAM_ROW,
            '<tr><td valign="top"><a href="getlex.php?coord=56000112010&word=9">x</a>'
            '<a href="comment.php?coord=56000112010"',
            "coordinate cell",
        ),
        # Loose text in the token cell would otherwise be merged into the line.
        (_SAM_TOKENS, "<td>stray " + _SAM_TOKENS[4:], "token cell"),
    ],
)
async def test_unexpected_row_shapes_fail_closed(old: str, new: str, message: str) -> None:
    body = SAMARITAN.read_text(encoding="utf-8")
    assert old in body
    with pytest.raises(TextParseError, match=message):
        await _page(body.replace(old, new, 1).encode(), "56000", "112")


@pytest.mark.anyio
async def test_lexical_link_outside_a_text_row_fails_closed() -> None:
    body = SAMARITAN.read_text(encoding="utf-8").replace(
        '<table class="text-display">',
        '<p><a href="getlex.php?coord=56000112010&word=0">w)mr</a></p><table class="text-display">',
        1,
    )
    with pytest.raises(TextParseError, match="outside"):
        await _page(body.encode(), "56000", "112")
