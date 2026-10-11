"""The documented default CAL pace must describe the actual HTTP client (#295)."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.anyio
async def test_real_transport_default_differs_from_explicit_and_offline_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("default-pacing contract must not contact CAL")

    monkeypatch.setattr(socket.socket, "connect", deny_network)

    async def fake(req: CalRequest, config: CalClientConfig) -> CalResponse:
        del req, config
        raise AssertionError("fake transport must not run in this test")

    real_default = CalHttpClient()
    explicit_config = CalHttpClient(config=CalClientConfig())
    offline_fake = CalHttpClient(transport=fake)
    try:
        assert real_default.config.min_request_interval_seconds == 3.0
        assert explicit_config.config.min_request_interval_seconds == 0.0
        assert offline_fake.config.min_request_interval_seconds == 0.0
    finally:
        await real_default.aclose()
        await explicit_config.aclose()
        await offline_fake.aclose()


def test_configuration_guide_distinguishes_real_default_from_programmatic_override() -> None:
    guide = (ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    assert "3 s for plain `CalHttpClient()` and the MCP server" in guide
    assert "0 s for explicitly supplied `CalClientConfig()` or injected fake transport" in guide
    assert (
        "Plain `CalHttpClient()` with the real HTTP transport defaults to three-second pacing."
        in guide
    )
    assert "three-second pacing is not a guaranteed CAL-accepted rate" in guide.lower()
    assert "defaults to one-second pacing" not in guide.lower()


def test_decision_d024_states_present_real_client_default_without_rewriting_history() -> None:
    decision = (ROOT / "wiki" / "decisions.md").read_text(encoding="utf-8")
    d024 = decision.split("## D-024", maxsplit=1)[1]
    assert "A direct `CalHttpClient()` using the real HTTP" in d024
    assert "transport also selects 3 seconds" in d024
    assert "transport also selects 1 second" not in d024
    assert "STILL encountered 429" in d024
