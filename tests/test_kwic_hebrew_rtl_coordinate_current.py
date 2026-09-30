"""Issue #206: Hebrew-script KWIC coordinates written reversed inside <BDO dir="rtl">.

See docs/research/issue-206-bdo-reversed-coordinate.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import ConcordanceParseError, KwicPage, KwicScopeKind, parse_kwic_result

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
BT = FIXTURES / "kwic_texts_gml_71002_hebrew_current.html"
TEL_DAN = FIXTURES / "kwic_texts_mlk_13250_hebrew_current.html"


def _parse(body: bytes, lemma_key: str, text_id: str) -> KwicPage:
    return parse_kwic_result(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/showdialectKWIC.php",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 29, tzinfo=UTC),
        ),
        lemma_key=lemma_key,
        scope_kind=KwicScopeKind.TEXTS,
        scope_ids=(text_id,),
    )


def test_babylonian_talmud_hebrew_hits_keep_cal_target_coordinates() -> None:
    page = _parse(BT.read_bytes(), "gml N", "71002")

    assert page.total == 2
    assert [
        (hit.file_id, hit.subtext_id, hit.target_coordinate, hit.charset, hit.target_text)
        for hit in page.hits
    ] == [
        ("71002", "01077", "7100201077225", "H", "גמלא"),
        ("71002", "01154", "7100201154219", "H", "דגמלי;"),
    ]
    assert page.hits[0].context.startswith("הני דמיכסינן")


def test_tel_dan_hebrew_hits_parse() -> None:
    page = _parse(TEL_DAN.read_bytes(), "mlk N", "13250")

    assert page.total == 6
    assert page.hits[0].target_coordinate == "1325003"
    assert all(hit.charset == "H" for hit in page.hits)


_REVERSED = b'<span class="mono"><BDO dir="rtl">5227701020017</BDO></span></a>'


@pytest.mark.parametrize(
    "replacement",
    [
        b"5227701020017</a>",  # reversed but not inside <BDO dir="rtl">
        b'<span class="mono"><BDO dir="ltr">5227701020017</BDO></span></a>',
        b'<span class="mono"><BDO dir="rtl">5227701020071</BDO></span></a>',  # not the reverse
        b'<span class="mono"><BDO dir="rtl">5227701020017</BDO></span> x</a>',  # extra text
        b'<span class="mono"><BDO dir="rtl">7100201077225</BDO></span></a>',  # plain inside rtl
    ],
)
def test_other_link_texts_fail_closed(replacement: bytes) -> None:
    body = BT.read_bytes()
    assert _REVERSED in body

    with pytest.raises(ConcordanceParseError):
        _parse(body.replace(_REVERSED, replacement, 1), "gml N", "71002")
