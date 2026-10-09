from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.token_analysis import TokenAnalysisParseError, parse_token_analysis_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _response(body: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getlex.php?coord=56000112010&word=0",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 9, tzinfo=UTC),
    )


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _summary(candidate: object) -> tuple[object, ...]:
    lemma = candidate.lemma  # type: ignore[attr-defined]
    return (
        candidate.analysis_label,  # type: ignore[attr-defined]
        lemma.lemma_key,
        lemma.headwords,
        lemma.pronunciation,
        lemma.part_of_speech,
        lemma.gloss,
    )


def test_every_lexeme_of_a_prefixed_verb_is_returned_with_marked_pos() -> None:
    page = parse_token_analysis_page(
        _response(_fixture("token_analysis_multi_lexeme_verb_current.html"))
    )

    assert [_summary(item) for item in page.candidates] == [
        ("w_ c", "w_ c", ("w_",), "wə_", "conj.", "and, also"),
        (")mr verb G", ")mr V", ("ˀmr",), None, "vb. a/a", "to say"),
    ]
    assert page.unlinked_summaries == ()


def test_linked_candidate_and_later_unlinked_summary_are_both_kept() -> None:
    page = parse_token_analysis_page(
        _response(_fixture("token_analysis_linked_then_unlinked_current.html"))
    )

    assert [_summary(item) for item in page.candidates] == [
        ("l_ p03", "l_ p", ("l_",), None, "prep.", "to, for"),
    ]
    assert page.unlinked_summaries == (")brM PN Personal name",)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        # A second table in the same segment.
        (
            "</td></tr></table><p>",
            '</td></tr></table><table border="1"><tr><td>x</td></tr></table><p>',
        ),
        # A linked segment without an analysis label.
        ("<hr>)mr verb G<table", "<hr><table"),
        # A marked POS that disagrees with the rendered header.
        ('<font color="#0000A0">ˀmr</font>', '<font color="#0000A0">ˀmr n.m.</font>'),
    ],
)
def test_segment_drift_fails_closed(old: str, new: str) -> None:
    body = _fixture("token_analysis_multi_lexeme_verb_current.html")
    assert old in body
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(_response(body.replace(old, new, 1)))


_LINKED_THEN_UNLINKED = "token_analysis_linked_then_unlinked_current.html"
_VERB = "token_analysis_multi_lexeme_verb_current.html"


@pytest.mark.parametrize(
    ("fixture", "old", "new"),
    [
        # No footer and no return link: CAL's navigation must not become a summary.
        (_LINKED_THEN_UNLINKED, '<div class="cal-footer">', '<div class="other">'),
        # A link inside a text-only segment would lose its lemma identity as a plain summary.
        (
            _LINKED_THEN_UNLINKED,
            ")brM PN Personal name",
            '<a href="oneentry.php?lemma=%29brM+PN&cits=all">)brM PN Personal name</a>',
        ),
        # Other markup in a summary segment.
        (_LINKED_THEN_UNLINKED, ")brM PN Personal name", "<span>)brM PN Personal name</span>"),
        # Bare text after a result table, before the next <hr>.
        (_LINKED_THEN_UNLINKED, "</small><hr><br>)brM", "</small>)brM"),
        # Two, empty or unclosed <pos> elements in a candidate link.
        (_VERB, "<pos>vb. a/a</pos>", "<pos>vb.</pos><pos>a/a</pos>"),
        (_VERB, "<pos>vb. a/a</pos>", "<pos></pos>vb. a/a"),
        (_VERB, "<pos>vb. a/a</pos></span>", "<pos>vb. a/a</span>"),
    ],
    ids=[
        "no-end-boundary",
        "link-in-summary",
        "markup-in-summary",
        "text-after-table",
        "two-pos",
        "empty-pos",
        "unclosed-pos",
    ],
)
def test_segment_boundary_drift_fails_closed(fixture: str, old: str, new: str) -> None:
    body = _fixture(fixture)
    assert old in body
    # Replace the last occurrence: the provenance comment quotes some of these strings first.
    head, _, tail = body.rpartition(old)
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(_response(head + new + tail))


def test_hr_inside_a_sense_outline_does_not_create_a_summary() -> None:
    body = _fixture(_VERB).replace(
        '<p><span class="bin">G</span>',
        '<p><span class="bin">G</span><div class="sense-line">to say<hr>to command</div>',
    )
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(_response(body))
