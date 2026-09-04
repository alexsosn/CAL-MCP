from __future__ import annotations

from datetime import UTC, datetime

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import parse_lexicon_entry


def test_capitalized_definition_is_not_guessed_to_be_a_dialect_label() -> None:
    entry = parse_lexicon_entry(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/cal_entry_web.php?lemma=test+N",
            body=(
                b"<html><body><header>test n.m. thing</header>"
                b"<div>1</div><div>Creation</div><div>Syr</div>"
                b"</body></html>"
            ),
            content_type="text/html",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        ),
        lemma_key="test N",
    )

    assert entry.senses[0].definition == "Creation"
    assert entry.senses[0].dialects == ("Syr",)
