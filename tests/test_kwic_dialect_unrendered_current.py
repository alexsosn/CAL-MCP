"""Issue #266: preserve CAL's diagnostic-only KWIC hits, never forge them."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    ConcordanceProvenance,
    KwicResult,
    KwicScopeKind,
    parse_kwic_result,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "kwic_dialect_aryk2_a_br_current.html"
_SOURCE = "https://cal.huc.edu/show1dialectKWIC.php?lemma=mlk&pos=N&texts=71"
_NOTICE = "error: line not found for 71600222x004133"
_STAMP = datetime(2026, 10, 10, tzinfo=UTC)


def _reduced_current_dialect_page() -> str:
    """Retain observed BR-line structure, replace quoted scholarly context minimally."""
    body = _FIXTURE.read_text(encoding="utf-8")
    body = body.replace(")ryk#2 A", "mlk N")
    body = body.replace(" in  3<br>", " in  71<br>")
    old = "<b>1</b> example found for <b>mlk N</b> in dialect 3"
    assert old in body
    body = body.replace(old, "<b>2</b> examples found for <b>mlk N</b> in dialect 71")
    old_end = '</p><div dir="ltr"'
    assert old_end in body
    return body.replace(old_end, f"</p><p>{_NOTICE}<br></p><div dir=\"ltr\"", 1)


def _parse(body: str):
    response = CalResponse(
        status_code=200,
        url=_SOURCE,
        body=body.encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_STAMP,
    )
    return parse_kwic_result(
        response,
        lemma_key="mlk N",
        scope_kind=KwicScopeKind.DIALECT,
        scope_ids=("71",),
    )


def test_explicit_cal_unrendered_hit_preserves_source_total_and_order() -> None:
    page = _parse(_reduced_current_dialect_page())
    assert page.total == 2
    assert len(page.hits) == 1
    assert len(page.unrendered_hits) == 1
    assert [form.total for form in page.forms] == [2]

    [missing] = page.unrendered_hits
    assert missing.coordinate == "71600222x004133"
    assert missing.message == _NOTICE
    assert missing.form_lemma_key == "mlk N"
    assert not hasattr(missing, "full_context_url")


def test_public_kwic_result_serializes_diagnostic_without_forged_target() -> None:
    page = _parse(_reduced_current_dialect_page())
    result = KwicResult(
        lemma_key="mlk N",
        scope_kind=KwicScopeKind.DIALECT,
        scope_ids=("71",),
        total=page.total,
        hits=page.hits,
        empty_scope_ids=page.empty_scope_ids,
        provenance=ConcordanceProvenance(
            source="CAL",
            source_url=_SOURCE,
            retrieved_at=_STAMP,
            operation="kwic_dialect",
            lemma_key="mlk N",
            scope_ids=("71",),
        ),
        forms=page.forms,
        unrendered_hits=page.unrendered_hits,
    )
    data = result.to_dict()
    assert data["total"] == 2
    assert len(data["hits"]) == 1
    assert data["unrendered_hits"] == [
        {
            "coordinate": "71600222x004133",
            "message": _NOTICE,
            "form_lemma_key": "mlk N",
        }
    ]


@pytest.mark.parametrize(
    "bad",
    [
        _NOTICE.replace("71600222x004133", "not-a-coordinate"),
        _NOTICE.replace("71600222x004133", "71600222/004133"),
        "error: line not found for ",
        "surprise: found for 71600222x004133",
    ],
)
def test_unknown_or_invalid_diagnostic_does_not_hide_parser_drift(bad: str) -> None:
    with pytest.raises(ConcordanceParseError):
        _parse(_reduced_current_dialect_page().replace(_NOTICE, bad))


def test_wrong_total_does_not_ignore_diagnostic_or_recount_as_rendered() -> None:
    with pytest.raises(ConcordanceParseError):
        _parse(
            _reduced_current_dialect_page().replace(
                "<b>2</b> examples found for", "<b>3</b> examples found for"
            )
        )


def test_unrendered_line_after_last_form_summary_is_not_assigned_a_form() -> None:
    body = _reduced_current_dialect_page()
    notice = f"<p>{_NOTICE}<br></p>"
    assert notice in body
    body = body.replace(notice, "")
    body = body.replace("</span></div><hr>", f"{notice}</span></div><hr>")
    with pytest.raises(ConcordanceParseError):
        _parse(body)
