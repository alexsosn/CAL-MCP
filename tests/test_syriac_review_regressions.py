from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LexiconLookupService, LexiconLookupStatus
from cal_mcp.syriac import parse_syriac_text_category_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 5, 16, 30, tzinfo=UTC)


def _inline_response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


@pytest.mark.parametrize(
    ("category", "heading", "url"),
    [
        ("nt-peshitta", "NT Peshiṭta", "https://cal.huc.edu/nt_peshitta.html"),
        (
            "apocryphal-pseudepigraphal",
            "Apocryphal/Pseudepigraphal Texts",
            "https://cal.huc.edu/apocryphal_pseudepigraphal.html",
        ),
    ],
)
def test_static_syriac_category_headings_match_current_cal(
    category: str,
    heading: str,
    url: str,
) -> None:
    page = parse_syriac_text_category_page(
        _inline_response(
            f"<h1>{heading}</h1><ul><li>"
            '<a href="/get_a_chapter.php?file=62001&amp;cset=S">62001</a> P Gn '
            '<a href="/get_file_info.php?coord=62001">ⓘ</a></li></ul>',
            url,
        ),
        category=category,
    )

    assert page.label == heading
    assert page.items[0].upstream_id == "62001"


def test_syriac_module_does_not_import_private_concordance_implementation() -> None:
    source = Path("src/cal_mcp/syriac.py").read_text(encoding="utf-8")
    assert "from cal_mcp.concordance import _validate_lemma_key" not in source


@pytest.mark.anyio
async def test_general_lexicon_service_accepts_syriac_script_without_ascii_rewrite() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        assert request == CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("first3", '"ܒܪ"'),),
        )
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/browseSKEYheaders.php?first3=%22%DC%92%DC%AA%22",
            body=(FIXTURES / "browse_b.html").read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=RETRIEVED_AT,
        )

    result = await LexiconLookupService(CalHttpClient(transport=transport)).lookup("ܒܪ")

    assert result.status is LexiconLookupStatus.AMBIGUOUS
    assert [item.lemma_key for item in result.matches] == ["br N", "br#2 N"]
    assert len(requests) == 1
