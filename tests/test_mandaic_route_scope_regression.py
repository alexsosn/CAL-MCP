from __future__ import annotations

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextService


class StopAfterRequest(Exception):
    pass


class RecordingStopTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        raise StopAfterRequest


@pytest.mark.anyio
@pytest.mark.parametrize("file_id", ["74501", "74717"])
async def test_direct_mandaic_page_one_does_not_invent_sub_selector(file_id: str) -> None:
    transport = RecordingStopTransport()
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(StopAfterRequest):
            await TextService(client).page(file_id, page=1)
    finally:
        await client.aclose()

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", file_id)),
        )
    ]


@pytest.mark.anyio
async def test_direct_mandaic_additional_page_fails_before_transport() -> None:
    transport = RecordingStopTransport()
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(ValueError, match="direct Mandaic.*page 1"):
            await TextService(client).page("74501", page=2)
    finally:
        await client.aclose()

    assert transport.requests == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "file_id",
    ["74401", "74411", "74700", "74701", "74702", "74711", "74714"],
)
async def test_researched_subdivided_mandaic_files_keep_sub_page_route(file_id: str) -> None:
    transport = RecordingStopTransport()
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(StopAfterRequest):
            await TextService(client).page(file_id, page=1)
    finally:
        await client.aclose()

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", file_id), ("sub", "001")),
        )
    ]
