"""Issue #222: current CAL lemma POS can carry one trailing uncertainty marker."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import (
    _parse_lemma_header,
    parse_browse_page,
    parse_lexicon_entry,
)


def _response(body: str, *, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 3, tzinfo=UTC),
    )


def test_uncertain_pos_header_preserves_terminal_marker() -> None:
    lemma = _parse_lemma_header(
        "šlh n.f.? watering(?)",
        lemma_key="$lh N",
        require_gloss=True,
    )

    assert lemma is not None
    assert lemma.lemma_key == "$lh N"
    assert lemma.headwords == ("šlh",)
    assert lemma.part_of_speech == "n.f.?"
    assert lemma.gloss == "watering(?)"


@pytest.mark.parametrize(
    "pos",
    [
        "n.?f.",
        "n.f.??",
        "?n.f.",
        "n.f.!",
    ],
)
def test_uncertain_pos_does_not_widen_other_punctuation(pos: str) -> None:
    assert (
        _parse_lemma_header(
            f"šlh {pos} watering",
            lemma_key="$lh N",
            require_gloss=True,
        )
        is None
    )


def test_browse_page_accepts_current_uncertain_pos_header() -> None:
    page = parse_browse_page(
        _response(
            """
            <html><body>
              <div>
                <a href="oneentry.php?lemma=%24lh+N&amp;cits=all">
                  <span class="lem">šlh</span> <pos>n.f.?</pos>
                </a>
              </div>
              <div><span class="gloss">watering(?)</span></div>
            </body></html>
            """,
            url="https://cal.huc.edu/browseSKEYheaders.php?first3=%22%24l%22",
        )
    )

    assert len(page.entries) == 1
    lemma = page.entries[0]
    assert lemma.lemma_key == "$lh N"
    assert lemma.headwords == ("šlh",)
    assert lemma.part_of_speech == "n.f.?"
    assert lemma.gloss == "watering(?)"


def test_exact_entry_prefers_real_uncertain_header_over_later_period_prose() -> None:
    entry = parse_lexicon_entry(
        _response(
            """
            <html><body>
              <div class="summary-card">
                <div class="lemma-header">
                  <span class="lemma-headword">šlh</span>
                  <span class="lemma-pos">n.f.?</span>
                  <span class="lemma-gloss">watering(?)</span>
                </div>
              </div>
              <div>1</div>
              <div>watering</div>
              <div>Common Aramaic</div>
              <div>✎Notes &amp; Bibliography▶</div>
              <p>See source 17 for other suggestions. Compare synthetic parallel.</p>
              <p>Page refs. in other dictionaries: SOURCE: 1136</p>
              <div>📖 Full Bibliography</div>
            </body></html>
            """,
            url="https://cal.huc.edu/oneentry.php?lemma=%24lh+N&cits=all",
        ),
        lemma_key="$lh N",
    )

    assert entry.lemma.lemma_key == "$lh N"
    assert entry.lemma.headwords == ("šlh",)
    assert entry.lemma.part_of_speech == "n.f.?"
    assert entry.lemma.gloss == "watering(?)"
    assert entry.lemma.headwords != ("See source 17 for other",)
    assert entry.lemma.part_of_speech != "suggestions."
    assert [sense.label_path for sense in entry.senses] == [(1,)]
    assert entry.senses[0].definition == "watering"
