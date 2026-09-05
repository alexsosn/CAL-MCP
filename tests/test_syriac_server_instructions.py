from __future__ import annotations

import importlib
import sys

import pytest
from mcp import Client


@pytest.mark.anyio
async def test_server_instructions_route_syriac_studies_tools() -> None:
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        assert client.server_info is not None
        instructions = client.server_info.instructions or ""
        assert "cal_syriac_texts" in instructions
        assert "cal_syriac_missing_words" in instructions
        assert "cal_syriac_peshitta_parallel" in instructions
        assert "issue #13" in instructions
        assert "cal_text_page" in instructions
        assert "cal_lexicon_lookup" in instructions
