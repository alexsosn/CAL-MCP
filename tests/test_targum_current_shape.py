"""Issue #152: current (2026-09-24) Targum concordance and Hebrew-reflex markup.

See docs/research/issue-152-targum-concordance-reflex-drift.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.targum import (
    TargumParseError,
    parse_targum_concordance_page,
    parse_targum_reflex_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
CONCORDANCE_URL = "https://cal.huc.edu/showtargumKWIC.php"
REFLEX_URL = "https://cal.huc.edu/getOmtlemma.php"


def _response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 24, tzinfo=UTC),
    )


def _concordance_body() -> str:
    return (FIXTURES / "targum_concordance_klb_current.html").read_text(encoding="utf-8")


def _reflex_body() -> str:
    return (FIXTURES / "targum_reflex_onqelos_1751_current.html").read_text(encoding="utf-8")


def _concordance(body: str) -> object:
    return parse_targum_concordance_page(_response(body, CONCORDANCE_URL), lemma_key="klb N")


def _reflex(body: str) -> object:
    return parse_targum_reflex_page(
        _response(body, REFLEX_URL), targum="onqelos", mt_lemma_id="1751"
    )


def test_current_targum_concordance_preserves_rows_counts_and_total() -> None:
    page = _concordance(_concordance_body())

    assert page.total == 26  # type: ignore[attr-defined]
    rows = page.rows  # type: ignore[attr-defined]
    assert [(row.section, row.label, row.count) for row in rows] == [
        ("Torah", "Onqelos", 3),
        ("Torah", "Former Prophets", 19),
        ("Torah", "Writing Prophets", 4),
        ("Torah", "TgSong", 0),
    ]
    # CAL's own truncated selector is passed through unchanged.
    assert "51019 5102&charset=H" in rows[2].example_url


def test_current_targum_reflex_preserves_correspondence() -> None:
    page = _reflex(_reflex_body())

    assert page.mt_hebrew_lemma == "מַעֲקֶה"  # type: ignore[attr-defined]
    assert page.source_label == "Onkelos"  # type: ignore[attr-defined]
    [row] = page.reflexes  # type: ignore[attr-defined]
    assert (row.lemma_key, row.label, row.frequency) == ("tyq#2 N", "תיק #2 N", 2)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        # Page title for another lemma.
        (
            "<title>CAL: Targum KWIC counts for klb N</title>",
            "<title>CAL: Targum KWIC counts for kbl N</title>",
            "heading does not match the submitted lemma",
        ),
        # Body statement naming another lemma.
        ('The lemma "klb N" is attested', 'The lemma "kbl N" is attested', "statement names"),
        # In-table total contradicting the row sum.
        ("total examples: 26", "total examples: 27", "contradict the reported total"),
        # Two totals.
        (
            "total examples: 26</td></tr>",
            "total examples: 26</td></tr><tr><td>total examples: 26</td></tr>",
            "count/total semantics",
        ),
        # A section row carrying a link.
        (
            '<td scope="col">Torah</td>',
            '<td scope="col"><a href="/x.php">Torah</a></td>',
            "section semantics",
        ),
    ],
)
def test_current_targum_concordance_contradictions_fail_closed(
    old: str, new: str, message: str
) -> None:
    body = _concordance_body()
    assert old in body
    with pytest.raises(TargumParseError, match=message):
        _concordance(body.replace(old, new, 1))


def test_current_targum_reflex_heading_for_wrong_source_fails_closed() -> None:
    body = _reflex_body().replace("Onkelos correspondences", "Neofiti correspondences")
    with pytest.raises(TargumParseError, match="source/result heading"):
        _reflex(body)
