from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import LexiconEntry, LexiconParseError, parse_lexicon_entry

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _entry(body: str) -> LexiconEntry:
    return parse_lexicon_entry(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/cal_entry_web.php?lemma=%29lh+N",
            body=body.encode("utf-8"),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
        ),
        lemma_key=")lh N",
    )


def _group(content: str, count: int = 1) -> str:
    """Synthetic legacy entry with a single independently testable citation group."""
    return (
        "<header>test n.m. example</header><div>1</div><div>example</div>"
        f"<div>▶ {count} citations</div><div>{content}</div>"
    )


def test_separator_and_in_text_semicolon_on_the_same_line() -> None:
    entry = _entry((FIXTURES / "entry_alh_citation_semicolon.html").read_text(encoding="utf-8"))

    assert [(item.reference, item.text) for item in entry.senses[0].citations] == [
        ("BT Yom 9b(41)", "mˀlhˀ; snynˀ lkw"),
        ("TAD B2.2 R.4", "ymˀt ly byhw ˀlhˀ"),
    ]
    assert [item.url for item in entry.senses[0].citations] == [
        "https://cal.huc.edu/citation.php?id=bt-yom-9b-41",
        "https://cal.huc.edu/citation.php?id=tad-b2-2-r4",
    ]
    assert [(item.reference, item.text) for item in entry.senses[1].citations] == [
        ("MT Jer 10:11", "ˀlhyˀ dy šmyˀ; wˀrqˀ")
    ]
    # Legacy free text supplies no independently delimited reference or URL.
    assert [(item.reference, item.url, item.text) for item in entry.senses[2].citations] == [
        (None, None, "EphNis 41:3 ddlˀ ˀlh ˀytyhwn")
    ]


@pytest.mark.parametrize(
    "text",
    [
        "mˀlhˀ; snynˀ lkw",
        "ܡܐܠܗܐ܃ ܣܢܝܢܐ ܠܟܘ",
        "אלהא; שנינא",
        "before ;after",
        "before;after",
    ],
)
@pytest.mark.parametrize("linked", [True, False])
def test_internal_punctuation_does_not_inflate_citation_count(text: str, linked: bool) -> None:
    reference = '<a href="/citation.php?id=test">Ref↗</a> ' if linked else ""

    citations = _entry(_group(reference + text)).senses[0].citations

    assert len(citations) == 1
    assert citations[0].text == text
    assert citations[0].reference == ("Ref" if linked else None)
    assert citations[0].url == ("https://cal.huc.edu/citation.php?id=test" if linked else None)


@pytest.mark.parametrize("separator", [" ; ", "  ;  ", "\t;\n"])
def test_separator_before_next_link_does_not_remain_in_previous_text(separator: str) -> None:
    content = (
        '<a href="/citation.php?id=first">First↗</a> first text'
        + separator
        + '<a href="/citation.php?id=second">Second↗</a> second text'
    )

    citations = _entry(_group(content, count=2)).senses[0].citations

    assert [(item.reference, item.text) for item in citations] == [
        ("First", "first text"),
        ("Second", "second text"),
    ]


def test_mixed_plain_and_linked_legacy_citations_preserve_order() -> None:
    content = (
        "First ref first; clause ; "
        '<a href="/citation.php?id=second">Second↗</a> second; clause ; '
        "Third ref third; clause"
    )

    citations = _entry(_group(content, count=3)).senses[0].citations

    assert [(item.reference, item.text) for item in citations] == [
        (None, "First ref first; clause"),
        ("Second", "second; clause"),
        (None, "Third ref third; clause"),
    ]
    assert citations[0].url is None
    assert citations[2].url is None


def test_structural_separator_takes_precedence_over_legacy_punctuation() -> None:
    content = (
        '<a href="/citation.php?id=first">First↗</a> first ; clause; text'
        '<span class="cit-sep">;</span>'
        '<a href="/citation.php?id=second">Second↗</a> second ; clause; text'
    )

    citations = _entry(_group(content, count=2)).senses[0].citations

    assert [(item.reference, item.text) for item in citations] == [
        ("First", "first ; clause; text"),
        ("Second", "second ; clause; text"),
    ]


def test_legacy_citation_count_mismatch_still_fails_closed() -> None:
    with pytest.raises(LexiconParseError, match="citation count"):
        _entry(_group("first; clause ; second; clause", count=3))
