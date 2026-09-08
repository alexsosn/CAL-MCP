from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextParseError, TextService, parse_text_catalogue_page, parse_text_search_page

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_search_ginza.html"


def _response(body: bytes | None = None) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/newsearchtxts.php",
        body=FIXTURE.read_bytes() if body is None else body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
    )


def test_ginza_search_preserves_specialized_mandaic_results_in_cal_order() -> None:
    page = parse_text_search_page(_response())

    assert [
        (match.file_id, match.subtext_id, match.label, match.description)
        for match in page.matches
    ] == [
        (
            "74410",
            None,
            "Ginza Rabba (Great Treasury) Right Side",
            "prepared by M. Morgenstern from the Petermann edition and collated manuscripts.",
        ),
        (
            "74411",
            None,
            "Ginza Rabba (Great Treasury) Left Side",
            "Ginza Smala prepared from the Petermann edition and known manuscripts by M. Morgenstern.",
        ),
    ]


class GinzaSearchTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if request == CalRequest(
            method="POST",
            path="newsearchtxts.php",
            data=(("search", "Ginza"),),
        ):
            return _response()
        raise AssertionError(f"unexpected CAL request: {request}")


@pytest.mark.anyio
async def test_ginza_search_uses_one_existing_post_without_followup() -> None:
    transport = GinzaSearchTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).search("Ginza")
    finally:
        await client.aclose()

    assert [match.file_id for match in result.matches] == ["74410", "74411"]
    assert result.provenance.original_query == "Ginza"
    assert result.provenance.submitted_query == "Ginza"
    assert transport.requests == [
        CalRequest(
            method="POST",
            path="newsearchtxts.php",
            data=(("search", "Ginza"),),
        )
    ]


@pytest.mark.parametrize(
    "href",
    [
        "/showsubtexts.php?subtext=&cset=M",
        "/showsubtexts.php?subtext=abc&cset=M",
        "/showsubtexts.php?subtext=74410&subtext=74411&cset=M",
        "/showsubtexts.php?subtext=74410",
        "/showsubtexts.php?subtext=74410&cset=",
        "/showsubtexts.php?subtext=74410&cset=X",
        "/showsubtexts.php?subtext=74410&cset=M&cset=M",
    ],
)
def test_malformed_mandaic_search_result_fails_closed(href: str) -> None:
    body = FIXTURE.read_text().replace(
        "/showsubtexts.php?subtext=74410&amp;cset=M",
        href.replace("&", "&amp;"),
        1,
    )

    with pytest.raises(TextParseError, match="Mandaic text search result"):
        parse_text_search_page(_response(body.encode()))


def test_catalogue_semantics_for_showsubtexts_link_are_not_reinterpreted() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/newtextmenu.html",
        body=(
            b'<html><body><a href="showsubtexts.php?subtext=74410&amp;cset=M">'
            b"Mandaic entry</a></body></html>"
        ),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
    )

    page = parse_text_catalogue_page(response)

    assert page.texts == ()
    assert [(category.category_id, category.label) for category in page.categories] == [
        ("74410", "Mandaic entry")
    ]
