"""Issue #175: lexicon browse cross-references are typed ordered rows."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LexiconParseError
from cal_mcp.lexicon_browse import LexiconBrowseService, parse_lexicon_browse_page
from cal_mcp.normalization import InputRepresentation

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "browse_crossrefs_structural.html"
URL = "https://cal.huc.edu/browseSKEYheaders.php?first3=%22%24l%22"


def _response(body: str | None = None) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=URL,
        body=(FIXTURE.read_text(encoding="utf-8") if body is None else body).encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 3, tzinfo=UTC),
    )


def _rows(page: object) -> tuple[Any, ...]:
    rows = getattr(page, "rows", None)
    assert isinstance(rows, tuple), "public browse page must expose ordered typed rows"
    return rows


def _entries(page: object) -> tuple[Any, ...]:
    entries = getattr(page, "entries", None)
    assert isinstance(entries, tuple)
    return entries


def _kind(row: object) -> str:
    kind = getattr(row, "kind", None)
    if hasattr(kind, "value"):
        kind = kind.value
    assert isinstance(kind, str)
    return kind


def test_mixed_browse_rows_preserve_order_and_keep_redirects_out_of_entries() -> None:
    page = parse_lexicon_browse_page(_response())

    rows = _rows(page)
    assert [_kind(row) for row in rows] == [
        "entry",
        "cross_reference",
        "cross_reference",
        "entry",
    ]

    first = getattr(rows[0], "lemma", None)
    assert first is not None
    assert first.lemma_key == "$l N"
    assert first.headwords == ("[šl]",)
    assert first.pronunciation == "šal"
    assert first.gloss == "synthetic ordinary gloss"
    assert first.aliases == ()

    redirect = rows[1]
    assert getattr(redirect, "source_text", None) == "šlhˀw"
    assert getattr(redirect, "target_lemma_key", None) == "$l)hw N"
    assert getattr(redirect, "target_label", None) == "šlˀhw, šlˀhwtˀ n.f."

    outside_prefix = rows[2]
    assert getattr(outside_prefix, "source_text", None) == "by dny"
    assert getattr(outside_prefix, "target_lemma_key", None) == "dn#2 N"
    assert getattr(outside_prefix, "target_label", None) == "dn n.m."

    later_entry = getattr(rows[3], "lemma", None)
    assert later_entry is not None
    assert later_entry.lemma_key == "$l)hw N"
    assert later_entry.gloss == "synthetic target-entry gloss"
    assert later_entry.aliases == ()

    assert [entry.lemma_key for entry in _entries(page)] == ["$l N", "$l)hw N"]
    assert all(not entry.aliases for entry in _entries(page))


def test_redirect_target_can_later_appear_as_a_distinct_ordinary_entry() -> None:
    rows = _rows(parse_lexicon_browse_page(_response()))

    assert _kind(rows[1]) == "cross_reference"
    assert getattr(rows[1], "target_lemma_key", None) == "$l)hw N"
    assert _kind(rows[3]) == "entry"
    assert getattr(getattr(rows[3], "lemma", None), "lemma_key", None) == "$l)hw N"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('<span class="uni">šlhˀw</span> → <a ', '→ <a '),
        (
            '<span class="uni">šlhˀw</span> → <a ',
            '<span class="uni">šlhˀw</span> → → <a ',
        ),
        (
            (
                '<span class="uni">šlhˀw</span> → '
                '<a href="oneentry.php?lemma=%24l%29hw+N&amp;cits=all">'
                '<span class="lem">šlˀhw, šlˀhwtˀ</span> <pos>n.f.</pos></a>'
            ),
            '<span class="uni">šlhˀw</span> → <span>missing target</span>',
        ),
        (
            'href="oneentry.php?lemma=%24l%29hw+N&amp;cits=all"',
            'href="oneentry.php?cits=all"',
        ),
        (
            (
                '<span class="lem">šlˀhw, šlˀhwtˀ</span> <pos>n.f.</pos></a>'
            ),
            (
                '<span class="lem">šlˀhw, šlˀhwtˀ</span> <pos>n.f.</pos></a>'
                ' <a href="oneentry.php?lemma=br+N&amp;cits=all">br n.m.</a>'
            ),
        ),
        (
            '<span class="lem">šlˀhw, šlˀhwtˀ</span> <pos>n.f.</pos></a>',
            '<span class="lem">šlˀhw, šlˀhwtˀ</span> <pos>n.f.</pos></a> TRAILING',
        ),
    ],
    ids=[
        "empty-source",
        "multiple-arrows",
        "missing-target",
        "missing-target-key",
        "multiple-targets",
        "trailing-text",
    ],
)
def test_malformed_cross_reference_shapes_fail_closed(old: str, new: str) -> None:
    body = FIXTURE.read_text(encoding="utf-8")
    assert old in body

    with pytest.raises(LexiconParseError):
        parse_lexicon_browse_page(_response(body.replace(old, new, 1)))


class CrossRefTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        assert request == CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("first3", '"$l"'),),
        )
        return _response()


@pytest.mark.anyio
async def test_public_browse_result_serializes_authoritative_mixed_rows() -> None:
    transport = CrossRefTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconBrowseService(client).browse(
            "$l",
            representation=InputRepresentation.CAL_CODE,
        )
    finally:
        await client.aclose()

    payload = result.to_dict()
    rows = payload.get("rows")
    assert isinstance(rows, list)
    assert [row["kind"] for row in rows] == [
        "entry",
        "cross_reference",
        "cross_reference",
        "entry",
    ]
    assert rows[0]["lemma"]["lemma_key"] == "$l N"
    assert rows[1] == {
        "kind": "cross_reference",
        "source_text": "šlhˀw",
        "target_lemma_key": "$l)hw N",
        "target_label": "šlˀhw, šlˀhwtˀ n.f.",
    }
    assert rows[2]["target_lemma_key"] == "dn#2 N"
    assert rows[3]["lemma"]["lemma_key"] == "$l)hw N"

    entries = payload["entries"]
    assert isinstance(entries, list)
    assert [entry["lemma_key"] for entry in entries] == ["$l N", "$l)hw N"]
    assert all(entry["aliases"] == [] for entry in entries)
    assert len(transport.requests) == 1
