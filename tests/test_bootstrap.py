from __future__ import annotations

import importlib.metadata
import shutil
import socket

import pytest

from cal_mcp import __version__
from cal_mcp.server import mcp
from mcp import Client, StdioServerParameters


@pytest.mark.anyio
async def test_server_introspection_does_not_require_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("bootstrap/introspection must not open a network socket")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)

    async with Client(mcp, raise_exceptions=True) as client:
        assert client.server_info is not None
        assert client.server_info.name == "cal-mcp"
        assert client.server_info.version == __version__
        assert (await client.list_tools()).tools == []


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
        assert (await client.list_tools()).tools == []
