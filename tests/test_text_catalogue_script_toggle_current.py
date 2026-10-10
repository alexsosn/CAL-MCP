"""Issue #264: CAL's script-display toggle is navigation, not a sub-category (R-082)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
PESHITTA_JOHN = FIXTURES / "text_catalogue_62043_script_toggle_current.html"
CPA_NODE = FIXTURES / "text_catalogue_cpa_55400122_script_toggle_current.html"


async def _catalogue(category_id: str, body: bytes):
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        assert dict(request.params) == {"subtext": category_id}
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/showsubtexts.php?subtext={category_id}",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        return await TextService(client).catalogue(category_id=category_id)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_peshitta_book_catalogue_returns_only_its_chapters() -> None:
    result = await _catalogue("62043", PESHITTA_JOHN.read_bytes())

    assert result.categories == ()
    assert [(text.file_id, text.subtext_id) for text in result.texts] == [
        ("62043", "01"),
        ("62043", "02"),
    ]


@pytest.mark.anyio
async def test_cpa_catalogue_node_returns_only_its_text() -> None:
    result = await _catalogue("55400122", CPA_NODE.read_bytes())

    assert result.categories == ()
    assert [(text.file_id, text.subtext_id, text.label) for text in result.texts] == [
        ("55400", "122", "Prodig2")
    ]


@pytest.mark.anyio
async def test_a_script_link_to_another_catalogue_is_still_a_category() -> None:
    # Only the page's own toggle is navigation; a script link naming another node is kept.
    body = PESHITTA_JOHN.read_bytes().replace(
        b'href="/showsubtexts.php?subtext=62043&script=R">Roman',
        b'href="/showsubtexts.php?subtext=62044&script=R">Roman',
    )

    result = await _catalogue("62043", body)

    assert [(category.category_id, category.label) for category in result.categories] == [
        ("62044", "Roman")
    ]


@pytest.mark.anyio
async def test_a_self_link_with_other_selectors_is_not_treated_as_the_toggle() -> None:
    # Only the exact observed toggle shape (subtext + one script selector) is navigation.
    body = PESHITTA_JOHN.read_bytes().replace(
        b'href="/showsubtexts.php?subtext=62043&script=R">Roman',
        b'href="/showsubtexts.php?subtext=62043&script=R&page=2">Roman',
    )

    result = await _catalogue("62043", body)

    assert [(category.category_id, category.label) for category in result.categories] == [
        ("62043", "Roman")
    ]
