from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.targum import (
    TargumParseError,
    parse_targum_concordance_page,
    parse_targum_reflex_page,
)


def _response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
    )


def _concordance_response(href: str) -> CalResponse:
    return _response(
        f"""
        <html><body>
          <h1>CAL: Targum KWIC counts for klb N</h1>
          <table>
            <tr><th>Targum</th><th>Occurrences</th></tr>
            <tr><td><a href="{href}">Onqelos</a></td><td>1</td></tr>
          </table>
          <p>total examples: 1</p>
        </body></html>
        """,
        "https://cal.huc.edu/showtargumKWIC.php",
    )


def _reflex_response(href: str) -> CalResponse:
    return _response(
        f"""
        <html><body>
          <h1>Onkelos correspondences to מַעֲקֶה</h1>
          <table>
            <tr><th>CAL lemma</th><th>frequency</th></tr>
            <tr><td><a href="{href}">תיק #2 N</a></td><td>2</td></tr>
          </table>
        </body></html>
        """,
        "https://cal.huc.edu/getOmtlemma.php",
    )


@pytest.mark.parametrize(
    "href",
    [
        "/show1dialectKWIC.php?lemma=klb&amp;pos=N&amp;texts=51001&amp;charset=H&amp;junk=x",
        "/show1dialectKWIC.php?lemma=klb&amp;pos=N&amp;texts=51001",
        "/show1dialectKWIC.php?lemma=klb&amp;pos=N&amp;texts=51001&amp;charset=R",
        "/show1dialectKWIC.php?lemma=klb&amp;pos=N&amp;texts=51001+oops&amp;charset=H",
        "/show1dialectKWIC.php?lemma=klb&amp;pos=N&amp;texts=51001+51001&amp;charset=H",
        "/show1dialectKWIC.php?lemma=klb&amp;pos=N&amp;texts=51001%C2%A051002&amp;charset=H",
        "/show1dialectKWIC.php?lemma=klb&amp;pos=N&amp;texts=51001&amp;charset=H#fragment",
    ],
)
def test_concordance_rejects_malformed_example_selectors(href: str) -> None:
    with pytest.raises(TargumParseError):
        parse_targum_concordance_page(_concordance_response(href), lemma_key="klb N")


@pytest.mark.parametrize(
    "href",
    [
        "/getOMT.php?MT=1751&amp;cal=tyq%232+N&amp;junk=x",
        "/getOMT.php?MT=1751&amp;cal=tyq%232+N#fragment",
        "/getOMT.php?MT=1751&amp;cal=bad",
    ],
)
def test_reflex_rejects_malformed_example_selectors(href: str) -> None:
    with pytest.raises(TargumParseError):
        parse_targum_reflex_page(
            _reflex_response(href),
            targum="onqelos",
            mt_lemma_id="1751",
        )
