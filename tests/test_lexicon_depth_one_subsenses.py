from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import LexiconParseError, _subsense_path, parse_lexicon_entry

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def test_depth_one_subsense_siblings_are_placeable() -> None:
    assert _subsense_path(None, 1) == (1,)
    assert _subsense_path((1,), 2) == (2,)
    assert _subsense_path((2,), 3) == (3,)
    assert _subsense_path((3,), 4) == (4,)


def test_existing_deeper_sibling_and_child_behavior_is_preserved() -> None:
    assert _subsense_path((2, 1), 2) == (2, 2)
    assert _subsense_path((1, 1), 2) == (1, 2)
    assert _subsense_path((2,), 1) == (2, 1)


def test_unplaceable_or_nonpositive_subsense_numbers_still_raise() -> None:
    with pytest.raises(LexiconParseError):
        _subsense_path((1,), 4)
    with pytest.raises(LexiconParseError):
        _subsense_path((1,), 0)
    with pytest.raises(LexiconParseError):
        _subsense_path((1,), -1)


def test_full_entry_can_begin_with_four_depth_one_subsenses() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/oneentry.php?lemma=%29lh+N",
        body=(FIXTURES / "entry_alh_depth1_subsenses.html").read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )

    entry = parse_lexicon_entry(response, lemma_key=")lh N")

    assert entry.lemma.headwords == (")lh",)
    assert entry.lemma.part_of_speech == "N"
    assert entry.lemma.gloss == "god"
    assert [sense.label_path for sense in entry.senses] == [(1,), (2,), (3,), (4,)]
    assert [sense.definition for sense in entry.senses] == [
        "God, deity",
        "a god or divine being",
        "divine title usage",
        "other attested usage",
    ]
