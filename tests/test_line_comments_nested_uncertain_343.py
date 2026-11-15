"""Issue #343: source-grounded romanized citations with one uncertain wrapper."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.texts import (
    TextParseError,
    _line_comment_record_to_dict,
    parse_text_line_comments_page,
)

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_line_comments_roman_uncertain.html"
_COORD = "1325002"


def _response(body: str | None = None) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/comment.php?coord={_COORD}",
        body=(FIXTURE.read_text(encoding="utf-8") if body is None else body).encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 11, 15, tzinfo=UTC),
    )


def test_current_roman_source_nested_uncertain_preserves_source_and_translation() -> None:
    parsed = parse_text_line_comments_page(_response(), requested_coordinate=_COORD)
    assert parsed.status.value == "found"
    assert len(parsed.records) == 1
    record = parsed.records[0]
    assert record.reference == "Synthetic 2"
    assert record.source_text == "a b c"
    assert record.translation == "synthetic translation"
    assert record.lemma_key == "mlk N"
    assert record.headword == "mlk"
    assert record.has_uncertain_reading is True
    assert _line_comment_record_to_dict(record)["has_uncertain_reading"] is True


@pytest.mark.parametrize(
    "modify",
    (
        lambda s: s.replace('class="uncertain"', 'class="unknown"', 1),
        lambda s: s.replace('<span class="rom">a ', '<span class="heb">a ', 1),
        lambda s: s.replace(
            '<span class="rom">synthetic translation',
            '<span class="heb">synthetic translation',
            1,
        ),
        lambda s: s.replace('<span class="uncertain">b</span>', "b", 1),
        lambda s: s.replace(
            '<span class="uncertain">b</span>', '<span class="uncertain"></span>', 1
        ),
        lambda s: s.replace(
            '<span class="uncertain">b</span>', '<span class="uncertain">  </span>', 1
        ),
        lambda s: s.replace(
            '<span class="uncertain">b</span>',
            '<span class="uncertain"><span class="uncertain">b</span></span>',
            1,
        ),
        lambda s: s.replace('<span class="uncertain">b</span>', '<span class="uncertain">b', 1),
    ),
)
def test_unreviewed_nested_spans_and_bare_roman_pair_fail_closed(modify) -> None:
    with pytest.raises(TextParseError):
        parse_text_line_comments_page(
            _response(modify(FIXTURE.read_text(encoding="utf-8"))),
            requested_coordinate=_COORD,
        )


def test_historical_hebrew_comment_has_no_uncertainty_annotation() -> None:
    fixture = FIXTURE.parent / "text_line_comments_pj_gen8_21.html"
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/comment.php?coord=8100110821",
        body=fixture.read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 11, 15, tzinfo=UTC),
    )
    page = parse_text_line_comments_page(response, requested_coordinate="8100110821")
    assert page.status.value == "found"
    assert all(record.has_uncertain_reading is False for record in page.records)
    serialized = [_line_comment_record_to_dict(record) for record in page.records]
    flags = [record["has_uncertain_reading"] for record in serialized]
    assert flags == [False] * len(page.records)
