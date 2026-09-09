from __future__ import annotations

import importlib
import importlib.util
import socket
from pathlib import Path
from types import ModuleType

import pytest
from mcp import Client

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts" / "verify_release_artifact.py"


def _load_release_surface() -> ModuleType:
    return importlib.import_module("cal_mcp.release_surface")


def _load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "cal_mcp_release_verifier_sync_test",
        VERIFIER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.anyio
async def test_frozen_release_surface_matches_actual_runtime_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("public registry introspection must stay offline")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    release_surface = _load_release_surface()

    server_module = importlib.import_module("cal_mcp.server")
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        actual = frozenset(tool.name for tool in (await client.list_tools()).tools)

    assert actual == release_surface.V01_PUBLIC_TOOLS


def test_surface_equality_rejects_equal_count_name_drift() -> None:
    release_surface = _load_release_surface()
    expected = release_surface.V01_PUBLIC_TOOLS
    removed = min(expected)
    drifted = (expected - {removed}) | {"cal_equal_count_drift_sentinel"}

    assert len(drifted) == len(expected)
    assert drifted != expected


def test_release_verifier_consumes_shared_manifest_without_duplicate_constants() -> None:
    release_surface = _load_release_surface()
    verifier = _load_verifier()

    assert verifier.V01_PUBLIC_TOOLS is release_surface.V01_PUBLIC_TOOLS
    assert not hasattr(verifier, "EXPECTED_TOOLS")
    assert not hasattr(verifier, "EXPECTED_TOOL_COUNT")
