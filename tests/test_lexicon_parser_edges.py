from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import parse_lexicon_entry

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


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


def test_repeated_parenthetical_labels_preserve_deep_sense_hierarchy() -> None:
    entry = parse_lexicon_entry(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
            body=(FIXTURES / "entry_br_nested.html").read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        ),
        lemma_key="br N",
    )

    assert [(sense.label_path, sense.definition) for sense in entry.senses] == [
        ((1,), "son, child"),
        ((2,), "member of the same cohort"),
        ((2, 1), "metaph."),
        ((2, 1, 1), "disciple"),
        ((2, 1, 1, 1), "in construct w. PN of a famous person"),
        ((2, 1, 1, 2), "product"),
    ]


def test_multiple_linked_citations_on_one_line_keep_separate_text() -> None:
    entry = parse_lexicon_entry(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
            body=(FIXTURES / "entry_br_nested.html").read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        ),
        lemma_key="br N",
    )

    citations = entry.senses[0].citations
    assert [(item.reference, item.text) for item in citations] == [
        ("TAD B3.8 R.28", "וה[ן] ימות"),
        ("BT Git 48a(50)", "חד בר חד"),
    ]
