"""Issue #260: the accepted biblical book labels are discoverable from the schema and the error."""

from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator, ValidationError
from mcp import Client

import cal_mcp.server as server_module
from cal_mcp.biblical import _BOOK_IDS, cal_biblical_book_id
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalInputError
from cal_mcp.syriac import SyriacService
from cal_mcp.targum import TargumService

# CAL's current selector order (rechecked live 2026-10-10 against searching/peshsearch.html).
LABELS = list(_BOOK_IDS)
TOOLS = ("cal_targum_parallel", "cal_syriac_peshitta_parallel")


def test_label_table_is_cals_36_books_in_selector_order() -> None:
    assert len(LABELS) == 36
    assert LABELS[:5] == ["Gen", "Exod", "Levit", "Numb", "Deut"]
    assert LABELS[-1] == "Esther"


@pytest.mark.anyio
@pytest.mark.parametrize("tool_name", TOOLS)
async def test_book_schema_enumerates_cal_labels_in_order(tool_name: str) -> None:
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    schema = tools[tool_name].input_schema
    assert schema["properties"]["book"]["type"] == "string"
    assert schema["properties"]["book"]["enum"] == LABELS

    validator = Draft202012Validator(schema)
    validator.validate({"book": "1 Sam", "chapter": 1, "verse": 1})
    for rejected in ("Genesis", "gen", "Gen ", "Matthew", ""):
        with pytest.raises(ValidationError):
            validator.validate({"book": rejected, "chapter": 1, "verse": 1})


@pytest.mark.parametrize("bad", ["Genesis", "Matthew", "", "gen"])
def test_invalid_book_error_lists_every_accepted_label(bad: str) -> None:
    with pytest.raises(CalInputError) as caught:
        cal_biblical_book_id(bad)

    message = str(caught.value)
    assert all(f"'{label}'" in message for label in LABELS)
    assert len(message) <= 500


def _rejecting_client() -> tuple[CalHttpClient, list[CalRequest]]:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        raise AssertionError("an invalid book must not reach CAL")

    return CalHttpClient(transport=transport), requests


@pytest.mark.anyio
async def test_invalid_book_fails_before_any_cal_request() -> None:
    client, requests = _rejecting_client()
    try:
        with pytest.raises(CalInputError, match="'Gen'"):
            await TargumService(client).parallel("Genesis", 1, 1)
        with pytest.raises(CalInputError, match="'Gen'"):
            await SyriacService(client).peshitta_parallel("Genesis", 1, 1)
    finally:
        await client.aclose()
    assert requests == []
