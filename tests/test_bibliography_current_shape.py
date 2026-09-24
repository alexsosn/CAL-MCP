"""Issue #150: current (2026-09-24) bibliography result-page markup.

See docs/research/issue-150-bibliography-drift.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.bibliography import (
    BibliographyPage,
    BibliographyParseError,
    BibliographyQueryKind,
    parse_bibliography_page,
)
from cal_mcp.client import CalResponse

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 24, tzinfo=UTC)
LEMMA_URL = "https://cal.huc.edu/getbiblemma.php?myauthor=br+N"
AUTHOR_URL = "https://cal.huc.edu/getbibauthor.php?myauthor=Sokoloff%2C+Michael"
EMPTY_URL = "https://cal.huc.edu/getbiblemma.php?myauthor=qqqqzz+N"


def _response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _lemma(body: str) -> BibliographyPage:
    return parse_bibliography_page(_response(body, LEMMA_URL))


def test_current_lemma_page_returns_one_record_per_paragraph() -> None:
    page = parse_bibliography_page(
        _response(_fixture("bibliography_lemma_br_n_current.html"), LEMMA_URL)
    )

    assert page.heading == "CAL Bibliography for br N"
    assert [record.citation.split(",")[0] for record in page.records] == [
        "Jansma",
        "Avishur",
        "Testen",
    ]
    for record in page.records:
        assert "BIBLIOGRAPHY SEARCH" not in record.citation
        assert "CAL Bibliography" not in record.citation
    assert page.records[0].citation.startswith("Jansma, T., \"Aphraate's Demonstration VII")
    assert page.records[0].citation.endswith("(1974): 21–48.")
    assert [link.label for link in page.records[0].links] == ["br N", "qym N", "m)mr N", "txwy N"]
    assert [(link.label, link.query_kind) for link in page.records[2].links] == [
        ("Grammar", BibliographyQueryKind.KEYWORD),
        ("br N", BibliographyQueryKind.LEMMA),
        ("tryn b", BibliographyQueryKind.LEMMA),
    ]


def test_current_author_page_omits_cal_empty_placeholder_links() -> None:
    page = parse_bibliography_page(
        _response(_fixture("bibliography_author_sokoloff_current.html"), AUTHOR_URL)
    )

    assert len(page.records) == 2
    # CAL order: the placeholder-bearing record comes first on the live page.
    assert [link.label for link in page.records[0].links] == ["Grammar", "CPA", "Gal", "Samar"]
    assert "[The Noun Pattern MQTWLYin Middle Western Aramaic]" in page.records[0].citation
    assert [link.label for link in page.records[1].links] == ["BA"]


def test_current_empty_page_with_marker_inside_card_is_valid_empty_result() -> None:
    page = parse_bibliography_page(
        _response(_fixture("bibliography_empty_current.html"), EMPTY_URL)
    )

    assert page.heading == "CAL Bibliography for qqqqzz N"
    assert page.records == ()


_LAST_RECORD_END = '<a href="/getbiblemma.php?myauthor=tryn%20b">tryn b</a></p>'


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        # Text inside the record card but outside any <p> record.
        (
            _LAST_RECORD_END,
            _LAST_RECORD_END + "Stray unparsed bibliography text",
            "outside its records",
        ),
        # A record nested inside another record.
        ("<p>Avishur, Y.,", "<p>Nested <p>Avishur, Y.,", "nested records"),
        # A closing </p> with no open record.
        ("<p>Testen, D.,", "</p><p>Testen, D.,", "unbalanced"),
        # An unclosed record.
        (_LAST_RECORD_END, _LAST_RECORD_END.removesuffix("</p>"), "incomplete"),
        # A link with a target but no label.
        (">qym N</a>", "></a>", "record link has no label"),
        # A labelled link with an empty target value.
        (
            '<a href="/getbiblemma.php?myauthor=qym%20N">qym N</a>',
            '<a href="/getbiblemma.php?myauthor=">qym N</a>',
            "invalid bibliography query value",
        ),
        # Records alongside the no-data marker.
        (
            _LAST_RECORD_END,
            _LAST_RECORD_END + "<p>NO data FOR br N ARE CURRENTLY STORED</p>",
            "contradicts its no-data marker",
        ),
    ],
)
def test_current_lemma_page_structure_fails_closed(old: str, new: str, message: str) -> None:
    body = _fixture("bibliography_lemma_br_n_current.html")
    assert old in body
    with pytest.raises(BibliographyParseError, match=message):
        _lemma(body.replace(old, new, 1))


def test_newline_placeholder_variant_is_also_omitted() -> None:
    body = _fixture("bibliography_author_sokoloff_current.html").replace(
        '<a href="/getbiblemma.php?myauthor="></a>',
        '<a href="/getbibsigla.php?myauthor=%0A">\n</a>',
    )
    page = parse_bibliography_page(_response(body, AUTHOR_URL))
    assert [link.label for link in page.records[0].links] == ["Grammar", "CPA", "Gal", "Samar"]


def test_placeholder_omission_requires_both_empty_label_and_empty_target() -> None:
    body = _fixture("bibliography_author_sokoloff_current.html").replace(
        '<a href="/getbiblemma.php?myauthor="></a>',
        '<a href="/getbiblemma.php?myauthor=br%20N"></a>',
    )
    with pytest.raises(BibliographyParseError, match="record link has no label"):
        parse_bibliography_page(_response(body, AUTHOR_URL))


def test_marker_card_with_links_is_not_treated_as_marker() -> None:
    body = _fixture("bibliography_empty_current.html").replace(
        "ARE CURRENTLY STORED<br>",
        'ARE CURRENTLY STORED <a href="/getbiblemma.php?myauthor=br%20N">br N</a><br>',
    )
    with pytest.raises(BibliographyParseError):
        parse_bibliography_page(_response(body, EMPTY_URL))


@pytest.mark.anyio
async def test_live_smoke_bibliography_probe_rejects_merged_title_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cal_mcp import live_smoke

    class _Service:
        def __init__(self, client: object) -> None:
            del client

        async def lemma(self, lemma_key: str) -> object:
            del lemma_key

            class _Result:
                def to_dict(self) -> dict[str, object]:
                    return {
                        "records": [{"citation": "CAL BIBLIOGRAPHY SEARCH Millard, A.R."}],
                        "provenance": {
                            "source_url": "https://cal.huc.edu/getbiblemma.php?myauthor=cly+V",
                            "retrieved_at": RETRIEVED_AT.isoformat(),
                        },
                    }

            return _Result()

    monkeypatch.setattr(live_smoke, "BibliographyService", _Service)
    with pytest.raises(live_smoke.LiveSmokeSemanticError, match="record boundaries"):
        await live_smoke._probe_bibliography(None)  # type: ignore[arg-type]


def test_legacy_document_without_record_boundaries_fails_closed() -> None:
    # If CAL dropped the <p> wrappers, the one-card-per-record fallback must not merge
    # every work into one record again (#150 review).
    body = _fixture("bibliography_lemma_br_n_current.html").replace("<p>", "").replace("</p>", "")
    with pytest.raises(BibliographyParseError, match="has no record boundaries"):
        _lemma(body)


def test_title_metadata_inside_a_record_fails_closed() -> None:
    body = _fixture("bibliography_lemma_br_n_current.html").replace(
        "21–48.", "21–48. <title>Hidden text</title> tail", 1
    )
    with pytest.raises(BibliographyParseError, match="record contains title metadata"):
        _lemma(body)


_PLACEHOLDER = '<a href="/getbiblemma.php?myauthor="></a>'


@pytest.mark.parametrize(
    "replacement",
    [
        # Cross-origin empty link.
        '<a href="https://other.example/getbiblemma.php?myauthor="></a>',
        # Same-origin empty link with a fragment.
        '<a href="/getbiblemma.php?myauthor=#x"></a>',
        # Not a bibliography result endpoint.
        '<a href="/getlex.php?myauthor="></a>',
        # Extra query parameter.
        '<a href="/getbiblemma.php?myauthor=&amp;x=1"></a>',
        # Repeated empty value.
        '<a href="/getbiblemma.php?myauthor=&amp;myauthor="></a>',
    ],
)
def test_placeholder_rule_does_not_swallow_other_empty_links(replacement: str) -> None:
    body = _fixture("bibliography_author_sokoloff_current.html").replace(_PLACEHOLDER, replacement)
    assert replacement in body
    with pytest.raises(BibliographyParseError):
        parse_bibliography_page(_response(body, AUTHOR_URL))


def test_link_outside_records_in_record_card_fails_closed() -> None:
    body = _fixture("bibliography_lemma_br_n_current.html").replace(
        _LAST_RECORD_END,
        _LAST_RECORD_END + '<a href="/getbiblemma.php?myauthor=br%20N">br N</a>',
    )
    with pytest.raises(BibliographyParseError, match="content outside its records"):
        _lemma(body)


def test_record_opening_inside_an_unclosed_card_link_fails_closed() -> None:
    body = _fixture("bibliography_lemma_br_n_current.html").replace(
        "<p>Jansma, T.,", '<a href="/getbiblemma.php?myauthor=br%20N"><p>Jansma, T.,', 1
    )
    with pytest.raises(BibliographyParseError, match="record link is incomplete"):
        _lemma(body)


@pytest.mark.anyio
async def test_live_smoke_bibliography_probe_rejects_oversized_merged_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cal_mcp import live_smoke

    merged = "Millard, A.R., " + "x" * 800

    class _Service:
        def __init__(self, client: object) -> None:
            del client

        async def lemma(self, lemma_key: str) -> object:
            del lemma_key

            class _Result:
                def to_dict(self) -> dict[str, object]:
                    return {
                        "records": [{"citation": merged, "links": []}],
                        "provenance": {
                            "source_url": "https://cal.huc.edu/getbiblemma.php?myauthor=cly+V",
                            "retrieved_at": RETRIEVED_AT.isoformat(),
                        },
                    }

            return _Result()

    monkeypatch.setattr(live_smoke, "BibliographyService", _Service)
    with pytest.raises(live_smoke.LiveSmokeSemanticError, match="record boundaries"):
        await live_smoke._probe_bibliography(None)  # type: ignore[arg-type]
