"""Issue #168: preserve CAL's researched blank text-line sentinel."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageResult, TextParseError, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
BLANK = FIXTURES / "text_page_blank_word0_60424_current.html"
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
async def test_single_empty_word_zero_link_is_preserved_as_blank_line() -> None:
    result = await _page(BLANK.read_bytes(), "60424")

    assert result.page is not None
    assert len(result.page.lines) == 1
    line = result.page.lines[0]
    assert line.coordinate == "60424100508"
    assert line.display_coordinate == "1.005:08"
    assert line.text == ""
    assert line.tokens == ()
    assert line.comment_url is None


@pytest.mark.anyio
async def test_normal_current_text_row_remains_tokenized() -> None:
    result = await _page(PHILEMON.read_bytes(), "62057")

    assert result.page is not None
    first = result.page.lines[0]
    assert first.coordinate == "620570101"
    assert first.display_coordinate == "01"
    assert first.text.startswith("p.awlAws )asyireh")
    assert first.tokens
    assert first.tokens[0].word_index == 0
    assert first.tokens[0].text == "p.awlAws"


@pytest.mark.anyio
async def test_empty_link_at_word_greater_than_zero_fails_closed() -> None:
    body = BLANK.read_text(encoding="utf-8").replace("word=0&hasvariant=0", "word=1&hasvariant=0")
    with pytest.raises(TextParseError):
        await _page(body.encode(), "60424")


@pytest.mark.anyio
async def test_empty_link_mixed_with_real_token_fails_closed() -> None:
    body = BLANK.read_text(encoding="utf-8").replace(
        "</a> </td>",
        '</a> <a href="getlex.php?coord=60424100508&word=1&hasvariant=0">x</a> </td>',
    )
    with pytest.raises(TextParseError):
        await _page(body.encode(), "60424")


@pytest.mark.anyio
@pytest.mark.parametrize(
    "old,new",
    [
        ("getlex.php?coord=", "bablex.php?coord="),
        ("&hasvariant=0", ""),
        ("&hasvariant=0", "&hasvariant=1"),
        ("&hasvariant=0", "&hasvariant=0&extra=1"),
    ],
)
async def test_other_empty_anchor_shapes_fail_closed(old: str, new: str) -> None:
    body = BLANK.read_text(encoding="utf-8")
    assert old in body
    with pytest.raises(TextParseError):
        await _page(body.replace(old, new, 1).encode(), "60424")
