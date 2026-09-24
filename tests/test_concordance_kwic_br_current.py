"""Issue #149: current (2026-09-24) concordance/KWIC markup.

See docs/research/issue-149-concordance-kwic-drift.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    ConcordanceService,
    KwicScopeKind,
    parse_kwic_result,
    parse_text_concordance_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 24, tzinfo=UTC)
CONCORDANCE_URL = "https://cal.huc.edu/newconcord.php?text=13250&cset=S"
TEXTS_URL = "https://cal.huc.edu/showdialectKWIC.php"
ARYK_URL = "https://cal.huc.edu/show1dialectKWIC.php?lemma=%29ryk%232&pos=A&texts=3"
NQH_URL = "https://cal.huc.edu/show1dialectKWIC.php?lemma=n%29qh&pos=N&texts=6"
NQH_ZERO_URL = "https://cal.huc.edu/show1dialectKWIC.php?lemma=n%29qh&pos=N&texts=51"


def _response(body: str | bytes, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body if isinstance(body, bytes) else body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _nqh(body: str) -> object:
    return parse_kwic_result(
        _response(body, NQH_URL),
        lemma_key="n)qh N",
        scope_kind=KwicScopeKind.DIALECT,
        scope_ids=("6",),
    )


def test_current_concordance_row_preserves_display_label_and_link_key() -> None:
    page = parse_text_concordance_page(
        _response(_fixture("concordance_text_13250_label_current.html"), CONCORDANCE_URL),
        requested_text_id="13250",
        requested_charset="S",
    )

    assert [(item.frequency, item.lemma_key, item.label, item.gloss) for item in page.lemmas] == [
        (4, ")b N", "ˀb, ˀbˀ n.m.", "father"),
        (1, ")x)b PN", ")x)b PN", "proper noun"),
        (6, "mlk N", "mlk, mlkˀ n.m.", "king"),
    ]


@pytest.mark.parametrize("link_text", ["", " "])
def test_concordance_row_requires_a_nonempty_label(link_text: str) -> None:
    # The inline BR layout rejects an empty link earlier (the link is missing from its
    # rendered row); the table layout reaches the label check itself.
    body = (
        "<html><body><div>Frequencies of lemmas in text 13250</div><table><tr><td>4:</td>"
        '<td><a href="/showKWIC.php?lemma=%29b+N&charset=S&texts=13250">'
        f"{link_text}</a></td><td>: father</td></tr></table></body></html>"
    )

    with pytest.raises(ConcordanceParseError, match="lemma link has no label"):
        parse_text_concordance_page(
            _response(body, CONCORDANCE_URL),
            requested_text_id="13250",
            requested_charset="S",
        )


def test_current_text_kwic_parses_br_line_hits_with_duplicates_and_empty_scope() -> None:
    page = parse_kwic_result(
        _response(_fixture("kwic_texts_mlk_br_current.html"), TEXTS_URL),
        lemma_key="mlk N",
        scope_kind=KwicScopeKind.TEXTS,
        scope_ids=("12250", "13250"),
    )

    assert page.total == 3
    assert page.empty_scope_ids == ("12250",)
    assert page.forms == ()
    assert [
        (hit.file_id, hit.subtext_id, hit.target_coordinate, hit.charset, hit.form_lemma_key)
        for hit in page.hits
    ] == [
        ("13250", None, "1325003", "R", None),
        ("13250", None, "1325006", "R", None),
        ("13250", None, "1325006", "R", None),
    ]
    assert page.hits[0].context == "wy$kb | )by | yhk | )l[ | )bht]h | wy(l mlk y[$"
    assert page.hits[0].full_context_url == (
        "https://cal.huc.edu/get_a_kwicchapter.php?file=13250&sub=&cset=R&target=1325003"
    )


def test_current_single_form_dialect_kwic_reports_its_form() -> None:
    page = parse_kwic_result(
        _response(_fixture("kwic_dialect_aryk2_a_br_current.html"), ARYK_URL),
        lemma_key=")ryk#2 A",
        scope_kind=KwicScopeKind.DIALECT,
        scope_ids=("3",),
    )

    assert page.total == 1
    assert [(form.lemma_key, form.total) for form in page.forms] == [(")ryk#2 A", 1)]
    [hit] = page.hits
    assert (hit.file_id, hit.subtext_id, hit.target_coordinate, hit.charset) == (
        "31000",
        "4",
        "31000414",
        "H",
    )
    assert hit.form_lemma_key == ")ryk#2 A"
    assert hit.context.startswith("כְּעַן")
    assert "31000414" not in hit.context


def test_current_multi_form_dialect_kwic_keeps_variant_form_hits() -> None:
    page = _nqh(_fixture("kwic_dialect_nqh_n_forms_current.html"))

    assert page.total == 1
    assert page.empty_scope_ids == ()
    assert [(form.lemma_key, form.total) for form in page.forms] == [("n)qh N", 0), ("nqh N", 1)]
    [hit] = page.hits
    assert (hit.file_id, hit.subtext_id, hit.target_coordinate, hit.charset) == (
        "60301",
        "53",
        "603015323",
        "U",
    )
    assert hit.form_lemma_key == "nqh N"


def test_current_all_zero_dialect_kwic_is_valid_empty_result() -> None:
    page = parse_kwic_result(
        _response(_fixture("kwic_dialect_nqh_n_zero_current.html"), NQH_ZERO_URL),
        lemma_key="n)qh N",
        scope_kind=KwicScopeKind.DIALECT,
        scope_ids=("51",),
    )

    assert page.total == 0
    assert page.hits == ()
    assert page.empty_scope_ids == ("51",)
    assert [(form.lemma_key, form.total) for form in page.forms] == [("n)qh N", 0), ("nqh N", 0)]


_FORMS = "kwic_dialect_nqh_n_forms_current.html"
_FOUND_NQH = "<b>1</b> example found for <b>nqh N</b> in dialect 6"
_NONE_REQUESTED = "No examples found for <b>n)qh N</b> in dialect 6"


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        # Form count disagrees with the hits it owns (grand total kept consistent).
        (
            _FOUND_NQH + '</div><br><BDO dir="rtl"></BDO></span></div>'
            '<div dir="ltr" style="font-family:sans-serif; font-size:13px;">Grand total: <b>1</b>',
            "<b>2</b> examples found for <b>nqh N</b> in dialect 6"
            '</div><br><BDO dir="rtl"></BDO></span></div>'
            '<div dir="ltr" style="font-family:sans-serif; font-size:13px;">Grand total: <b>2</b>',
            "does not match parsed target hits",
        ),
        # Summary names another dialect.
        (
            _FOUND_NQH,
            "<b>1</b> example found for <b>nqh N</b> in dialect 7",
            "contradicts the request",
        ),
        # Requested form missing.
        (
            _NONE_REQUESTED,
            "No examples found for <b>nqh#2 N</b> in dialect 6",
            "lacks the requested form",
        ),
        # Requested form duplicated.
        (
            _FOUND_NQH,
            "<b>1</b> example found for <b>n)qh N</b> in dialect 6",
            "repeats a form summary",
        ),
        # Non-canonical form key.
        (
            _FOUND_NQH,
            "<b>1</b> example found for <b>nqh  N x</b> in dialect 6",
            "invalid form key",
        ),
        # Grand total disagrees with the per-form sum.
        (
            "Grand total: <b>1</b> example",
            "Grand total: <b>2</b> examples",
            "grand total contradicts",
        ),
        # Hit link text is not the target coordinate.
        (
            '">603015323</span></a>',
            '">603015324</span></a>',
            "differs from its coordinate",
        ),
        # Unknown hit charset.
        ("cset=U&target", "cset=Q&target", "unknown charset"),
    ],
)
def test_current_dialect_kwic_contradictions_fail_closed(old: str, new: str, message: str) -> None:
    body = _fixture(_FORMS)
    assert old in body
    with pytest.raises(ConcordanceParseError, match=message):
        _nqh(body.replace(old, new, 1))


def test_current_dialect_kwic_rejects_hits_owned_by_a_no_examples_form() -> None:
    body = _fixture(_FORMS)
    # Move the requested form's "No examples" summary after the hit block, so the
    # hit falls inside a zero-count form.
    body = body.replace(
        f'<div dir="ltr" style="text-align:left; font-family:sans-serif; font-size:13px;">'
        f"{_NONE_REQUESTED}</div><br>",
        "",
    ).replace(
        "</p>",
        f"</p><div>{_NONE_REQUESTED}</div>",
    )
    with pytest.raises(ConcordanceParseError, match="does not match parsed target hits"):
        _nqh(body)


def test_current_dialect_kwic_rejects_hit_after_last_form_summary() -> None:
    body = _fixture(_FORMS).replace(
        "Grand total:",
        '<a href="/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015330">'
        "603015330</a> x <b>ܢܩܬܐ</b><br>Grand total:",
    )
    with pytest.raises(ConcordanceParseError, match="follows the last form summary"):
        _nqh(body)


def test_current_dialect_kwic_rejects_repeated_form_summary() -> None:
    body = _fixture(_FORMS).replace(
        "Grand total:",
        "<div>No examples found for <b>nqh N</b> in dialect 6</div>Grand total:",
    )
    with pytest.raises(ConcordanceParseError, match="repeats a form summary"):
        _nqh(body)


@pytest.mark.parametrize(
    ("target_line", "message"),
    [
        (
            'x <a href="/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323">'
            "603015323</a> ܢܩܬܐ",
            "does not start with its coordinate",
        ),
        (
            '<a href="/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323">'
            "603015323</a>",
            "no rendered context",
        ),
        (
            '<a href="/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323">'
            '603015323</a> ܢܩܬܐ <a href="/getlex.php?coord=1&word=0">x</a>',
            "unexpected links",
        ),
    ],
)
def test_current_kwic_malformed_target_line_fails_closed(target_line: str, message: str) -> None:
    body = _fixture(_FORMS)
    start = body.index('<a href="/get_a_kwicchapter.php')
    end = body.index("<br>", start)
    with pytest.raises(ConcordanceParseError, match=message):
        _nqh(body[:start] + target_line + body[end:])


def test_kwic_result_serializes_forms_and_hit_form_keys() -> None:
    page = _nqh(_fixture(_FORMS))
    from cal_mcp.concordance import ConcordanceProvenance, _kwic_result

    result = _kwic_result(
        "n)qh N",
        KwicScopeKind.DIALECT,
        page,
        ConcordanceProvenance(
            source="CAL",
            source_url=NQH_URL,
            retrieved_at=RETRIEVED_AT,
            operation="kwic_dialect",
            lemma_key="n)qh N",
            scope_ids=("6",),
        ),
    ).to_dict()

    assert result["forms"] == [
        {"lemma_key": "n)qh N", "total": 0},
        {"lemma_key": "nqh N", "total": 1},
    ]
    hits = result["hits"]
    assert isinstance(hits, list)
    assert hits[0]["form_lemma_key"] == "nqh N"
    assert hits[0]["charset"] == "U"


class _RecordingClient:
    def __init__(self) -> None:
        self.requests: list[object] = []

    async def fetch(self, request: object, *, parser: object, cache_namespace: str) -> object:
        self.requests.append(request)
        raise _Stop


class _Stop(Exception):
    pass


@pytest.mark.anyio
async def test_full_context_accepts_current_unicode_syriac_charset() -> None:
    client = _RecordingClient()
    with pytest.raises(_Stop):
        await ConcordanceService(client).kwic_full_context(  # type: ignore[arg-type]
            "60301",
            "603015323",
            "U",
            subtext_id="53",
        )
    [request] = client.requests
    assert ("cset", "U") in request.params  # type: ignore[attr-defined]


def test_concordance_lemma_serializes_label() -> None:
    from cal_mcp.concordance import _concordance_lemma_to_dict

    page = parse_text_concordance_page(
        _response(_fixture("concordance_text_13250_label_current.html"), CONCORDANCE_URL),
        requested_text_id="13250",
        requested_charset="S",
    )
    assert _concordance_lemma_to_dict(page.lemmas[0])["label"] == "ˀb, ˀbˀ n.m."


def test_current_kwic_hits_carry_cal_highlighted_target_token() -> None:
    texts = parse_kwic_result(
        _response(_fixture("kwic_texts_mlk_br_current.html"), TEXTS_URL),
        lemma_key="mlk N",
        scope_kind=KwicScopeKind.TEXTS,
        scope_ids=("12250", "13250"),
    )
    # Two occurrences on line 1325006 share a coordinate and rendered line; CAL's
    # highlighted token is what tells them apart.
    assert [(hit.target_coordinate, hit.target_text) for hit in texts.hits] == [
        ("1325003", "mlk"),
        ("1325006", "mlky"),
        ("1325006", "ml?[kN"),
    ]
    dialect = _nqh(_fixture(_FORMS))
    assert [hit.target_text for hit in dialect.hits] == ["ܢܩܬܐ"]


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        # No highlighted token on the target line.
        ("&nbsp;&nbsp;<b>mlk&nbsp;&nbsp; </b>y[$", "mlk y[$", "highlighted target token"),
        # Two highlighted tokens on one target line.
        (
            "&nbsp;&nbsp;<b>mlk&nbsp;&nbsp; </b>y[$",
            "<b>mlk</b> <b>y[$</b>",
            "highlighted target token",
        ),
        # Text before the link that happens to repeat the coordinate.
        (
            '<a href="/get_a_kwicchapter.php?file=13250&sub=&cset=R&target=1325003">',
            '1325003 <a href="/get_a_kwicchapter.php?file=13250&sub=&cset=R&target=1325003">',
            "does not start with its coordinate",
        ),
        # A hit rendered under another requested text's section header.
        (
            "<b>12250:</b><br>no examples found in 12250<br><b>13250:</b>",
            "<b>12250:</b>",
            "another text",
        ),
    ],
)
def test_current_text_kwic_target_structure_fails_closed(old: str, new: str, message: str) -> None:
    body = _fixture("kwic_texts_mlk_br_current.html")
    assert old in body
    with pytest.raises(ConcordanceParseError, match=message):
        parse_kwic_result(
            _response(body.replace(old, new, 1), TEXTS_URL),
            lemma_key="mlk N",
            scope_kind=KwicScopeKind.TEXTS,
            scope_ids=("12250", "13250"),
        )


def test_unicode_syriac_full_context_page_parses_offline() -> None:
    from cal_mcp.concordance import KwicFullContextStatus, parse_kwic_full_context_page

    url = "https://cal.huc.edu/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323"
    page = parse_kwic_full_context_page(
        _response(_fixture("kwic_full_context_syr_romlaw_unicode.html"), url),
        requested_file_id="60301",
        requested_subtext_id="53",
        requested_target_coordinate="603015323",
        requested_charset="U",
    )

    assert page.status is KwicFullContextStatus.FOUND
    assert [line.coordinate for line in page.lines] == ["603015322", "603015323", "603015324"]
    target = page.lines[1]
    assert target.tokens[-1].text == "ܢܩܬܐ"
    assert [token.word_index for token in target.tokens] == list(range(8))


_ARYK_TABLE_URL = ARYK_URL


def _aryk_table(body: str) -> object:
    return parse_kwic_result(
        _response(body, _ARYK_TABLE_URL),
        lemma_key=")ryk#2 A",
        scope_kind=KwicScopeKind.DIALECT,
        scope_ids=("3",),
    )


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        # Form summaries mixed with a text-style total.
        ("Grand total:", "total examples: 1<br>Grand total:", "mixes form summaries and a total"),
        # Form summaries mixed with a scope-level empty marker.
        ("Grand total:", "no examples found in 6<br>Grand total:", "mixes form and scope markers"),
        # A summary-like line that is not one of CAL's summary shapes.
        (
            "Grand total:",
            "<div>1 example found for <b>nqh N</b> in dialect six</div>Grand total:",
            "unrecognized form summary",
        ),
        # Two grand totals.
        (
            "<hr>",
            '<div dir="ltr">Grand total: <b>1</b> example across all forms</div><hr>',
            "repeats its grand total",
        ),
        # A dialect target line that runs into the following coordinate line.
        (
            '&nbsp;<br><span class="mono" dir="ltr" style="display:inline-block;">603015324',
            '&nbsp;<span class="mono" dir="ltr" style="display:inline-block;">603015324',
            "runs into another line",
        ),
        # No whitespace between the coordinate link and the rendered line.
        ('">603015323</span></a> ', '">603015323</span></a>', "does not start with its coordinate"),
    ],
)
def test_current_dialect_kwic_structure_guards_fail_closed(
    old: str, new: str, message: str
) -> None:
    body = _fixture(_FORMS)
    assert old in body
    with pytest.raises(ConcordanceParseError, match=message):
        _nqh(body.replace(old, new, 1))


def test_current_text_kwic_rejects_dialect_form_summaries() -> None:
    body = _fixture("kwic_texts_mlk_br_current.html").replace(
        "total examples: 3",
        "1 example found for mlk N in dialect 13250<br>total examples: 3",
    )
    with pytest.raises(ConcordanceParseError, match="contains dialect form summaries"):
        parse_kwic_result(
            _response(body, TEXTS_URL),
            lemma_key="mlk N",
            scope_kind=KwicScopeKind.TEXTS,
            scope_ids=("12250", "13250"),
        )


def test_earlier_table_dialect_layout_still_checks_summary_count() -> None:
    body = _fixture("kwic_dialect_aryk2_a_biblical.html")
    assert _aryk_table(body) is not None
    with pytest.raises(ConcordanceParseError, match="does not match parsed target hits"):
        _aryk_table(body.replace("1 example found for", "2 examples found for", 1))


def test_earlier_table_dialect_layout_rejects_grand_total_without_forms() -> None:
    body = _fixture("kwic_dialect_aryk2_a_biblical.html").replace(
        "1 example found for )ryk#2 A in dialect 3",
        "total examples: 1</div><div>Grand total: 1 example across all forms",
    )
    with pytest.raises(ConcordanceParseError, match="grand total lacks form summaries"):
        _aryk_table(body)


def test_target_structure_must_agree_with_parsed_hit_lines() -> None:
    from dataclasses import replace

    from cal_mcp.concordance import _apply_kwic_target_structure

    response = _response(_fixture(_FORMS), NQH_URL)
    [(index, hit)] = [(i, h) for i, h in enumerate(_nqh(_fixture(_FORMS)).hits)]
    with pytest.raises(ConcordanceParseError, match="disagree with their links"):
        _apply_kwic_target_structure(response, (), scope_kind=KwicScopeKind.DIALECT)
    moved = replace(hit, full_context_url=hit.full_context_url.replace("603015323", "1"))
    with pytest.raises(ConcordanceParseError, match="disagree with their links"):
        _apply_kwic_target_structure(
            response,
            ((index, moved),),
            scope_kind=KwicScopeKind.DIALECT,
        )
