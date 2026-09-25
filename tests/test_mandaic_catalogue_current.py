"""Issue #169: the current (2026-09-25) Mandaic catalogue layout.

See docs/research/issue-169-mandaic-catalogue.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextCatalogueResult, TextParseError, TextService

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_catalogue_mandaic_current.html"


def _transport_for(body: bytes):  # type: ignore[no-untyped-def]
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        assert request.path == "show_Mandaic.php"
        assert request.params == (("R1", "74"),)
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/show_Mandaic.php?R1=74",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )

    return transport


async def _catalogue(body: bytes) -> TextCatalogueResult:
    client = CalHttpClient(transport=_transport_for(body))
    try:
        return await TextService(client).catalogue(category_id="74")
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_current_mandaic_catalogue_lists_texts_in_cal_order() -> None:
    result = await _catalogue(FIXTURE.read_bytes())

    assert [(text.file_id, text.subtext_id, text.label) for text in result.texts] == [
        ("74410", None, "Ginza Rabba (Great Treasury) Right Side"),
        ("74411", None, "Ginza Rabba (Great Treasury) Left Side"),
        ("74423", None, "Diwan Malkuta ˁlaita"),
        ("74923", None, "Diwan Malkuta ˁlaita"),
        ("74501", None, "Haran Gauaita"),
        ("74701", None, "Mandaic Magic Bowls"),
    ]
    assert result.categories == ()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        # Mandaic-script rows are never requested.
        ("subtext=74410&cset=R", "subtext=74410&cset=J", "cset"),
        ("file=74501&cset=R", "file=74501&cset=X", "cset"),
        # The information link names another file.
        ('get_file_info.php?coord=74411"', 'get_file_info.php?coord=74412"', "information link"),
        # A route link with no title.
        (">Haran Gauaita</a>", "></a>", "label|title"),
        # A current row must show only its title (#169 re-review).
        (">Haran Gauaita</a>", ">Haran Gauaita</a> (fragment)", "unexpected text"),
        # A digits-only "title" on a current (cset=R) row (#169 review).
        (">Haran Gauaita</a>", ">74401</a>", "unexpected text"),
        # A current-script row in the earlier id-anchor shape.
        (
            'file=74501&cset=R">Haran Gauaita</a>',
            'file=74501&cset=R">74501</a> Haran Gauaita',
            "unexpected text",
        ),
        # An earlier-layout (cset=M) row whose anchor is a title, not the file id.
        (
            'file=74501&cset=R">Haran Gauaita</a>',
            'file=74501&cset=M">Haran Gauaita</a>',
            "mislabeled",
        ),
        # An earlier-layout row whose id anchor names another file, with no trailing text.
        ('file=74501&cset=R">Haran Gauaita</a>', 'file=74501&cset=M">74401</a>', "mislabeled"),
        # A title-less route link with a single-quoted href must not vanish.
        (
            "</ul>\n</details>\n\n<details>",
            "<li><a href='/showsubtexts.php?subtext=74999&cset=R'></a></li></ul>\n</details>"
            "\n\n<details>",
            "without a rendered title",
        ),
        # The same file listed twice (route and information link agree).
        (
            'subtext=74923&cset=R">Diwan Malkuta &#x2C1;laita</a> '
            '<a href="/get_file_info.php?coord=74923"',
            'subtext=74423&cset=R">Diwan Malkuta &#x2C1;laita</a> '
            '<a href="/get_file_info.php?coord=74423"',
            "repeats a file identifier",
        ),
    ],
)
async def test_unexpected_current_rows_fail_closed(old: str, new: str, message: str) -> None:
    body = FIXTURE.read_text(encoding="utf-8")
    assert old in body
    with pytest.raises(TextParseError, match=message):
        await _catalogue(body.replace(old, new, 1).encode())


@pytest.mark.anyio
async def test_information_link_with_a_return_query_is_not_a_route_link() -> None:
    body = FIXTURE.read_text(encoding="utf-8").replace(
        'get_file_info.php?coord=74410"',
        'get_file_info.php?coord=74410&return=/showsubtexts.php?subtext=74410&amp;script=R"',
        1,
    )
    assert "return=/showsubtexts.php" in body
    result = await _catalogue(body.encode())
    assert [text.file_id for text in result.texts][:2] == ["74410", "74411"]


@pytest.mark.anyio
async def test_route_links_inside_scripts_are_not_counted() -> None:
    body = FIXTURE.read_text(encoding="utf-8").replace(
        "</body>",
        "<script>var x = '<a href=\"/showsubtexts.php?subtext=74999&cset=R\">';</script></body>",
        1,
    )
    result = await _catalogue(body.encode())
    assert len(result.texts) == 6
