"""Issue #255: CAL's current Peshitta Matthew concordance links the key ``prC PN``."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import ConcordanceService, parse_text_concordance_page
from cal_mcp.errors import CalInputError

FIXTURE = (
    Path(__file__).parent / "fixtures" / "cal" / "text_concordance_62040_capital_c_current.html"
)
SOURCE_URL = "https://cal.huc.edu/newconcord.php?text=62040&cset=S"


def _parse(body: bytes):
    return parse_text_concordance_page(
        CalResponse(
            status_code=200,
            url=SOURCE_URL,
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        ),
        requested_text_id="62040",
        requested_charset="S",
    )


def test_observed_capital_c_key_is_kept_verbatim_in_cal_order() -> None:
    page = _parse(FIXTURE.read_bytes())

    assert [(item.frequency, item.lemma_key, item.label, item.gloss) for item in page.lemmas] == [
        (1, "pr(#3 V", "prˁ vb.", "to put forth leaves or fruit"),
        (2, "prC PN", "prC PN", "proper noun"),
        (6, "prcwp N", "prṣwp, prṣwpˀ n.m.", "face; individual"),
    ]
    assert page.lemmas[1].kwic_url == (
        "https://cal.huc.edu/showKWIC.php?lemma=prC+PN&charset=S&texts=62040"
    )


class _NoRequestClient:
    async def fetch(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("no CAL request expected")


@pytest.mark.anyio
async def test_capital_c_key_is_rejected_as_kwic_input_like_other_capitals() -> None:
    with pytest.raises(CalInputError, match="kwic_url of the cal_text_concordance row"):
        await ConcordanceService(_NoRequestClient()).kwic_texts(  # type: ignore[arg-type]
            "prC PN", ["62040"]
        )
