"""Issue #178: current citation-search rows, including a citation without its own header.

See docs/research/issue-178-headerless-citation.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.search import (
    CitationTextSearchResult,
    SearchParseError,
    SearchProvenance,
    parse_citation_search_page,
)

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "search_citations_king_rows_current.html"
URL = "https://cal.huc.edu/searchcits.php"


def _parse(body: bytes):
    return parse_citation_search_page(
        CalResponse(
            status_code=200,
            url=URL,
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 29, tzinfo=UTC),
        )
    )


def test_rows_keep_cal_order_and_never_attribute_a_headerless_citation() -> None:
    hits = _parse(FIXTURE.read_bytes()).hits

    assert [(hit.lemma.lemma_key if hit.lemma else None, hit.reference) for hit in hits] == [
        ("brt@ym N", "TgEsth2 1:2(86)"),
        (None, "JulSok 257(125):14"),
        ("kl N", "Sf.2.c15"),
        ("krk N", "TN Num34:15"),
        ("mlk V", "TgIIChron 25:16"),
    ]
    headerless = hits[1]
    assert headerless.lexical_context == ": small wall or glacis"
    assert "ܫܘܪܐ" in headerless.source_text
    assert headerless.translation == (
        "its Lord’s blessings will be a rampart for Edessa and your kingship’s blessing a wall"
    )
    assert hits[0].lexical_context == "dolphin : (zool.) dolphin"


def test_headers_take_the_part_of_speech_from_cal_pos_markup() -> None:
    hits = _parse(FIXTURE.read_bytes()).hits
    lemmas = [hit.lemma for hit in hits if hit.lemma is not None]

    assert [
        (lemma.headwords, lemma.pronunciation, lemma.part_of_speech, lemma.gloss)
        for lemma in lemmas
    ] == [
        (("brt ym",), None, "n.f.", ""),
        (("kl", "klˀ"), "ku/ol, kullā (kollā)", "n.(pr.)", ""),
        (("krk", "krkˀ"), "kreḵ, karkā", "n.m.(f.)", ""),
        (("MLK",), None, "vb. e(a)/u", ""),
    ]


def test_headerless_citation_serializes_with_null_lemma() -> None:
    page = _parse(FIXTURE.read_bytes())
    result = CitationTextSearchResult(
        hits=page.hits,
        provenance=SearchProvenance(
            source="CAL",
            source_url=URL,
            retrieved_at=datetime(2026, 9, 29, tzinfo=UTC),
            original_query="king",
            submitted_query="king",
            search_kind="citation_text",
        ),
    )

    hits = result.to_dict()["hits"]
    assert isinstance(hits, list)
    assert hits[1]["lemma"] is None
    assert hits[1]["reference"] == "JulSok 257(125):14"


_BRT = (
    b'<a href="oneentry.php?lemma=brt%40ym N&cits=all"><span class="lem">'
    b'<font color="#0000A0">brt ym</font></span>\n\t<pos>n.f.</pos>\n</a><br>'
)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (_BRT, b""),  # a row without a header
        (_BRT, _BRT + _BRT),  # a row with two headers
        (b"<pos>n.f.</pos>", b""),  # a header without CAL's POS markup
        (b"<pos>n.f.</pos>", b"<pos>n.f.</pos><pos>adj.</pos>"),  # two POS elements
        (b"<br>\n : small wall or glacis<br>", b"<br>"),  # a citation without its context
        (b"<i>JulSok 257(125):14</i>", b"JulSok 257(125):14"),  # a context without a citation
    ],
)
def test_other_row_shapes_fail_closed(old: bytes, new: bytes) -> None:
    body = FIXTURE.read_bytes()
    assert old in body

    with pytest.raises(SearchParseError):
        _parse(body.replace(old, new, 1))


_HOMOGRAPH_ROW = (
    b'<div class="citation-row odd"><a href="oneentry.php?lemma=gml%233 N&cits=all">'
    b'<span class="lem"><font color="#0000A0">gml, gmlk</font></span>\n'
    b'(<span class="uni">gamm\xc4\x81l, gamm\xc4\x81l\xc4\x81</span>)\n\t<pos>n.m.</pos>\n #3</a><br>'
    b'&nbsp;&nbsp;<span class="gloss"> camel-driver</span><br>\n'
    b'<i>EchR[1]50(2)</i> :<span class="heb">\xd7\x95\xd7\x92\xd7\x9e\xd7\x9c\xd7\x90</span>&rlm;\n'
    b':<span class="rom"> the camel-driver is a gentile</span><br>\n</div>'
)


def _with_homograph_row(row: bytes) -> bytes:
    return FIXTURE.read_bytes().replace(b"</div>\n</body>", row + b"\n</div>\n</body>")


def test_homograph_marker_after_pos_is_not_part_of_the_headwords() -> None:
    hits = _parse(_with_homograph_row(_HOMOGRAPH_ROW)).hits
    lemma = hits[-1].lemma

    assert lemma is not None
    assert (lemma.lemma_key, lemma.headwords, lemma.pronunciation, lemma.part_of_speech) == (
        "gml#3 N",
        ("gml", "gmlk"),
        "gammāl, gammālā",
        "n.m.",
    )
    assert hits[-1].lexical_context == "camel-driver"


@pytest.mark.parametrize("marker", [b" #2", b" extra"])
def test_other_text_after_pos_fails_closed(marker: bytes) -> None:
    with pytest.raises(SearchParseError):
        _parse(_with_homograph_row(_HOMOGRAPH_ROW.replace(b" #3</a>", marker + b"</a>")))
