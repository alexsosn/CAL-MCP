"""Issue #218: current direct-Mandaic alphanumeric machine coordinates.

See docs/research/issue-218-mandaic-machine-coordinates.md.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, cast

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageStatus, TextParseError, TextService
from cal_mcp.token_analysis import TokenAnalysisService, TokenAnalysisStatus

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _mandaic_coordinate_predicate() -> Callable[[object], bool]:
    module = importlib.import_module("cal_mcp.identifiers")
    predicate = getattr(module, "is_cal_mandaic_machine_coordinate", None)
    assert callable(predicate), "identifiers.is_cal_mandaic_machine_coordinate must exist"
    return cast(Callable[[object], bool], predicate)


@pytest.mark.parametrize(
    "coordinate",
    [
        "7442500a",
        "74425231aa",
        "74429000a",
        "74429A01",
        "74425001",
        "74429001",
    ],
)
def test_researched_mandaic_machine_coordinate_shapes_are_accepted(coordinate: str) -> None:
    assert _mandaic_coordinate_predicate()(coordinate)


@pytest.mark.parametrize(
    "coordinate",
    [
        "",
        "74425a",
        "74425231aaa",
        "74425-001",
        "74425 001",
        "74429A",
        "74429B01",
        "74429A01x",
        "7442600a",
        "74430A01",
        "x7442500a",
    ],
)
def test_mandaic_machine_coordinate_predicate_rejects_near_misses(coordinate: str) -> None:
    predicate = _mandaic_coordinate_predicate()
    assert not predicate(coordinate)


def _response(fixture: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / fixture).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 2, tzinfo=UTC),
    )


class PageFixtureTransport:
    def __init__(self, file_id: str, fixture: str) -> None:
        self.file_id = file_id
        self.fixture = fixture
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        expected = CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", self.file_id)),
        )
        assert request == expected
        return _response(
            self.fixture,
            f"https://cal.huc.edu/get_a_chapter.php?cset=M&file={self.file_id}",
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("file_id", "fixture", "expected_coordinates"),
    [
        (
            "74425",
            "text_page_mandaic_74425_alphanumeric_structural.html",
            ["7442500a", "74425231aa"],
        ),
        (
            "74429",
            "text_page_mandaic_74429_uppercase_structural.html",
            ["74429A01"],
        ),
    ],
)
async def test_direct_mandaic_page_preserves_researched_alphanumeric_coordinates(
    file_id: str,
    fixture: str,
    expected_coordinates: list[str],
) -> None:
    transport = PageFixtureTransport(file_id, fixture)
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page(file_id, page=1)
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert [line.coordinate for line in result.page.lines] == expected_coordinates
    assert [
        token.coordinate
        for line in result.page.lines
        for token in line.tokens
    ] == expected_coordinates
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", file_id)),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("fixture", "old", "new"),
    [
        (
            "text_page_mandaic_74425_alphanumeric_structural.html",
            b"74425231aa",
            b"74425231aaa",
        ),
        (
            "text_page_mandaic_74429_uppercase_structural.html",
            b"74429A01",
            b"74429B01",
        ),
        (
            "text_page_mandaic_74425_alphanumeric_structural.html",
            b"7442500a",
            b"7442600a",
        ),
    ],
)
async def test_direct_mandaic_page_rejects_unresearched_coordinate_shapes(
    fixture: str,
    old: bytes,
    new: bytes,
) -> None:
    file_id = "74429" if "74429" in fixture else "74425"
    body = (FIXTURES / fixture).read_bytes()
    assert old in body
    response = CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/get_a_chapter.php?cset=M&file={file_id}",
        body=body.replace(old, new),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 2, tzinfo=UTC),
    )

    class MutatedTransport:
        async def __call__(
            self,
            request: CalRequest,
            config: CalClientConfig,
        ) -> CalResponse:
            del request, config
            return response

    client = CalHttpClient(transport=MutatedTransport())
    try:
        with pytest.raises(TextParseError):
            await TextService(client).page(file_id, page=1)
    finally:
        await client.aclose()


class TokenAnalysisTransport:
    def __init__(self, coordinate: str) -> None:
        self.coordinate = coordinate
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return CalResponse(
            status_code=200,
            url=(
                "https://cal.huc.edu/getlex.php?"
                f"coord={self.coordinate}&word=0"
            ),
            body=(FIXTURES / "token_analysis_not_found.html").read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 2, tzinfo=UTC),
        )


@pytest.mark.anyio
@pytest.mark.parametrize("coordinate", ["74425231aa", "74429A01"])
async def test_token_analysis_accepts_returned_mandaic_coordinate(
    coordinate: str,
) -> None:
    transport = TokenAnalysisTransport(coordinate)
    client = CalHttpClient(transport=transport)
    try:
        result = await TokenAnalysisService(client).analyze(coordinate, 0)
    finally:
        await client.aclose()

    assert result.status is TokenAnalysisStatus.NOT_FOUND
    assert result.coordinate == coordinate
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="getlex.php",
            params=(("coord", coordinate), ("word", "0")),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "coordinate",
    [
        "74425231aaa",
        "74429B01",
        "74429A",
        "7442600a",
        "74430A01",
    ],
)
async def test_token_analysis_rejects_unresearched_mandaic_coordinate_before_transport(
    coordinate: str,
) -> None:
    transport = TokenAnalysisTransport(coordinate)
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(ValueError):
            await TokenAnalysisService(client).analyze(coordinate, 0)
    finally:
        await client.aclose()

    assert transport.requests == []
