"""ONE-TIME bounded installed-wheel MCP acceptance; remove after run (#262).

Not a production command. This runner must execute from a fresh wheel venv,
with cwd outside the repository, and MUST NOT be run repeatedly or on failure.
The separate private child-side cap is 38: one exact text page, then 37 tokens.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import cal_mcp
from mcp import Client, StdioServerParameters

VERSES = ("620430101", "620430102", "620430103", "620430104")
MAX_ATTEMPTS = 38
WRAPPER = r'''
import atexit
import json
import os
import time
from pathlib import Path

import cal_mcp.server as server

LIMIT = 38
started = []
original = server.CalHttpClient

def before_transport_attempt():
    if len(started) >= LIMIT:
        raise RuntimeError("one-time CAL acceptance transport cap of 38 exhausted")
    started.append(time.monotonic())

def report():
    path = Path(os.environ["CAL_MCP_262_PRIVATE_REPORT_PATH"])
    path.write_text(
        json.dumps({"actual_cal_transport_attempts": len(started),
                    "max_cal_transport_attempts": LIMIT,
                    "attempt_starts_monotonic": started}),
        encoding="utf-8",
    )

atexit.register(report)

def metered_client(*, config=None, **kwargs):
    if config is None or config.min_request_interval_seconds < 1:
        raise RuntimeError("one-time live acceptance requires MCP's paced client")
    if kwargs:
        raise RuntimeError("unexpected MCP client constructor arguments")
    return original(config=config, before_transport_attempt=before_transport_attempt)

server.CalHttpClient = metered_client
server.main([])
'''


def _trusted_source(value: object) -> bool:
    if not isinstance(value, str):
        return False
    url = urlsplit(value)
    return (
        url.scheme == "https"
        and url.hostname == "cal.huc.edu"
        and url.username is None
        and url.password is None
        and url.port is None
        and not url.fragment
    )


def _expect_public_response(result: object, operation: str) -> dict[str, object]:
    if getattr(result, "is_error", None):
        data = getattr(result, "structured_content", None)
        err = data.get("error") if isinstance(data, dict) else None
        kind = err.get("kind") if isinstance(err, dict) else "untyped"
        status = err.get("status_code") if isinstance(err, dict) else None
        raise AssertionError(
            f"CAL-MCP live acceptance {operation} failed: kind={kind}, status={status}"
        )
    data = getattr(result, "structured_content", None)
    if not isinstance(data, dict):
        raise AssertionError(f"{operation} missing structured content")
    return data


async def _accept(wrapper: Path, report: Path) -> dict[str, object]:
    env = dict(os.environ)
    env.pop("CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS", None)
    env.pop("CAL_MCP_LIVE_SMOKE_REPORT_PATH", None)
    env["CAL_MCP_262_PRIVATE_REPORT_PATH"] = str(report)
    async with Client(
        StdioServerParameters(command=sys.executable, args=[str(wrapper)], env=env),
        raise_exceptions=True,
    ) as client:
        tools = {item.name: item for item in (await client.list_tools()).tools}
        assert len(tools) == 36 and "cal_text_page" in tools and "cal_token_analysis" in tools
        page_result = await client.call_tool(
            "cal_text_page", {"file_id": "62043", "subtext_id": "01", "page": 1}
        )
        page_data = _expect_public_response(page_result, "cal_text_page")
        assert page_data.get("status") == "found"
        provenance = page_data.get("provenance")
        assert isinstance(provenance, dict) and _trusted_source(provenance.get("source_url"))
        page = page_data.get("page")
        assert isinstance(page, dict) and isinstance(page.get("lines"), list)

        handles: list[tuple[str, int]] = []
        for line in page["lines"]:
            assert isinstance(line, dict)
            tokens = line.get("tokens")
            assert isinstance(tokens, list)
            for token in tokens:
                assert isinstance(token, dict)
                coordinate = token.get("coordinate")
                index = token.get("word_index")
                if coordinate in VERSES:
                    assert type(index) is int and index >= 0
                    handles.append((coordinate, index))
        assert len(handles) == 37, (
            "Expected 37 distinct documented Peshitta John 1:1-4 tokens; "
            f"CAL page returned {len(handles)}"
        )
        assert len(set(handles)) == 37
        assert set(coord for coord, _ in handles) == set(VERSES)

        counts: dict[str, int] = {}
        for coordinate, index in handles:
            result = await client.call_tool(
                "cal_token_analysis", {"coordinate": coordinate, "word_index": index}
            )
            data = _expect_public_response(result, "cal_token_analysis")
            assert data.get("status") in {"found", "not_found"}
            assert data.get("coordinate") == coordinate
            assert data.get("word_index") == index
            source = data.get("provenance")
            assert isinstance(source, dict) and _trusted_source(source.get("source_url"))
            counts[coordinate] = counts.get(coordinate, 0) + 1
        return {"tokens": len(handles), "per_verse_tokens": counts}


def main() -> None:
    # Require an installed distribution outside the checked-out repository.
    installed = Path(cal_mcp.__file__).resolve()
    assert "site-packages" in installed.parts, installed
    with TemporaryDirectory(prefix="cal-mcp-262-once-") as tmp:
        base = Path(tmp)
        wrapper = base / "metered_stdio_server.py"
        report = base / "meter.json"
        wrapper.write_text(WRAPPER, encoding="utf-8")
        try:
            outcome = asyncio.run(_accept(wrapper, report))
        finally:
            if report.exists():
                meter = json.loads(report.read_text(encoding="utf-8"))
                timestamps = meter["attempt_starts_monotonic"]
                deltas = [b - a for a, b in zip(timestamps, timestamps[1:])]
                print(json.dumps({
                    "meter": {
                        "actual_cal_transport_attempts": meter["actual_cal_transport_attempts"],
                        "max_cal_transport_attempts": meter["max_cal_transport_attempts"],
                        "min_seconds_between_attempts": min(deltas) if deltas else None,
                    }
                }))
        assert meter["actual_cal_transport_attempts"] == MAX_ATTEMPTS
        assert meter["max_cal_transport_attempts"] == MAX_ATTEMPTS
        assert len(timestamps) == MAX_ATTEMPTS
        assert all(delta >= 0.90 for delta in deltas), "MCP transport starts were not paced"
        print(json.dumps({"status": "success", **outcome}))


if __name__ == "__main__":
    main()
