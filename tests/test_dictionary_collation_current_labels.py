"""Issue #174: current (2026-09-25) dictionary-collation result headings.

See docs/research/issue-174-dictionary-labels.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.dictionary_collation import (
    DictionaryCollationParseError,
    DictionaryCollationResult,
    DictionaryCollationService,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
DJBA = FIXTURES / "dictionary_collation_djba_100_current.html"
SCHULTHESS = FIXTURES / "dictionary_collation_schulthess_100_current.html"


def _relabel(label: str) -> bytes:
    """The DJBA page with CAL's <title> and heading both naming ``label``."""
    body = DJBA.read_text(encoding="utf-8")
    old = "Dictionary of Jewish Babylonian Aramaic"
    for suffix in ("</title>", "</i>"):
        assert old + suffix in body
        body = body.replace(old + suffix, label + suffix, 1)
    return body.encode()


async def _collate(source: str, body: bytes) -> DictionaryCollationResult:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config, request
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/searchdicts.php",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        return await DictionaryCollationService(client).collate(source, "100")
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_djba_current_heading_label_is_accepted_and_returned() -> None:
    result = await _collate("djba", DJBA.read_bytes())

    assert result.source_label == "Dictionary of Jewish Babylonian Aramaic"
    assert [(entry.display_lemma, entry.gloss) for entry in result.entries] == [
        (")zyt) N", "a type of fever"),
        (")zl V", "to go"),
    ]


@pytest.mark.anyio
async def test_schulthess_current_heading_label_is_accepted_and_returned() -> None:
    result = await _collate("schulthess", SCHULTHESS.read_bytes())

    assert result.source_label == "Schulthess"
    assert len(result.entries) == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("source", "heading"),
    [
        ("djpa", "Dictionary of Jewish Palestinian Aramaic"),
        ("levy_targumim", "Levy Chaldäisches Wörterbuch"),
    ],
)
async def test_other_shortened_heading_labels_are_accepted(source: str, heading: str) -> None:
    result = await _collate(source, _relabel(heading))
    assert result.source_label == heading


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("source", "heading"),
    [
        # Another dictionary's current heading.
        ("djba", "Dictionary of Jewish Palestinian Aramaic"),
        # A near miss of an accepted label.
        ("schulthess", "Schulthess Lexicon"),
        # The full form label of a different source.
        ("djba", "A Dictionary of Christian Palestinian Aramaic"),
    ],
)
async def test_heading_naming_another_dictionary_fails_closed(source: str, heading: str) -> None:
    with pytest.raises(DictionaryCollationParseError, match="does not match the submitted source"):
        await _collate(source, _relabel(heading))


@pytest.mark.anyio
async def test_full_form_label_is_still_accepted() -> None:
    # The earlier heading used the form label; it stays valid.
    result = await _collate("djba", _relabel("A Dictionary of Jewish Babylonian Aramaic"))
    assert result.source_label == "A Dictionary of Jewish Babylonian Aramaic"
