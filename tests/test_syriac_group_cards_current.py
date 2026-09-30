"""Issue #172: Syriac group pages in CAL's current card layout.

See docs/research/issue-172-syriac-group-cards.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.syriac import (
    SyriacParseError,
    SyriacProvenance,
    SyriacTextGroupResult,
    SyriacTextNavigationKind,
    parse_syriac_text_group_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _body(group: str) -> bytes:
    return (FIXTURES / f"syriac_group_{group}_cards_current.html").read_bytes()


def _parse(body: bytes, group: str):
    return parse_syriac_text_group_page(
        CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/showsubtexts.php?keyword={group}",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 30, tzinfo=UTC),
        ),
        group_id=group,
    )


def test_ephpar_group_children_are_subtexts_of_one_file() -> None:
    items = _parse(_body("60420"), "60420")

    assert [(item.upstream_id, item.subtext_id, item.label) for item in items] == [
        ("60420", "01", "hymn 1"),
        ("60420", "02", "hymn 2"),
        ("60420", "03", "hymn 3"),
    ]
    assert all(item.navigation_kind is SyriacTextNavigationKind.TEXT for item in items)
    assert items[0].navigation_url == (
        "https://cal.huc.edu/get_a_chapter.php?file=60420&sub=01&cset=S"
    )
    assert items[0].info_url is not None
    assert "coord=60420" in items[0].info_url


def test_inscription_group_cards_carry_file_plus_sub_info_links() -> None:
    items = _parse(_body("61000"), "61000")

    assert [(item.upstream_id, item.subtext_id, item.label) for item in items] == [
        ("61000", "001", "Drijvers.1=OS.As55= Birecik"),
        ("61000", "002", "Drijvers.2=OS.Bs2"),
        ("61000", "003", "Drijvers.3=OS.As45"),
    ]
    assert items[1].info_url is not None
    assert "coord=61000002" in items[1].info_url


def test_subtext_id_is_serialized() -> None:
    items = _parse(_body("61000"), "61000")
    result = SyriacTextGroupResult(
        group_id="61000",
        items=items,
        provenance=SyriacProvenance(
            source="CAL",
            source_url="https://cal.huc.edu/showsubtexts.php?keyword=61000",
            retrieved_at=datetime(2026, 9, 30, tzinfo=UTC),
            operation="syriac_group",
        ),
    )

    serialized = result.to_dict()["items"]
    assert isinstance(serialized, list)
    assert serialized[0]["subtext_id"] == "001"


_CARD = (
    b'<a class="book-link" href="/get_a_chapter.php?file=61000&sub=002&cset=S">'
    b"Drijvers.2=OS.Bs2</a>"
)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        # an unknown link class inside a card
        (_CARD, _CARD.replace(b"book-link", b"other-link")),
        # two book links in one card
        (_CARD, _CARD + _CARD.replace(b"sub=002", b"sub=009")),
        # a card info link naming another file
        (b"coord=61000002&", b"coord=61001002&"),
        # a script toggle naming another group
        (b"subtext=61000&script=R", b"subtext=61001&script=R"),
        # the group summary's info link naming another group
        (b"coord=61000&return", b"coord=61001&return"),
        # a repeated card
        (_CARD, _CARD.replace(b"sub=002", b"sub=001")),
        # a sub that is not decimal
        (_CARD, _CARD.replace(b"sub=002", b"sub=0x2")),
    ],
)
def test_unexpected_card_structure_fails_closed(old: bytes, new: bytes) -> None:
    body = _body("61000")
    assert old in body

    with pytest.raises(SyriacParseError):
        _parse(body.replace(old, new, 1), "61000")
