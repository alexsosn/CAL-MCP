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


def test_current_concordance_row_still_requires_a_nonempty_label() -> None:
    body = _fixture("concordance_text_13250_label_current.html").replace(
        ">ˀb, ˀbˀ n.m.</a>", "></a>"
    )

    with pytest.raises(ConcordanceParseError):
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
    ("old", "new"),
    [
        # Form count disagrees with the hits it owns.
        (_FOUND_NQH, "<b>2</b> examples found for <b>nqh N</b> in dialect 6"),
        # Summary names another dialect.
        (_FOUND_NQH, "<b>1</b> example found for <b>nqh N</b> in dialect 7"),
        # Requested form missing.
        (_NONE_REQUESTED, "No examples found for <b>nqh#2 N</b> in dialect 6"),
        # Requested form duplicated.
        (_FOUND_NQH, "<b>1</b> example found for <b>n)qh N</b> in dialect 6"),
        # Non-canonical form key.
        (_FOUND_NQH, "<b>1</b> example found for <b>nqh  N x</b> in dialect 6"),
        # Grand total disagrees with the per-form sum.
        ("Grand total: <b>1</b> example", "Grand total: <b>2</b> examples"),
        # Hit link text is not the target coordinate.
        (
            '">603015323</span></a>',
            '">603015324</span></a>',
        ),
        # Unknown hit charset.
        ("cset=U&target", "cset=Q&target"),
    ],
)
def test_current_dialect_kwic_contradictions_fail_closed(old: str, new: str) -> None:
    body = _fixture(_FORMS)
    assert old in body
    with pytest.raises(ConcordanceParseError):
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
    with pytest.raises(ConcordanceParseError):
        _nqh(body)


def test_current_dialect_kwic_rejects_hit_after_last_form_summary() -> None:
    body = _fixture(_FORMS).replace(
        "Grand total:",
        '<a href="/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015330">'
        "603015330</a> ܢܩܬܐ<br>Grand total:",
    )
    with pytest.raises(ConcordanceParseError):
        _nqh(body)


def test_current_dialect_kwic_rejects_repeated_form_summary() -> None:
    body = _fixture(_FORMS).replace(
        "Grand total:",
        "<div>No examples found for <b>nqh N</b> in dialect 6</div>Grand total:",
    )
    with pytest.raises(ConcordanceParseError):
        _nqh(body)


@pytest.mark.parametrize(
    "target_line",
    [
        # Link text does not start the line.
        'x <a href="/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323">'
        "603015323</a> ܢܩܬܐ",
        # No rendered text after the coordinate.
        '<a href="/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323">603015323</a>',
        # An extra link on the target line.
        '<a href="/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323">'
        '603015323</a> ܢܩܬܐ <a href="/getlex.php?coord=1&word=0">x</a>',
    ],
)
def test_current_kwic_malformed_target_line_fails_closed(target_line: str) -> None:
    body = _fixture(_FORMS)
    start = body.index('<a href="/get_a_kwicchapter.php')
    end = body.index("<br>", start)
    with pytest.raises(ConcordanceParseError):
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
