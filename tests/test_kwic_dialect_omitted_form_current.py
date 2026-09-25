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
    with pytest.raises(ConcordanceParseError):
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
