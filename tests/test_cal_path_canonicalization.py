"""Issue #301: CAL request paths must not alias a different URL endpoint.

All fixtures stay local. No CAL network traffic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest

import cal_mcp.client as client_module
from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalRequest,
    CalRequestValidationError,
    CalResponse,
)


def html_response() -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/entry.php",
        body=b"<html>offline fixture</html>",
        content_type="text/html",
        retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    [
        "foo/..",  # urljoin silently resolves this to the CAL origin root
        "foo/./entry.php",
        "./entry.php",
        "foo//entry.php",
        "foo/%2e%2e/entry.php",
        "foo/%2Fentry.php",
        "foo/%5centry.php",
        "foo/%00entry.php",
        "foo\\entry.php",
        "entry.php\\..",
        "entry.php\x00",
        "\tentry.php",
        "entry.php\n",
    ],
)
async def test_ambiguous_endpoint_path_is_rejected_before_any_transport_or_hook(
    path: str,
) -> None:
    calls: list[CalRequest] = []
    hooks: list[int] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        calls.append(request)
        return html_response()

    client = CalHttpClient(
        transport=transport,
        before_transport_attempt=lambda: hooks.append(1),
    )
    for _ in range(2):
        with pytest.raises(CalRequestValidationError, match="CAL request path"):
            await client.fetch(CalRequest("GET", path), parser=lambda r: r.body, cache_namespace="path")
    assert calls == []
    assert hooks == []


@pytest.mark.anyio
async def test_legitimate_relative_endpoints_and_encoded_parameter_values_survive() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return html_response()

    client = CalHttpClient(transport=transport)
    for path in ("entry.php", "/entry.php", "cgi-bin/getlex.php"):
        await client.fetch(
            CalRequest(
                method="GET",
                path=path,
                params=(("lemma", "br N"), ("pattern", "../%2f שלום"), ("lemma", "ktb V")),
            ),
            parser=lambda r: r.body,
            cache_namespace="endpoints",
        )
    assert [item.path for item in requests] == [
        "entry.php",
        "entry.php",
        "cgi-bin/getlex.php",
    ] or [item.path for item in requests] == ["entry.php", "cgi-bin/getlex.php"]
    assert requests[0].params == (
        ("lemma", "br N"),
        ("pattern", "../%2f שלום"),
        ("lemma", "ktb V"),
    )


@pytest.mark.anyio
async def test_real_url_construction_keeps_canonical_endpoint_with_mock_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    original = httpx2.AsyncClient

    async def handler(request: httpx2.Request) -> httpx2.Response:
        observed.append(str(request.url))
        return httpx2.Response(
            200,
            request=request,
            content=b"<html>offline canonical</html>",
            headers={"content-type": "text/html"},
        )

    mocked = httpx2.MockTransport(handler)

    def factory(**kwargs: object) -> httpx2.AsyncClient:
        return original(transport=mocked, **kwargs)

    monkeypatch.setattr(client_module.httpx2, "AsyncClient", factory)
    async with CalHttpClient(config=CalClientConfig(max_retries=0, cache_enabled=False)) as client:
        result = await client.fetch(
            CalRequest("GET", "/cgi-bin/getlex.php", params=(("lemma", "br N"),)),
            parser=lambda r: r.body,
            cache_namespace="canonical",
        )
    assert result.value == b"<html>offline canonical</html>"
    assert len(observed) == 1
    assert urlsplit(observed[0]).netloc == "cal.huc.edu"
    assert urlsplit(observed[0]).path == "/cgi-bin/getlex.php"
    assert parse_qs(urlsplit(observed[0]).query) == {"lemma": ["br N"]}
