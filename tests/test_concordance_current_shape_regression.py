from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import ConcordanceParseError, parse_text_concordance_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
SOURCE_URL = "https://cal.huc.edu/newconcord.php?text=13250&cset=S"


def _response(body: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=SOURCE_URL,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 6, tzinfo=UTC),
    )


def test_current_inline_text_concordance_preserves_ordered_semantics() -> None:
    response = CalResponse(
        status_code=200,
        url=SOURCE_URL,
        body=(FIXTURES / "concordance_text_13250_inline_current.html").read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 6, tzinfo=UTC),
    )

    page = parse_text_concordance_page(
        response,
        requested_text_id="13250",
        requested_charset="S",
    )

    assert [(item.frequency, item.lemma_key, item.gloss) for item in page.lemmas] == [
        (4, ")b N", "father"),
        (1, ")x)b PN", "proper noun"),
        (1, ")xzyhw PN", "proper noun"),
    ]
    assert page.lemmas[0].kwic_url == (
        "https://cal.huc.edu/showKWIC.php?lemma=%29b+N&charset=S&texts=13250"
    )


def test_current_inline_mode_rejects_frequency_row_without_kwic_link() -> None:
    body = """
    <html><body>
    <div>Frequencies of lemmas in text 13250</div>
    <span>
    4:.......<a href="/showKWIC.php?lemma=%29b+N&amp;charset=S&amp;texts=13250">)b N</a>: father<br>
    2:.......br N: son<br>
    </span>
    </body></html>
    """

    with pytest.raises(ConcordanceParseError):
        parse_text_concordance_page(
            _response(body),
            requested_text_id="13250",
            requested_charset="S",
        )


def test_current_inline_mode_rejects_kwic_row_without_frequency() -> None:
    body = """
    <html><body>
    <div>Frequencies of lemmas in text 13250</div>
    <span>
    4:.......<a href="/showKWIC.php?lemma=%29b+N&amp;charset=S&amp;texts=13250">)b N</a>: father<br>
    <a href="/showKWIC.php?lemma=br+N&amp;charset=S&amp;texts=13250">br N</a>: son<br>
    </span>
    </body></html>
    """

    with pytest.raises(ConcordanceParseError):
        parse_text_concordance_page(
            _response(body),
            requested_text_id="13250",
            requested_charset="S",
        )


def test_current_inline_mode_rejects_empty_gloss() -> None:
    body = """
    <html><body>
    <div>Frequencies of lemmas in text 13250</div>
    <span>
    4:.......<a href="/showKWIC.php?lemma=%29b+N&amp;charset=S&amp;texts=13250">)b N</a>:<br>
    </span>
    </body></html>
    """

    with pytest.raises(ConcordanceParseError):
        parse_text_concordance_page(
            _response(body),
            requested_text_id="13250",
            requested_charset="S",
        )
