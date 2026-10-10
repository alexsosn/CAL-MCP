"""Issue #284: a ": " inside a parenthesized text-search label is part of the label."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.texts import parse_text_search_page

FIXTURE = (
    Path(__file__).parent / "fixtures" / "cal" / "text_search_john_parenthesized_label_current.html"
)


def _parse(body: str):
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/newsearchtxts.php",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
    )
    return parse_text_search_page(response, submitted_query="John")


def test_parenthesized_separator_stays_in_the_label() -> None:
    page = _parse(FIXTURE.read_text(encoding="utf-8"))

    assert [(match.file_id, match.label, match.description) for match in page.matches] == [
        (
            "64550",
            "JElet (Jacob of Edessa: Letter to John the Stylite of Litarab)",
            "Text as per Karl-Erik Rignell,",
        )
    ]


@pytest.mark.parametrize(
    ("old", "new", "label", "description"),
    [
        # Parentheses that never close: no trustworthy depth, so keep the first ": " split.
        (
            "Litarab): Text",
            "Litarab: Text",
            "JElet (Jacob of Edessa",
            "Letter to John the Stylite of Litarab: Text as per Karl-Erik Rignell,",
        ),
        # A stray closing parenthesis first: likewise the first ": " split.
        (
            "JElet (Jacob",
            "JElet) (Jacob",
            "JElet) (Jacob of Edessa",
            "Letter to John the Stylite of Litarab): Text as per Karl-Erik Rignell,",
        ),
        # ")" before "(" balances in count but not in order: still the first ": " split.
        (
            "JElet (Jacob of Edessa: Letter to John the Stylite of Litarab): Text",
            "JElet) Jacob of Edessa: Letter to John (the Stylite of Litarab: Text",
            "JElet) Jacob of Edessa",
            "Letter to John (the Stylite of Litarab: Text as per Karl-Erik Rignell,",
        ),
        # A separator after a balanced group is the separator.
        (
            ": Letter to John the Stylite of Litarab)",
            ")",
            "JElet (Jacob of Edessa)",
            "Text as per Karl-Erik Rignell,",
        ),
        # Balanced group with only a bare colon inside: no description beyond the real one.
        (
            "Edessa: Letter",
            "Edessa:Letter",
            "JElet (Jacob of Edessa:Letter to John the Stylite of Litarab)",
            "Text as per Karl-Erik Rignell,",
        ),
    ],
)
def test_separator_edge_cases(old: str, new: str, label: str, description: str) -> None:
    body = FIXTURE.read_text(encoding="utf-8")
    assert old in body

    page = _parse(body.replace(old, new))

    assert [(match.label, match.description) for match in page.matches] == [(label, description)]
