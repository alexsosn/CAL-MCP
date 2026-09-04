from __future__ import annotations

import importlib
import importlib.metadata
import shutil
import socket
import sys

import pytest
from mcp import Client, StdioServerParameters

from cal_mcp import __version__


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
    # registration must stay local and lazy; CAL traffic starts only on a tool call.
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        assert client.server_info is not None
        assert client.server_info.name == "cal-mcp"
        assert client.server_info.version == __version__
        await _assert_public_lexicon_tool(client)


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
