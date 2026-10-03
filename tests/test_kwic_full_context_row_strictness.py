"""Issue #208: full-context text rows enforce the text-page fail-closed boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import ConcordanceParseError, parse_kwic_full_context_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
BT = FIXTURES / "kwic_full_context_bt_71002_01051_current.html"
SAMARITAN = FIXTURES / "kwic_full_context_samaritan_56000_112_current.html"


def _parse_bt(body: bytes) -> None:
    parse_kwic_full_context_page(
        CalResponse(
            status_code=200,
            url=(
                "https://cal.huc.edu/get_a_kwicchapter.php?"
                "file=71002&sub=01051&cset=H&target=7100201051217"
            ),
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        ),
        requested_file_id="71002",
        requested_subtext_id="01051",
        requested_target_coordinate="7100201051217",
        requested_charset="H",
    )


def _parse_samaritan(body: bytes):
    return parse_kwic_full_context_page(
        CalResponse(
            status_code=200,
            url=(
                "https://cal.huc.edu/get_a_kwicchapter.php?"
                "file=56000&sub=112&cset=R&target=56000112010"
            ),
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        ),
        requested_file_id="56000",
        requested_subtext_id="112",
        requested_target_coordinate="56000112010",
        requested_charset="R",
    )


def test_loose_text_between_full_context_tokens_fails_closed() -> None:
    body = BT.read_bytes()
    old = (
        b'word=0" target="info">\xd7\x94\xd7\x90\xd7\x99</a> '
        b'<a href="bablex.php?coord=7100201050244&word=1"'
    )
    new = old.replace(b"</a> ", b"</a> LOOSE ", 1)
    assert old in body

    with pytest.raises(ConcordanceParseError, match="loose|text"):
        _parse_bt(body.replace(old, new, 1))



def test_raw_leading_angle_bracket_in_full_context_token_is_preserved() -> None:
    body = SAMARITAN.read_bytes()
    old = b">yhwh</a>"
    new = b"><w)th</a>"
    assert old in body

    page = _parse_samaritan(body.replace(old, new, 1))

    token_texts = [token.text for line in page.lines for token in line.tokens]
    assert "<w)th" in token_texts
    assert any("<w)th" in line.text for line in page.lines)


def test_unknown_element_inside_full_context_token_fails_closed() -> None:
    body = SAMARITAN.read_bytes()
    old = b">yhwh</a>"
    new = b">yh<wmr>wh</a>"
    assert old in body

    with pytest.raises(ConcordanceParseError, match="element|tag|row"):
        _parse_samaritan(body.replace(old, new, 1))


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            b'href="bablex.php?coord=7100201051217&word=1"',
            b'href="/evil/bablex.php?coord=7100201051217&word=1"',
        ),
        (
            b'href="bablex.php?coord=7100201051217&word=1"',
            b'href="bablex.php?coord=7100201051217&word=1#unexpected"',
        ),
    ],
)
def test_bablex_full_context_link_path_and_fragment_are_exact(old: bytes, new: bytes) -> None:
    body = BT.read_bytes()
    assert old in body

    with pytest.raises(ConcordanceParseError, match="path|fragment|link"):
        _parse_bt(body.replace(old, new, 1))


def test_getlex_full_context_link_requires_cal_root_path() -> None:
    body = SAMARITAN.read_bytes()
    old = b'href="getlex.php?coord=56000112010&word=1&hasvariant=0"'
    new = b'href="/evil/getlex.php?coord=56000112010&word=1&hasvariant=0"'
    assert old in body

    with pytest.raises(ConcordanceParseError, match="path|link"):
        _parse_samaritan(body.replace(old, new, 1))


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            b'href="comment.php?coord=56000112010"',
            b'href="/evil/comment.php?coord=56000112010"',
        ),
        (
            b'href="comment.php?coord=56000112010"',
            b'href="comment.php?coord=56000112010#unexpected"',
        ),
    ],
)
def test_full_context_comment_link_path_and_fragment_are_exact(old: bytes, new: bytes) -> None:
    body = SAMARITAN.read_bytes()
    assert old in body

    with pytest.raises(ConcordanceParseError, match="path|fragment|link"):
        _parse_samaritan(body.replace(old, new, 1))
