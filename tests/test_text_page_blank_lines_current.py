"""Issue #168: preserve CAL's explicit empty lexical word slots."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageResult, TextParseError, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
ALL_EMPTY = FIXTURES / "text_page_blank_word0_60424_current.html"
MIXED = FIXTURES / "text_page_empty_slots_mixed_60424_structural.html"
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
            retrieved_at=datetime(2026, 9, 26, tzinfo=UTC),
        )


async def _page(body: bytes, file_id: str) -> TextPageResult:
    client = CalHttpClient(transport=FixtureTransport(body))
    try:
        return await TextService(client).page(file_id)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_all_empty_row_preserves_coordinate_and_empty_word_index() -> None:
    result = await _page(ALL_EMPTY.read_bytes(), "60424")

    assert result.page is not None
    assert len(result.page.lines) == 1
    line = result.page.lines[0]
    assert line.coordinate == "60424100508"
    assert line.display_coordinate == "1.005:08"
    assert line.text == ""
    assert line.tokens == ()
    assert line.empty_word_indexes == (0,)
    assert line.comment_url is None


@pytest.mark.anyio
async def test_mixed_row_keeps_rendered_token_and_records_empty_slot() -> None:
    result = await _page(MIXED.read_bytes(), "60424")

    assert result.page is not None
    line = result.page.lines[0]
    assert line.coordinate == "60424100523"
    assert line.display_coordinate == "fixture-line"
    assert line.text == "fixture-token"
    assert [(token.word_index, token.text) for token in line.tokens] == [(0, "fixture-token")]
    assert line.empty_word_indexes == (1,)


@pytest.mark.anyio
async def test_normal_current_text_row_has_no_empty_word_indexes() -> None:
    result = await _page(PHILEMON.read_bytes(), "62057")

    assert result.page is not None
    first = result.page.lines[0]
    assert first.coordinate == "620570101"
    assert first.display_coordinate == "01"
    assert first.text.startswith("p.awlAws )asyireh")
    assert first.tokens
    assert first.empty_word_indexes == ()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("getlex.php?coord=", "bablex.php?coord="),
        ("getlex.php?coord=", "/getlex.php?coord="),
        ("getlex.php?coord=", "https://example.invalid/getlex.php?coord="),
        ("coord=60424100508", "coord=not-a-coordinate"),
        ("coord=60424100508", "coord=0"),
        ("word=0", "word=not-a-number"),
        ("&hasvariant=0", ""),
        ("&hasvariant=0", "&hasvariant=1"),
        ("&hasvariant=0", "&hasvariant=0&extra=1"),
        ("&hasvariant=0", "&hasvariant=0#fragment"),
    ],
)
async def test_malformed_all_empty_slot_shapes_fail_closed(old: str, new: str) -> None:
    body = ALL_EMPTY.read_text(encoding="utf-8")
    assert old in body
    with pytest.raises(TextParseError):
        await _page(body.replace(old, new, 1).encode(), "60424")


@pytest.mark.anyio
async def test_empty_slot_coordinate_must_match_rendered_tokens() -> None:
    body = MIXED.read_text(encoding="utf-8")
    # Change only the empty slot's coordinate.
    marker = "coord=60424100523&word=1"
    assert marker in body
    body = body.replace(marker, "coord=60424100524&word=1", 1)
    with pytest.raises(TextParseError, match="coordinate"):
        await _page(body.encode(), "60424")


@pytest.mark.anyio
async def test_duplicate_empty_word_index_fails_closed() -> None:
    body = MIXED.read_text(encoding="utf-8")
    empty = '<a href="getlex.php?coord=60424100523&word=1&hasvariant=0"></a>'
    assert empty in body
    body = body.replace(empty, empty + " " + empty, 1)
    with pytest.raises(TextParseError, match="duplicate"):
        await _page(body.encode(), "60424")


@pytest.mark.anyio
async def test_empty_word_index_cannot_collide_with_rendered_token() -> None:
    body = MIXED.read_text(encoding="utf-8")
    assert 'word=1&hasvariant=0"></a>' in body
    body = body.replace('word=1&hasvariant=0"></a>', 'word=0&hasvariant=0"></a>', 1)
    with pytest.raises(TextParseError, match="collides"):
        await _page(body.encode(), "60424")


@pytest.mark.anyio
async def test_empty_slot_with_loose_text_still_fails_closed() -> None:
    body = ALL_EMPTY.read_text(encoding="utf-8")
    assert "</a> </td>" in body
    body = body.replace("</a> </td>", "</a> stray </td>", 1)
    with pytest.raises(TextParseError, match="text outside"):
        await _page(body.encode(), "60424")


@pytest.mark.anyio
async def test_empty_slot_does_not_weaken_normal_empty_token_parser() -> None:
    # The generic token parser is intentionally unchanged. A legacy non-table line containing
    # an empty lexical anchor remains invalid rather than inheriting the table-slot exception.
    body = b"""<html><body>
    <a href="/get_file_info.php?coord=60424">60424: fixture</a>
    <div>fixture <a href="getlex.php?coord=60424100508&word=0&hasvariant=0"></a></div>
    </body></html>"""
    with pytest.raises(TextParseError):
        await _page(body, "60424")
