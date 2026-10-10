"""Issue #256: Ginza Rabba (74410) row info links name the parent file (R-076)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextParseError, TextService

GINZA = (
    Path(__file__).parent
    / "fixtures"
    / "cal"
    / "text_catalogue_mandaic_74410_parent_info_current.html"
)


async def _child_catalogue(file_id: str, body: bytes):
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        assert request == CalRequest(
            method="GET", path="showsubtexts.php", params=(("subtext", file_id),)
        )
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/showsubtexts.php?subtext={file_id}",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).catalogue(category_id=file_id)
    finally:
        await client.aclose()
    return result, requests


@pytest.mark.anyio
async def test_ginza_rows_with_parent_file_info_links_are_kept_in_cal_order() -> None:
    result, _ = await _child_catalogue("74410", GINZA.read_bytes())

    assert [(item.file_id, item.subtext_id, item.label) for item in result.texts] == [
        ("74410", "001", "page 1"),
        ("74410", "002", "page 2"),
        ("74410", "003", "page 3"),
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "coordinate",
    [
        b"74411",  # another file
        b"7441",  # a prefix of the file id
        b"74410002",  # another row's subtext coordinate
    ],
)
async def test_row_info_link_naming_anything_else_still_fails_closed(coordinate: bytes) -> None:
    old = (
        b'sub=001&cset=J">page 1</a>\n'
        b'      <a class="info-link" href="/get_file_info.php?coord=74410&'
    )
    body = GINZA.read_bytes()
    assert old in body
    body = body.replace(old, old.replace(b"coord=74410&", b"coord=" + coordinate + b"&"))

    with pytest.raises(TextParseError, match="names another text"):
        await _child_catalogue("74410", body)
