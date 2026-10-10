"""Issue #268: the tool description says which gloss-search mode suits English→lemma lookup."""

from __future__ import annotations

import pytest
from mcp import Client

import cal_mcp.server as server_module


@pytest.mark.anyio
async def test_gloss_search_description_recommends_all_glosses_for_reverse_lookup() -> None:
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    description = " ".join((tools["cal_gloss_search"].description or "").split())
    assert "all_glosses=true" in description
    assert "English-to-lemma lookup" in description
    assert "not by relevance" in description
