"""Offline real-stdio lifecycle test for the release smoke attempt-count channel."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters


@pytest.mark.anyio
async def test_real_stdio_server_writes_zero_attempts_on_shutdown(tmp_path: Path) -> None:
    """Use the real server entry point, never a CAL transport or simulated lifespan."""

    report = tmp_path / "attempts.json"
    environment = os.environ.copy()
    environment["CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS"] = "25"
    environment["CAL_MCP_LIVE_SMOKE_REPORT_PATH"] = str(report)

    async with Client(
        StdioServerParameters(
            command=sys.executable,
            args=["-m", "cal_mcp"],
            cwd=str(tmp_path),
            env=environment,
        )
    ) as client:
        tools = await client.list_tools()
        assert len(tools.tools) == 34
        assert not report.exists()

    assert json.loads(report.read_text(encoding="utf-8")) == {
        "actual_cal_transport_attempts": 0,
        "max_cal_transport_attempts": 25,
    }
