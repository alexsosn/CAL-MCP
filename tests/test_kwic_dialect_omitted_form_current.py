"""Issue #176: CAL can omit the requested form on a one-dialect KWIC page.

See docs/research/issue-176-kwic-omitted-form.md and D-014 (amended).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import ConcordanceParseError, ConcordanceService, KwicResult

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
OMITTED = FIXTURES / "kwic_dialect_nqh_71_current.html"
LISTED = FIXTURES / "kwic_dialect_nqh_n_forms_current.html"


async def _dialect(body: bytes, dialect_id: str) -> KwicResult:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config, request
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/show1dialectKWIC.php?lemma=n%29qh&pos=N&texts={dialect_id}",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        return await ConcordanceService(client).kwic_dialect("n)qh N", dialect_id)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_page_listing_only_other_forms_is_reported_as_such() -> None:
    result = await _dialect(OMITTED.read_bytes(), "71")
    data = result.to_dict()

    assert data["forms"] == [
        {"lemma_key": "n)qt) N", "total": 1},
        {"lemma_key": "nqh N", "total": 0},
    ]
    assert data["requested_form_listed"] is False
    assert data["total"] == 1
    assert data["empty_scope_ids"] == []
    assert [hit["form_lemma_key"] for hit in data["hits"]] == ["n)qt) N"]
    assert data["lemma_key"] == "n)qh N"


@pytest.mark.anyio
async def test_page_listing_the_requested_form_says_so() -> None:
    result = await _dialect(LISTED.read_bytes(), "6")
    assert result.to_dict()["requested_form_listed"] is True


@pytest.mark.anyio
async def test_omitted_form_page_still_cross_checks_counts() -> None:
    body = OMITTED.read_text(encoding="utf-8").replace(
        "<b>1</b> example found for <b>n)qt) N</b>", "<b>2</b> examples found for <b>n)qt) N</b>", 1
    )
    assert "<b>2</b> examples found" in body
    with pytest.raises(ConcordanceParseError, match="count|hits|total"):
        await _dialect(body.encode(), "71")


@pytest.mark.anyio
async def test_text_scope_reports_no_form_listing() -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config, request
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/showdialectKWIC.php",
            body=(FIXTURES / "kwic_texts_mlk_br_current.html").read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        result = await ConcordanceService(client).kwic_texts("mlk N", ["12250", "13250"])
    finally:
        await client.aclose()
    assert result.to_dict()["requested_form_listed"] is None


@pytest.mark.anyio
async def test_requested_form_listed_after_another_form_is_still_listed() -> None:
    # #176 review: the flag must not depend on the requested form being listed first.
    body = OMITTED.read_text(encoding="utf-8").replace(
        "No examples found for <b>nqh N</b> in dialect 71",
        "No examples found for <b>n)qh N</b> in dialect 71",
        1,
    )
    result = await _dialect(body.encode(), "71")
    assert [form.lemma_key for form in result.forms] == ["n)qt) N", "n)qh N"]
    assert result.to_dict()["requested_form_listed"] is True


@pytest.mark.anyio
@pytest.mark.parametrize(
    "heading",
    [
        "Looking for <b>nqh N</b> in  71",  # another lemma
        "Looking for <b>n)qt) N</b> in  71",  # the related form CAL listed
        "Looking for <b>n)qh N</b> in  6",  # another dialect
    ],
)
async def test_page_for_another_lemma_or_dialect_fails_closed(heading: str) -> None:
    # With the requested form no longer required, the page heading is what ties the
    # page to the request (#176 review).
    body = OMITTED.read_text(encoding="utf-8").replace(
        "Looking for <b>n)qh N</b> in  71", heading, 1
    )
    assert heading in body
    with pytest.raises(ConcordanceParseError, match="heading"):
        await _dialect(body.encode(), "71")
