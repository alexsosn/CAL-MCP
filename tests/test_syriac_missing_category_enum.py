"""Issue #159: discoverable exact Syriac missing-word selectors over MCP."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from jsonschema import Draft202012Validator, ValidationError
from mcp import Client

import cal_mcp.server as server_module
import cal_mcp.syriac as syriac_module
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalInputError
from cal_mcp.syriac import SyriacService

EXPECTED = (
    "adjectives",
    "adverbs",
    "miscellaneous",
    "nomina-agentis",
    "abstracts",
    "verbal-nouns",
    "verbs",
    "masculine-nouns",
    "feminine-nouns",
)


def _rejecting_client() -> tuple[CalHttpClient, list[CalRequest]]:
    requests: list[CalRequest] = []

    async def rejecting_transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        raise AssertionError("invalid missing-word category must not reach CAL")

    return CalHttpClient(transport=rejecting_transport), requests


@pytest.mark.anyio
async def test_missing_words_public_schema_exposes_only_current_nine_choices() -> None:
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    schema = tools["cal_syriac_missing_words"].input_schema
    assert set(schema["properties"]) == {"category"}
    assert schema["required"] == ["category"]

    # Exercise actual JSON Schema resolution, including any generated $defs/$ref.
    validator = Draft202012Validator(schema)
    for slug in EXPECTED:
        validator.validate({"category": slug})
    for rejected in ("ot-peshitta", "verbs ", "", "V", "VERBS", 7, None):
        with pytest.raises(ValidationError):
            validator.validate({"category": rejected})

    encoded = json.dumps(schema, sort_keys=True)
    assert all(f'"{slug}"' in encoded for slug in EXPECTED)


@pytest.mark.anyio
async def test_invalid_mcp_category_reports_all_valid_slugs_without_cal_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[CalRequest] = []

    def make_client() -> CalHttpClient:
        client, captured = _rejecting_client()
        # Keep the owned list accessible when the fake app context starts.
        requests.extend(captured)
        return client

    monkeypatch.setattr(server_module, "CalHttpClient", make_client)
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_syriac_missing_words", {"category": "ot-peshitta"})

    assert result.is_error is True
    envelope = result.structured_content
    assert envelope is not None
    public_error = envelope["error"]
    assert public_error["kind"] == "invalid_input"
    assert public_error["operation"] == "cal_syriac_missing_words"
    assert public_error["upstream_reached"] is False
    message = public_error["message"]
    assert len(message) <= 500
    assert all(slug in message for slug in EXPECTED)
    assert requests == []


@pytest.mark.anyio
async def test_invalid_direct_service_category_lists_valid_names_without_transport() -> None:
    client, requests = _rejecting_client()
    with pytest.raises(CalInputError) as exc:
        await SyriacService(client).missing_words("ot-peshitta")
    assert all(slug in str(exc.value) for slug in EXPECTED)
    assert requests == []


def test_enum_and_route_mapping_remain_exhaustively_synchronized() -> None:
    enum = getattr(syriac_module, "SyriacMissingWordCategory", None)
    assert enum is not None
    assert tuple(value.value for value in enum) == EXPECTED
    assert tuple(syriac_module._MISSING_WORD_PATHS) == tuple(enum)
