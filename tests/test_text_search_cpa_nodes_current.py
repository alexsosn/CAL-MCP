"""Issue #263: CAL text search returns CPA catalogue nodes with ``cset=C`` (R-083).

Some CPA node identifiers carry one lowercase letter suffix (``5500056125a``). They are opaque
catalogue identifiers: returned whole for ``cal_text_catalogue`` and never split into a file and
subtext pair.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalInputError
from cal_mcp.texts import TextParseError, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
SEARCH = FIXTURES / "text_search_john_cpa_nodes_current.html"
NODE = FIXTURES / "text_catalogue_cpa_5500056125a_node_current.html"
CATALOGUE = "cal_text_catalogue"


def _client(url: str, body: bytes, requests: list[CalRequest]) -> CalHttpClient:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return CalResponse(
            status_code=200,
            url=url,
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        )

    return CalHttpClient(transport=transport)


async def _search(body: bytes):
    client = _client("https://cal.huc.edu/newsearchtxts.php", body, [])
    try:
        return await TextService(client).search("John")
    finally:
        await client.aclose()


async def _catalogue(category_id: str, body: bytes, requests: list[CalRequest] | None = None):
    requests = [] if requests is None else requests
    client = _client(f"https://cal.huc.edu/showsubtexts.php?subtext={category_id}", body, requests)
    try:
        return await TextService(client).catalogue(category_id=category_id)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_text_search_returns_cpa_nodes_as_whole_catalogue_identifiers() -> None:
    result = await _search(SEARCH.read_bytes())

    assert [
        (match.file_id, match.subtext_id, match.category_id, match.follow_up_tool)
        for match in result.matches
    ] == [
        (None, None, "5500056125a", CATALOGUE),
        (None, None, "55400122", CATALOGUE),
        (None, None, "62043", CATALOGUE),
    ]
    # A verse-range colon is part of CAL's label; only ": " separates the description.
    assert [(match.label, match.description) for match in result.matches[:2]] == [
        ("John 13:15-16:9 Cambridge TS", None),
        (
            "Prodig2",
            "Prodigal Son, no. 2S. P. Brock, 'Fragments of Ps-John Chrysostom, Homily on the "
            "Prodigal Son, in Christian Palestinian Aramaic,' Le Museon 112(1999): 335-62.",
        ),
    ]
    assert result.matches[2].label == "P Jn"
    assert result.matches[2].description is not None
    assert result.matches[2].description.startswith("chapter 2 verse 2")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new"),
    [
        # cset=C is only observed on CPA (55…) nodes.
        (b"subtext=62043&cset=U", b"subtext=62043&cset=C"),
        # Only a single lowercase letter suffix is a CPA node identifier.
        (b"subtext=5500056125a&cset=C", b"subtext=5500056125ab&cset=C"),
        (b"subtext=5500056125a&cset=C", b"subtext=5500056125A&cset=C"),
        # A letter suffix outside CPA is not an observed node shape.
        (b"subtext=62043&cset=U", b"subtext=62043a&cset=U"),
        # A letter-suffixed node is only observed with cset=C.
        (b"subtext=5500056125a&cset=C", b"subtext=5500056125a&cset=U"),
        # cset=C on a node outside the observed subdivided CPA files.
        (b"subtext=5500056125a&cset=C", b"subtext=5599956125a&cset=C"),
        (b"subtext=55400122&cset=C", b"subtext=55999122&cset=C"),
        # An unknown script selector stays drift, CPA or not.
        (b"subtext=55400122&cset=C", b"subtext=55400122&cset=Q"),
    ],
)
async def test_unobserved_node_shapes_remain_parser_drift(old: bytes, new: bytes) -> None:
    body = SEARCH.read_bytes()
    assert old in body

    with pytest.raises(TextParseError):
        await _search(body.replace(old, new))


@pytest.mark.anyio
async def test_suffixed_cpa_node_catalogue_lists_its_text() -> None:
    requests: list[CalRequest] = []
    result = await _catalogue("5500056125a", NODE.read_bytes(), requests)

    assert [dict(request.params) for request in requests] == [{"subtext": "5500056125a"}]
    assert result.categories == ()
    assert [(text.file_id, text.subtext_id, text.label) for text in result.texts] == [
        ("55000", "56125a", "John 13:15-16:9 Cambridge TS")
    ]


@pytest.mark.anyio
async def test_suffix_less_toggle_on_another_node_is_not_skipped() -> None:
    # Only the requested node's own suffix-less toggle is navigation.
    body = NODE.read_bytes().replace(
        b'href="/showsubtexts.php?subtext=5500056125&script=U">Serto',
        b'href="/showsubtexts.php?subtext=5500056126&script=U">Serto',
    )

    result = await _catalogue("5500056125a", body)

    assert [(category.category_id, category.label) for category in result.categories] == [
        ("5500056126", "Serto")
    ]


@pytest.mark.anyio
async def test_suffix_less_self_link_on_a_decimal_node_is_still_a_category() -> None:
    # Stripping a letter only applies to a suffixed request; 6204 is a different node from 62043.
    body = NODE.read_bytes().replace(
        b'href="/showsubtexts.php?subtext=5500056125&script=U">Serto',
        b'href="/showsubtexts.php?subtext=5540012&script=U">Serto',
    )

    result = await _catalogue("55400122", body)

    assert [(category.category_id, category.label) for category in result.categories] == [
        ("5540012", "Serto"),
        ("5500056125", "CPA"),
    ]


@pytest.mark.parametrize(
    "bad",
    [
        "5500056125ab",
        "5500056125A",
        "62043a",
        "55a",
        "a",
        "55-1a",
        " 5500056125a",
        # A suffixed id whose file part is not an observed subdivided CPA file.
        "5599956125a",
        "5500256125a",
        "55000a",
    ],
)
@pytest.mark.anyio
async def test_catalogue_rejects_other_suffixed_identifiers_before_cal(bad: str) -> None:
    requests: list[CalRequest] = []

    with pytest.raises(CalInputError):
        await _catalogue(bad, NODE.read_bytes(), requests)

    assert requests == []
