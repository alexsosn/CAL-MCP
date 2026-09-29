"""Issue #181: current file-info coordinate on KWIC full-context pages of subdivided texts.

See docs/research/issue-181-full-context-subtext.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    KwicFullContextPage,
    KwicFullContextStatus,
    parse_kwic_full_context_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
SAMARITAN = FIXTURES / "kwic_full_context_samaritan_56000_112_current.html"
EZRA = FIXTURES / "kwic_full_context_ba_ezra_31000_4_current.html"
ROMLAW = FIXTURES / "kwic_full_context_syr_romlaw_unicode.html"


def _parse(
    body: bytes, file_id: str, sub: str | None, target: str, cset: str
) -> KwicFullContextPage:
    url = (
        f"https://cal.huc.edu/get_a_kwicchapter.php?file={file_id}&sub={sub or ''}"
        f"&cset={cset}&target={target}"
    )
    return parse_kwic_full_context_page(
        CalResponse(
            status_code=200,
            url=url,
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 29, tzinfo=UTC),
        ),
        requested_file_id=file_id,
        requested_subtext_id=sub,
        requested_target_coordinate=target,
        requested_charset=cset,
    )


def test_composed_file_info_coordinate_is_accepted() -> None:
    page = _parse(SAMARITAN.read_bytes(), "56000", "112", "56000112010", "R")

    assert page.status is KwicFullContextStatus.FOUND
    assert [line.coordinate for line in page.lines] == ["56000112010", "56000112020"]


def test_composed_coordinate_on_a_hebrew_script_page_is_accepted() -> None:
    page = _parse(EZRA.read_bytes(), "31000", "4", "31000414", "H")

    assert page.status is KwicFullContextStatus.FOUND
    assert "31000414" in [line.coordinate for line in page.lines]


def test_bare_file_info_coordinate_is_still_accepted() -> None:
    # CAL still renders the bare file id on some current subdivided pages (BT Shabbat
    # 71002/01051 on 2026-09-29, which needs #203 to parse). This 2026-09-24 Syriac fixture
    # shows the same bare form.
    page = _parse(ROMLAW.read_bytes(), "60301", "53", "603015323", "U")

    assert page.status is KwicFullContextStatus.FOUND


def test_composed_coordinate_without_a_submitted_sub_fails_closed() -> None:
    body = SAMARITAN.read_bytes()

    with pytest.raises(ConcordanceParseError):
        _parse(body, "56000", None, "56000112010", "R")


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (b'coord=56000112"', b'coord=56000113"'),  # another subtext
        (b'coord=56000112"', b'coord=56001112"'),  # another file
        (b'coord=56000112"', b'coord=5600011"'),  # a prefix of the sub
        (b">56000: SamTgJ", b">56001: SamTgJ"),  # a label naming another file
        (b">56000: SamTgJ", b">56000112: SamTgJ"),  # a label naming the coordinate
    ],
)
def test_file_identity_naming_anything_else_fails_closed(old: bytes, new: bytes) -> None:
    body = SAMARITAN.read_bytes()
    assert old in body

    with pytest.raises(ConcordanceParseError):
        _parse(body.replace(old, new), "56000", "112", "56000112010", "R")


def test_repeated_file_information_links_fail_closed() -> None:
    body = SAMARITAN.read_bytes()
    link = b'<a href="/get_file_info.php?coord=56000" target="info">56000: SamTgJ</a>'
    body = body.replace(b"</center>", link + b"</center>", 1)

    with pytest.raises(ConcordanceParseError):
        _parse(body, "56000", "112", "56000112010", "R")


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (b'coord=56000112"', b'coord=56000113"'),  # CAL echoes the (wrong) submitted sub
        (b'coord=56000112"', b'coord=56000"'),  # the bare form
    ],
)
def test_target_row_must_belong_to_the_submitted_subtext(old: bytes, new: bytes) -> None:
    body = SAMARITAN.read_bytes().replace(old, new)

    with pytest.raises(ConcordanceParseError, match="subtext"):
        _parse(body, "56000", "113", "56000112010", "R")


def test_suffix_bearing_composed_coordinate_is_checked_by_membership() -> None:
    # CPA subtexts carry a letter suffix (R-039). The composed coordinate is accepted by
    # exact membership, not rejected as a non-decimal file id.
    body = SAMARITAN.read_bytes().replace(b'coord=56000112"', b'coord=56000112a"')

    with pytest.raises(ConcordanceParseError) as caught:
        _parse(body, "56000", "112a", "56000112010", "R")
    assert "file_id" not in str(caught.value)
