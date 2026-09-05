from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from mcp import Client


@pytest.mark.anyio
async def test_external_citation_tools_expose_only_public_workflow_parameters() -> None:
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    dialects = tools["cal_external_citation_dialects"].input_schema
    sources = tools["cal_external_citation_sources"].input_schema
    citations = tools["cal_external_citations"].input_schema

    assert set(dialects["properties"]) == set()
    assert "required" not in dialects or dialects["required"] == []
    assert set(sources["properties"]) == {"dialect_id"}
    assert sources["required"] == ["dialect_id"]
    assert set(citations["properties"]) == {"source_abbrev"}
    assert citations["required"] == ["source_abbrev"]

    for schema in (dialects, sources, citations):
        for private_parameter in ("dial", "dial1", "abbrev", "cits", "lemma"):
            assert private_parameter not in schema["properties"]


def test_server_instructions_distinguish_external_citations_from_english_search() -> None:
    source = Path("src/cal_mcp/server.py").read_text(encoding="utf-8")
    instructions = source.split("instructions=(", 1)[1].split("version=__version__", 1)[0]

    assert "cal_external_citation_dialects" in instructions
    assert "cal_external_citation_sources" in instructions
    assert "cal_external_citations" in instructions
    assert "cal_citation_text_search" in instructions
    assert "not in the online" in instructions.lower() or "non-online" in instructions.lower()


def test_external_citation_docs_include_concrete_non_online_example() -> None:
    docs = Path("docs/tools/external-citations.md").read_text(encoding="utf-8")

    assert "Syriac" in docs
    assert "1CorH" in docs
    assert "1CorH 12:28" in docs
    assert "not an online CAL passage coordinate" in docs
