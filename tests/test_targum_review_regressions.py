from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.targum import (
    TargumParallelStatus,
    TargumParseError,
    parse_hebrew_lemma_options_page,
    parse_targum_concordance_page,
    parse_targum_parallel_page,
)


def _response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )


def test_parallel_ignores_coordinate_error_text_inside_non_rendered_style() -> None:
    page = parse_targum_parallel_page(
        _response(
            """
            <html><head><style>.notice::after { content: "error in coordinate"; }</style></head>
            <body>
              <h1>MT and targums for Gen 1:1</h1>
              <div class="targum-block"><span class="heb">בְּרֵאשִׁית</span></div>
              <div class="targum-block">Onqelos:<span class="heb">בֲקַדמִין</span></div>
            </body></html>
            """,
            "https://cal.huc.edu/showtargum.php",
        ),
        book="Gen",
        chapter=1,
        verse=1,
    )

    assert page.status is TargumParallelStatus.FOUND
    assert page.mt_text == "בְּרֵאשִׁית"
    assert [reading.label for reading in page.readings] == ["Onqelos:"]


def test_concordance_requires_rendered_total_not_css_counterfeit() -> None:
    response = _response(
        """
        <html><head><style>/* total examples: 3 */</style></head><body>
          <h1>CAL: Targum KWIC counts for klb N</h1>
          <table>
            <tr><th>Targum</th><th>Occurrences</th></tr>
            <tr><th>Torah</th></tr>
            <tr>
              <td>
                <a href="/show1dialectKWIC.php?lemma=klb&amp;pos=N&amp;texts=51001&amp;charset=H">
                  Onqelos
                </a>
              </td>
              <td>3</td>
            </tr>
          </table>
        </body></html>
        """,
        "https://cal.huc.edu/showtargumKWIC.php",
    )

    with pytest.raises(TargumParseError, match="count/total semantics"):
        parse_targum_concordance_page(response, lemma_key="klb N")


def test_hebrew_chooser_requires_rendered_marker_not_css_counterfeit() -> None:
    response = _response(
        """
        <html><head><style>/* CAL: MT lemma chooser */</style></head><body>
          <form method="post" action="/getOmtlemma.php">
            <label><input type="radio" name="R1" value="1751">מַעֲקֶה n</label>
          </form>
        </body></html>
        """,
        "https://cal.huc.edu/Omtlemmas/memMTlemma.html",
    )

    with pytest.raises(TargumParseError, match="semantic page marker"):
        parse_hebrew_lemma_options_page(response, targum="onqelos")


def test_parallel_rejects_unclosed_ignored_content_subtree() -> None:
    response = _response(
        """
        <html><body>
          <h1>MT and targums for Gen 1:1</h1>
          <div class="targum-block"><span class="heb">בְּרֵאשִׁית</span></div>
          <div class="targum-block">Onqelos:<span class="heb">בֲקַדמִין</span></div>
          <style>.unfinished { content: "ignored";
        """,
        "https://cal.huc.edu/showtargum.php",
    )

    with pytest.raises(TargumParseError, match="ignored content subtree"):
        parse_targum_parallel_page(response, book="Gen", chapter=1, verse=1)


def test_concordance_rejects_unclosed_ignored_content_subtree() -> None:
    response = _response(
        """
        <html><body>
          <h1>CAL: Targum KWIC counts for zzzzzz N</h1>
          <table>
            <tr><th>Targum</th><th>Occurrences</th></tr>
            <tr><th>Torah</th></tr>
            <tr>
              <td>
                <a
                  href="/show1dialectKWIC.php?lemma=zzzzzz&amp;pos=N&amp;texts=51001&amp;charset=H"
                >
                  Onqelos
                </a>
              </td>
              <td>0</td>
            </tr>
          </table>
          <p>total examples: 0</p>
          <script>const unfinished = true;
        """,
        "https://cal.huc.edu/showtargumKWIC.php",
    )

    with pytest.raises(TargumParseError, match="ignored content subtree"):
        parse_targum_concordance_page(response, lemma_key="zzzzzz N")


def test_hebrew_chooser_rejects_unclosed_ignored_content_subtree() -> None:
    response = _response(
        """
        <html><body>
          <h1>CAL: MT lemma chooser</h1>
          <form method="post" action="/getOmtlemma.php">
            <label><input type="radio" name="R1" value="1751">מַעֲקֶה n</label>
          </form>
          <style>.unfinished { display: none;
        """,
        "https://cal.huc.edu/Omtlemmas/memMTlemma.html",
    )

    with pytest.raises(TargumParseError, match="ignored content subtree"):
        parse_hebrew_lemma_options_page(response, targum="onqelos")
