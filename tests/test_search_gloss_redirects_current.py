from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import _looks_like_pos_token, parse_lexicon_entry
from cal_mcp.lexicon_browse import parse_lexicon_browse_page
from cal_mcp.search import SearchParseError, parse_gloss_search_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 10, 8, 18, 48, tzinfo=UTC)
URL = "https://cal.huc.edu/newsearchmngs.php"


def _response(body: bytes) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=URL,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_field_search_preserves_cal_alternate_gender_pos() -> None:
    page = parse_gloss_search_page(_response(_fixture("search_gloss_field_alt_gender.html")))

    assert [(m.lemma.lemma_key, m.lemma.part_of_speech, m.lemma.gloss) for m in page.matches] == [
        (")yr) N", "n.m.", "medicament"),
        ("xyl N", "n.m.(f.)", "army; force"),
        ("qlyd N", "n.f./(m.)", "key"),
        ("gl#3 N", "n.m.(f.)", "tortoise"),
    ]
    assert page.matches[1].lemma.headwords == ("ḥyl", "ḥylˀ")
    assert page.matches[1].lemma.pronunciation == "ḥayl/ḥēl, ḥaylā"
    assert all(m.cross_reference_from is None for m in page.matches)


def test_gloss_search_keeps_cal_repeated_row_and_exposes_redirect_source() -> None:
    page = parse_gloss_search_page(_response(_fixture("search_gloss_camel_redirect.html")))

    assert [m.lemma.lemma_key for m in page.matches] == ["n)qh N", "n)qh N"]
    assert [m.cross_reference_from for m in page.matches] == [None, "nqh N"]
    assert page.matches[0].lemma == page.matches[1].lemma
    assert page.matches[1].lemma.aliases == ()
    assert page.matches[1].lemma.gloss == "female camel"


def test_gloss_match_serialization_is_flat_with_cross_reference_field() -> None:
    from cal_mcp.search import _gloss_match_to_dict

    page = parse_gloss_search_page(_response(_fixture("search_gloss_camel_redirect.html")))

    assert _gloss_match_to_dict(page.matches[1]) == {
        "lemma_key": "n)qh N",
        "headwords": ["nˀqh", "nˀqtˀ"],
        "pronunciation": "nāqā, nāqṯā",
        "part_of_speech": "n.f.",
        "gloss": "female camel",
        "aliases": [],
        "cross_reference_from": "nqh N",
    }


@pytest.mark.parametrize(
    ("needle", "replacement"),
    [
        ('<span class="uni">nqh N </span>⟹', "stray text "),
        ('<span class="uni">nqh N </span>⟹', '<span class="uni">nqh N </span>⟹⟹'),
        ('<span class="uni">nqh N </span>⟹', "⟹"),
        ('<span class="uni">nqh N </span>⟹', '<span class="uni">nqh N </span>⟹ x → '),
    ],
)
def test_gloss_search_row_prefix_drift_fails_closed(needle: str, replacement: str) -> None:
    body = _fixture("search_gloss_camel_redirect.html").decode()
    assert needle in body
    with pytest.raises(SearchParseError):
        parse_gloss_search_page(_response(body.replace(needle, replacement, 1).encode()))


def test_gloss_search_row_with_two_lemma_links_fails_closed() -> None:
    body = _fixture("search_gloss_camel_redirect.html").decode()
    needle = '<span class="uni">nqh N </span>⟹'
    doubled = '<a href="oneentry.php?lemma=nqh N&cits=all">nqh n.f.</a> ⟹'
    with pytest.raises(SearchParseError):
        parse_gloss_search_page(_response(body.replace(needle, doubled, 1).encode()))


# CAL evidence (R-062) has the group without "?"; a combined "?" form is not evidenced or pinned.
@pytest.mark.parametrize("token", ["n.m.(f.)", "n.f./(m.)", "n.m./f.", "n.f.?"])
def test_pos_grammar_accepts_secondary_gender(token: str) -> None:
    assert _looks_like_pos_token(token)


@pytest.mark.parametrize(
    "token",
    ["n.m.(f.", "n.m.()", "n.m.(f.)(m.)", "(f.)", "n.m.(ḥ.)", "n.m.(f)", "n.?f.", "#3"],
)
def test_pos_grammar_rejects_other_parentheses(token: str) -> None:
    assert not _looks_like_pos_token(token)


@pytest.mark.parametrize(
    "fixture",
    ["search_gloss_camel_redirect.html", "search_gloss_field_alt_gender.html"],
)
def test_gloss_row_without_its_gloss_span_fails_closed(fixture: str) -> None:
    # A missing final gloss must not silently take the next rendered text, such as CAL's footer.
    body = _fixture(fixture).decode()
    last = body.rindex('<span class="gloss">')
    end = body.index("</span>", last) + len("</span>")
    footer = "<hr><div>© The Comprehensive Aramaic Lexicon ©</div>"
    with pytest.raises(SearchParseError):
        parse_gloss_search_page(_response((body[:last] + body[end:] + footer).encode()))


@pytest.mark.parametrize("pos", ["n.m.(f.)", "n.f./(m.)"])
def test_lexicon_entry_header_keeps_secondary_gender_pos(pos: str) -> None:
    body = _fixture("entry_br_n.html").decode().replace("brā) n.m. son", f"brā) {pos} son", 1)
    entry = parse_lexicon_entry(_response(body.encode()), lemma_key="br N")

    assert entry.lemma.part_of_speech == pos
    assert entry.lemma.gloss == "son"
    assert entry.lemma.headwords == ("br", "brˀ")


def test_lexicon_browse_row_keeps_secondary_gender_pos() -> None:
    body = (
        '<a href="oneentry.php?lemma=xyl N&cits=all"><span class="lem">ḥyl, ḥylˀ</span> '
        '(<span class="uni">ḥayl/ḥēl, ḥaylā</span>) <pos>n.m.(f.)</pos></a><br>army; force'
    )
    page = parse_lexicon_browse_page(_response(body.encode()))

    assert [(e.lemma_key, e.part_of_speech, e.gloss) for e in page.entries] == [
        ("xyl N", "n.m.(f.)", "army; force")
    ]
