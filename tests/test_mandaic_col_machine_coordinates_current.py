"""Issue #220: current Mandaic 74421/col machine-coordinate identity.

See docs/research/issue-220-mandaic-col-machine-coordinates.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.identifiers import is_cal_machine_coordinate, is_cal_mandaic_machine_coordinate
from cal_mcp.texts import TextPageStatus, TextParseError, TextService
from cal_mcp.token_analysis import TokenAnalysisService, TokenAnalysisStatus

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


@pytest.mark.parametrize(
    "coordinate",
    ["74421col13614", "74421col14012"],
)
def test_col_machine_coordinates_use_only_the_special_mandaic_predicate(
    coordinate: str,
) -> None:
    assert not is_cal_machine_coordinate(coordinate)
    assert is_cal_mandaic_machine_coordinate(coordinate)


@pytest.mark.parametrize(
    "coordinate",
    [
        "74421col",
        "74421Col13614",
        "74421COL13614",
        "74421foo13614",
        "74422col13614",
        "74421col13-614",
        "74421col 13614",
        "74421xcol13614",
    ],
)
def test_col_machine_coordinate_near_misses_remain_invalid(coordinate: str) -> None:
    assert not is_cal_machine_coordinate(coordinate)
    assert not is_cal_mandaic_machine_coordinate(coordinate)


def test_token_analysis_executable_docs_name_74421_col_coordinate_identity() -> None:
    source = Path("src/cal_mcp/server.py").read_text(encoding="utf-8")
    tool = source.split("async def cal_token_analysis(", 1)[1].split("@mcp.tool(", 1)[0]

    assert "74421" in tool
    assert "col" in tool
    assert "opaque" in tool.lower()


def _response(fixture: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / fixture).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 2, tzinfo=UTC),
    )


class PageTransport:
    def __init__(self, subtext_id: str, fixture: str) -> None:
        self.subtext_id = subtext_id
        self.fixture = fixture
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        expected = CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74421"), ("sub", self.subtext_id)),
        )
        assert request == expected
        return _response(
            self.fixture,
            (
                "https://cal.huc.edu/get_a_chapter.php?"
                f"cset=M&file=74421&sub={self.subtext_id}"
            ),
        )


@pytest.mark.anyio
async def test_col_page_preserves_literal_subtext_machine_coordinate() -> None:
    transport = PageTransport("col", "text_page_mandaic_74421_col_structural.html")
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("74421", subtext_id="col")
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.file_id == "74421"
    assert result.page.text.subtext_id == "col"
    assert [line.coordinate for line in result.page.lines] == ["74421col13614"]
    assert result.page.lines[0].tokens[0].coordinate == "74421col13614"
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74421"), ("sub", "col")),
        )
    ]


@pytest.mark.anyio
async def test_numeric_74421_subtext_keeps_existing_decimal_coordinate_path() -> None:
    transport = PageTransport("103", "text_page_mandaic_74421_103_structural.html")
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("74421", subtext_id="103")
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.subtext_id == "103"
    assert result.page.lines[0].tokens[0].coordinate == "7442110313604"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new"),
    [
        (b"74421col13614", b"74421col"),
        (b"74421col13614", b"74421foo13614"),
        (b"74421col13614", b"74422col13614"),
    ],
)
async def test_col_page_rejects_wrong_literal_or_coordinate_identity(
    old: bytes,
    new: bytes,
) -> None:
    body = (FIXTURES / "text_page_mandaic_74421_col_structural.html").read_bytes()
    assert old in body
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/get_a_chapter.php?cset=M&file=74421&sub=col",
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
            await TextService(client).page("74421", subtext_id="col")
    finally:
        await client.aclose()


class TokenTransport:
    def __init__(self, coordinate: str) -> None:
        self.coordinate = coordinate
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/getlex.php?coord={self.coordinate}&word=0",
            body=(FIXTURES / "token_analysis_not_found.html").read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 2, tzinfo=UTC),
        )


@pytest.mark.anyio
async def test_token_analysis_accepts_returned_74421_col_coordinate() -> None:
    transport = TokenTransport("74421col13614")
    client = CalHttpClient(transport=transport)
    try:
        result = await TokenAnalysisService(client).analyze("74421col13614", 0)
    finally:
        await client.aclose()

    assert result.status is TokenAnalysisStatus.NOT_FOUND
    assert result.coordinate == "74421col13614"
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="getlex.php",
            params=(("coord", "74421col13614"), ("word", "0")),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "coordinate",
    [
        "74421col",
        "74421Col13614",
        "74421foo13614",
        "74422col13614",
    ],
)
async def test_token_analysis_rejects_unresearched_col_shapes_before_transport(
    coordinate: str,
) -> None:
    transport = TokenTransport(coordinate)
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(ValueError):
            await TokenAnalysisService(client).analyze(coordinate, 0)
    finally:
        await client.aclose()

    assert transport.requests == []
