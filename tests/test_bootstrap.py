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


async def _assert_public_lexicon_tool(client: Client) -> None:
    tools = (await client.list_tools()).tools
    assert [tool.name for tool in tools] == ["cal_lexicon_lookup"]
    schema = tools[0].input_schema
    assert set(schema["properties"]) == {"query", "lemma_key"}
    assert schema["required"] == ["query"]
    assert "first3" not in schema["properties"]
    assert "cits" not in schema["properties"]


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
        await _assert_public_lexicon_tool(client)


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
        await _assert_public_lexicon_tool(client)
