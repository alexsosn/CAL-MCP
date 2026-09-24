"""Issue #152: current (2026-09-24) Targum concordance and Hebrew-reflex markup.

See docs/research/issue-152-targum-concordance-reflex-drift.md.
"""

from __future__ import annotations

import re
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
    # CAL's current page renders "Torah" as a label row without applying it as a grouping
    # (later rows include Former/Writing Prophets), so rows carry no section and the label
    # is reported with its position instead.
    assert [(row.section, row.label, row.count) for row in rows] == [
        (None, "Onqelos", 3),
        (None, "Former Prophets", 19),
        (None, "Writing Prophets", 4),
        (None, "TgSong", 0),
    ]
    assert [(item.label, item.row_index) for item in page.section_labels] == [  # type: ignore[attr-defined]
        ("Torah", 0)
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


def test_current_targum_reflex_mixed_header_cell_kinds_are_not_a_header() -> None:
    body = _reflex_body().replace(
        "<tr><td>CAL lemma</td><td>frequency</td></tr>",
        "<tr><th>CAL lemma</th><td>frequency</td></tr>",
    )
    with pytest.raises(TargumParseError, match="unrecognized result row|required semantics"):
        _reflex(body)


def test_current_concordance_damaged_result_row_is_not_a_label_row() -> None:
    # A result row that lost its link and count must not be reclassified as a label row.
    body, replaced = re.subn(
        r"<tr><td[^>]*><div[^>]*><a [^>]*>Former Prophets</a>.*?</tr>",
        "<tr><td>Former Prophets</td><td></td></tr>",
        _concordance_body(),
    )
    assert replaced == 1
    body = body.replace("total examples: 26", "total examples: 7")
    with pytest.raises(TargumParseError, match="row lacks required semantics"):
        _concordance(body)


@pytest.mark.parametrize(
    "extra",
    [
        "<h1>CAL: Targum KWIC counts for klb N</h1>",
        "<title>CAL: Targum KWIC counts for klb N</title>",
    ],
)
def test_current_concordance_repeated_identical_heading_is_accepted(extra: str) -> None:
    body = _concordance_body().replace(
        '<div class="summary-card">', extra + '<div class="summary-card">'
    )
    page = _concordance(body)
    assert page.total == 26  # type: ignore[attr-defined]


def test_current_concordance_total_row_must_be_exact() -> None:
    body = _concordance_body().replace("total examples: 26", "total examples: 26 (approx.)")
    with pytest.raises(TargumParseError, match="unrecognized result row"):
        _concordance(body)


def test_concordance_result_serializes_section_labels() -> None:
    from cal_mcp.targum import TargumConcordanceResult, _make_provenance

    page = _concordance(_concordance_body())
    result = TargumConcordanceResult(
        lemma_key="klb N",
        rows=page.rows,  # type: ignore[attr-defined]
        total=page.total,  # type: ignore[attr-defined]
        section_labels=page.section_labels,  # type: ignore[attr-defined]
        provenance=_make_provenance(
            CONCORDANCE_URL,
            datetime(2026, 9, 24, tzinfo=UTC),
            operation="targum_concordance",
            lemma_key="klb N",
        ),
    ).to_dict()
    assert result["section_labels"] == [{"label": "Torah", "row_index": 0}]


@pytest.mark.anyio
async def test_service_output_carries_section_labels() -> None:
    from cal_mcp.client import CalHttpClient
    from cal_mcp.targum import TargumService

    async def transport(request: object, config: object) -> CalResponse:
        del request, config
        return _response(_concordance_body(), CONCORDANCE_URL)

    service = TargumService(CalHttpClient(transport=transport))  # type: ignore[arg-type]
    payload = (await service.concordance("klb N")).to_dict()

    assert payload["section_labels"] == [{"label": "Torah", "row_index": 0}]
    rows = payload["rows"]
    assert isinstance(rows, list)
    assert {row["section"] for row in rows} == {None}


_LABEL_ROW = '<tr><td scope="col">Former group</td><td scope="col">&nbsp;</td></tr>'


def test_section_label_row_index_points_at_the_first_row_after_it() -> None:
    body = re.sub(
        r"(<tr><td[^>]*><div[^>]*><a [^>]*>Writing Prophets</a>)",
        _LABEL_ROW + r"\1",
        _concordance_body(),
        count=1,
    )
    page = _concordance(body)
    assert [(item.label, item.row_index) for item in page.section_labels] == [  # type: ignore[attr-defined]
        ("Torah", 0),
        ("Former group", 2),
    ]
    assert page.rows[2].label == "Writing Prophets"  # type: ignore[attr-defined]


def test_section_label_after_the_last_row_has_index_equal_to_row_count() -> None:
    body = re.sub(
        r"(<tr><td[^>]*>total examples:)",
        _LABEL_ROW + r"\1",
        _concordance_body(),
        count=1,
    )
    page = _concordance(body)
    assert page.section_labels[-1].row_index == len(page.rows) == 4  # type: ignore[attr-defined]


def test_missing_identifying_heading_fails_closed() -> None:
    body = _concordance_body().replace(
        "<title>CAL: Targum KWIC counts for klb N</title>", "<title>CAL</title>"
    )
    with pytest.raises(TargumParseError, match="heading does not match the submitted lemma"):
        _concordance(body)
