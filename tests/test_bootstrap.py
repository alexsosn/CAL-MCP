from __future__ import annotations

import importlib
import importlib.metadata
import shutil
import socket
import sys
from datetime import UTC, datetime

import pytest
from mcp import Client, StdioServerParameters

from cal_mcp import __version__
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse


async def _assert_public_tools(client: Client) -> None:
    tools = {tool.name: tool for tool in (await client.list_tools()).tools}
    assert set(tools) == {
        "cal_lexicon_lookup",
        "cal_gloss_search",
        "cal_citation_text_search",
        "cal_text_catalogue",
        "cal_text_search",
        "cal_text_page",
        "cal_token_analysis",
        "cal_text_concordance",
        "cal_kwic_texts",
        "cal_kwic_dialects",
        "cal_kwic_dialect",
        "cal_bibliography_authors",
        "cal_bibliography_author",
        "cal_bibliography_keyword",
        "cal_bibliography_lemma",
        "cal_targum_parallel",
        "cal_targum_concordance",
        "cal_targum_hebrew_lemmas",
        "cal_targum_hebrew_reflexes",
        "cal_syriac_texts",
        "cal_syriac_missing_words",
        "cal_syriac_peshitta_parallel",
    }

    lexicon_schema = tools["cal_lexicon_lookup"].input_schema
    assert set(lexicon_schema["properties"]) == {"query", "lemma_key"}
    assert lexicon_schema["required"] == ["query"]

    gloss_schema = tools["cal_gloss_search"].input_schema
    assert set(gloss_schema["properties"]) == {"query", "all_glosses"}
    assert gloss_schema["required"] == ["query"]

    citation_schema = tools["cal_citation_text_search"].input_schema
    assert set(citation_schema["properties"]) == {"query"}
    assert citation_schema["required"] == ["query"]

    catalogue_schema = tools["cal_text_catalogue"].input_schema
    assert set(catalogue_schema["properties"]) == {"category_id"}
    assert "required" not in catalogue_schema or catalogue_schema["required"] == []

    text_search_schema = tools["cal_text_search"].input_schema
    assert set(text_search_schema["properties"]) == {"query"}
    assert text_search_schema["required"] == ["query"]

    text_page_schema = tools["cal_text_page"].input_schema
    assert set(text_page_schema["properties"]) == {"file_id", "subtext_id", "page"}
    assert text_page_schema["required"] == ["file_id"]

    token_schema = tools["cal_token_analysis"].input_schema
    assert set(token_schema["properties"]) == {"coordinate", "word_index"}
    assert token_schema["required"] == ["coordinate", "word_index"]

    concordance_schema = tools["cal_text_concordance"].input_schema
    assert set(concordance_schema["properties"]) == {"text_id", "script"}
    assert concordance_schema["required"] == ["text_id"]

    kwic_texts_schema = tools["cal_kwic_texts"].input_schema
    assert set(kwic_texts_schema["properties"]) == {"lemma_key", "text_ids", "script"}
    assert kwic_texts_schema["required"] == ["lemma_key", "text_ids"]

    kwic_dialects_schema = tools["cal_kwic_dialects"].input_schema
    assert set(kwic_dialects_schema["properties"]) == {"lemma_key"}
    assert kwic_dialects_schema["required"] == ["lemma_key"]

    kwic_dialect_schema = tools["cal_kwic_dialect"].input_schema
    assert set(kwic_dialect_schema["properties"]) == {"lemma_key", "dialect_id"}
    assert kwic_dialect_schema["required"] == ["lemma_key", "dialect_id"]

    bibliography_authors_schema = tools["cal_bibliography_authors"].input_schema
    assert set(bibliography_authors_schema["properties"]) == {"prefix"}
    assert bibliography_authors_schema["required"] == ["prefix"]

    bibliography_author_schema = tools["cal_bibliography_author"].input_schema
    assert set(bibliography_author_schema["properties"]) == {"author"}
    assert bibliography_author_schema["required"] == ["author"]

    bibliography_keyword_schema = tools["cal_bibliography_keyword"].input_schema
    assert set(bibliography_keyword_schema["properties"]) == {"keyword"}
    assert bibliography_keyword_schema["required"] == ["keyword"]

    bibliography_lemma_schema = tools["cal_bibliography_lemma"].input_schema
    assert set(bibliography_lemma_schema["properties"]) == {"lemma_key"}
    assert bibliography_lemma_schema["required"] == ["lemma_key"]

    targum_parallel_schema = tools["cal_targum_parallel"].input_schema
    assert set(targum_parallel_schema["properties"]) == {
        "book",
        "chapter",
        "verse",
        "include_peshitta",
        "include_samaritan",
    }
    assert targum_parallel_schema["required"] == ["book", "chapter", "verse"]

    targum_concordance_schema = tools["cal_targum_concordance"].input_schema
    assert set(targum_concordance_schema["properties"]) == {"lemma_key"}
    assert targum_concordance_schema["required"] == ["lemma_key"]

    targum_hebrew_lemmas_schema = tools["cal_targum_hebrew_lemmas"].input_schema
    assert set(targum_hebrew_lemmas_schema["properties"]) == {"initial", "targum"}
    assert targum_hebrew_lemmas_schema["required"] == ["initial", "targum"]

    targum_hebrew_reflexes_schema = tools["cal_targum_hebrew_reflexes"].input_schema
    assert set(targum_hebrew_reflexes_schema["properties"]) == {"targum", "mt_lemma_id"}
    assert targum_hebrew_reflexes_schema["required"] == ["targum", "mt_lemma_id"]

    syriac_texts_schema = tools["cal_syriac_texts"].input_schema
    assert set(syriac_texts_schema["properties"]) == {"category"}
    assert syriac_texts_schema["required"] == ["category"]

    syriac_missing_words_schema = tools["cal_syriac_missing_words"].input_schema
    assert set(syriac_missing_words_schema["properties"]) == {"category"}
    assert syriac_missing_words_schema["required"] == ["category"]

    syriac_peshitta_schema = tools["cal_syriac_peshitta_parallel"].input_schema
    assert set(syriac_peshitta_schema["properties"]) == {"book", "chapter", "verse"}
    assert syriac_peshitta_schema["required"] == ["book", "chapter", "verse"]

    for schema in (
        lexicon_schema,
        gloss_schema,
        citation_schema,
        catalogue_schema,
        text_search_schema,
        text_page_schema,
        token_schema,
        concordance_schema,
        kwic_texts_schema,
        kwic_dialects_schema,
        kwic_dialect_schema,
        bibliography_authors_schema,
        bibliography_author_schema,
        bibliography_keyword_schema,
        bibliography_lemma_schema,
        targum_parallel_schema,
        targum_concordance_schema,
        targum_hebrew_lemmas_schema,
        targum_hebrew_reflexes_schema,
        syriac_texts_schema,
        syriac_missing_words_schema,
        syriac_peshitta_schema,
    ):
        for private_parameter in (
            "English",
            "secondary",
            "first3",
            "myauthor",
            "cits",
            "cset",
            "sub",
            "clen",
            "coord",
            "word",
            "R1",
            "texts",
            "charset",
            "lemma",
            "pos",
            "lth",
            "bookname",
            "Peshitta",
            "Sam",
        ):
            assert private_parameter not in schema["properties"]

    for schema in (
        bibliography_authors_schema,
        bibliography_author_schema,
        bibliography_keyword_schema,
        bibliography_lemma_schema,
    ):
        for unsupported_bound in ("page", "offset", "limit"):
            assert unsupported_bound not in schema["properties"]

    for schema in (syriac_texts_schema, syriac_missing_words_schema, syriac_peshitta_schema):
        for private_syriac_parameter in (
            "bookname",
            "dial",
            "cset",
            "file",
            "keyword",
            "coord",
        ):
            assert private_syriac_parameter not in schema["properties"]


@pytest.mark.anyio
async def test_server_import_and_introspection_do_not_require_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("server import/introspection must not open a network socket")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)

    # Import the server itself while the network guard is active. Public tool
    # registration must stay local; CAL traffic starts only on a tool call.
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        assert client.server_info is not None
        assert client.server_info.name == "cal-mcp"
        assert client.server_info.version == __version__
        await _assert_public_tools(client)


@pytest.mark.anyio
async def test_public_tool_reuses_one_server_client_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    transport_calls = 0
    clients: list[CalHttpClient] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal transport_calls
        del config
        transport_calls += 1
        assert request.path == "browseSKEYheaders.php"
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22",
            body=(
                b'<html><body><div><a href="/oneentry.php?lemma=br+N">br n.m.</a></div>'
                b'<div>son</div><div><a href="/oneentry.php?lemma=br%232+N">br n.m.</a></div>'
                b"<div>bar</div></body></html>"
            ),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        )

    def client_factory() -> CalHttpClient:
        client = CalHttpClient(transport=transport)
        clients.append(client)
        return client

    monkeypatch.setattr(server_module, "CalHttpClient", client_factory)

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        first = await client.call_tool("cal_lexicon_lookup", {"query": "br"})
        second = await client.call_tool("cal_lexicon_lookup", {"query": "br"})
        assert first.structured_content == second.structured_content

    assert len(clients) == 1
    assert transport_calls == 1


def test_package_version_is_exposed() -> None:
    assert __version__ == importlib.metadata.version("cal-mcp")


@pytest.mark.anyio
async def test_installed_entry_point_starts_over_stdio() -> None:
    executable = shutil.which("cal-mcp")
    assert executable is not None

    async with Client(StdioServerParameters(command=executable)) as client:
        assert client.server_info is not None
        assert client.server_info.name == "cal-mcp"
        assert client.server_info.version == __version__
        await _assert_public_tools(client)
