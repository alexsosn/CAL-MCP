from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import parse_lexicon_entry

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def test_verb_entry_preserves_root_and_stem_specific_sense_context() -> None:
    html = (FIXTURES / "entry_abr_v.html").read_bytes()
    entry = parse_lexicon_entry(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/oneentry.php?cits=all&lemma=%29br+V",
            body=html,
            content_type="text/html",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        ),
        lemma_key=")br V",
    )

    assert entry.lemma.headwords == ("ˀbr",)
    assert entry.lemma.part_of_speech == "vb."
    assert entry.root == "br, brˀ n.m."
    assert entry.grammar == ("D Dt",)
    assert [(sense.heading, sense.definition) for sense in entry.senses] == [
        ("D paˁˁel to make a son", "to make a son"),
        ("Dt ˀeṯpaˁˁal to be made a son", "to be made a son"),
    ]
    assert entry.senses[0].dialects == ("Syr",)
    assert entry.senses[0].citations[0].reference == "Hormizd 16:5"
