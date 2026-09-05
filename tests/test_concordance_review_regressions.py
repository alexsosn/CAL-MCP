from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    KwicScopeKind,
    parse_kwic_result,
    parse_text_concordance_page,
)


def _response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )


def test_text_concordance_rejects_foreign_origin_kwic_link() -> None:
    href = "https://other.example/showKWIC.php?lemma=mlk+N&amp;charset=S&amp;texts=13250"
    response = _response(
        f"""<html><body>
<div>Frequencies of lemmas in text 13250</div>
<table><tr>
<td>1:</td>
<td><a href="{href}">mlk N</a></td>
<td>: king</td>
</tr></table>
</body></html>""",
        "https://cal.huc.edu/newconcord.php?text=13250&cset=S",
    )

    with pytest.raises(ConcordanceParseError):
        parse_text_concordance_page(
            response,
            requested_text_id="13250",
            requested_charset="S",
        )


def test_kwic_rejects_foreign_origin_full_context_link() -> None:
    href = (
        "https://other.example/get_a_kwicchapter.php?"
        "file=13250&amp;sub=&amp;cset=R&amp;target=1325003"
    )
    response = _response(
        f"""<html><body>
<div>Looking for mlk N in dialect 13250</div>
<div>13250:</div>
<table><tr>
<td>left context</td>
<td><a href="{href}">1325003</a></td>
<td>right context</td>
</tr></table>
<div>total examples: 1</div>
</body></html>""",
        "https://cal.huc.edu/showdialectKWIC.php",
    )

    with pytest.raises(ConcordanceParseError):
        parse_kwic_result(
            response,
            lemma_key="mlk N",
            scope_kind=KwicScopeKind.TEXTS,
            scope_ids=("13250",),
        )


def test_text_concordance_rejects_malformed_returned_lemma_key() -> None:
    response = _response(
        """<html><body>
<div>Frequencies of lemmas in text 13250</div>
<table><tr>
<td>1:</td>
<td><a href="/showKWIC.php?lemma=mlk+%21&amp;charset=S&amp;texts=13250">mlk !</a></td>
<td>: malformed</td>
</tr></table>
</body></html>""",
        "https://cal.huc.edu/newconcord.php?text=13250&cset=S",
    )

    with pytest.raises(ConcordanceParseError):
        parse_text_concordance_page(
            response,
            requested_text_id="13250",
            requested_charset="S",
        )
