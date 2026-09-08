from __future__ import annotations

import importlib
import json
import sys

import pytest
from mcp import Client

_FIELD_SLUGS = (
    "alchemy",
    "anatomy",
    "architecture",
    "astronomy",
    "botany",
    "cantillation",
    "chemistry",
    "geography",
    "geology",
    "geometry",
    "grammar",
    "liturgy",
    "logic",
    "magic",
    "mathematics",
    "medicine",
    "music",
    "philosophy",
    "topography",
    "zoology",
)


@pytest.mark.anyio
async def test_specialized_gloss_field_is_discoverable_in_public_schema() -> None:
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert "cal_gloss_field" in tools
    field_schema = tools["cal_gloss_field"].input_schema
    assert set(field_schema["properties"]) == {"field"}
    assert field_schema["required"] == ["field"]

    encoded_schema = json.dumps(field_schema, sort_keys=True)
    for field_slug in _FIELD_SLUGS:
        assert f'"{field_slug}"' in encoded_schema

    ordinary_schema = tools["cal_gloss_search"].input_schema
    assert set(ordinary_schema["properties"]) == {"query", "all_glosses"}
    assert ordinary_schema["required"] == ["query"]
