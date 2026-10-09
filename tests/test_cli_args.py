from __future__ import annotations

import subprocess
import sys

import pytest

from cal_mcp import __version__


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    # stdin is closed, so a CLI that wrongly starts the stdio server cannot block on a prompt; the
    # timeout catches a hang either way.
    return subprocess.run(
        [sys.executable, "-m", "cal_mcp", *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_version_prints_and_exits() -> None:
    result = _run("--version")

    assert result.returncode == 0
    assert result.stdout.strip() == f"cal-mcp {__version__}"


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage_and_exits(flag: str) -> None:
    result = _run(flag)

    assert result.returncode == 0
    assert "usage: cal-mcp" in result.stdout
    assert "stdio" in result.stdout
    assert "MCP" in result.stdout
    assert "jsonrpc" not in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [("--bogus",), ("foo",), ("--bogus", "--version"), ("--version", "--bogus"), ("--vers",)],
)
def test_unknown_argument_fails_with_usage(arguments: tuple[str, ...]) -> None:
    result = _run(*arguments)

    assert result.returncode != 0
    assert "usage: cal-mcp" in result.stderr
    assert result.stdout == ""
