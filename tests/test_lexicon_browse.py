from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urlencode

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LexiconParseError, parse_browse_page
from cal_mcp.normalization import AmbiguousQueryError, InputRepresentation, UnsupportedQueryError

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
_RETRIEVED_AT = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
_BR_URL = "https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22"
_NEXT_ANCHOR = '<a href="browseSKEYheaders.php?direction=1&sortkey=br">NEXT PAGE</a>'


class _BrowseService(Protocol):
    async def browse(
        self,
        prefix: str,
        *,
        representation: InputRepresentation | None = None,
        continuation: str | None = None,
    ) -> object: ...


class _Serializable(Protocol):
    def to_dict(self) -> dict[str, object]: ...


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _response(body: str, *, url: str = _BR_URL) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def _public_parser() -> Callable[[CalResponse], object]:
    module = importlib.import_module("cal_mcp.lexicon_browse")
    parser = getattr(module, "parse_lexicon_browse_page", None)
    assert callable(parser), "public browse parser must be implemented after the RED gate"
    return cast(Callable[[CalResponse], object], parser)


def _service(client: CalHttpClient) -> _BrowseService:
    module = importlib.import_module("cal_mcp.lexicon_browse")
    service_type = getattr(module, "LexiconBrowseService", None)
    assert callable(service_type), "LexiconBrowseService must be implemented after the RED gate"
    factory = cast(Callable[[CalHttpClient], _BrowseService], service_type)
    return factory(client)


def _entries(page: object) -> tuple[object, ...]:
    value = getattr(page, "entries", None)
    assert isinstance(value, tuple)
    return value


def _next(page: object) -> str | None:
    value = getattr(page, "next_continuation", None)
    assert value is None or isinstance(value, str)
    return value


def test_public_browse_parser_preserves_cal_order_and_next_continuation() -> None:
    page = _public_parser()(_response(_fixture("browse_br_unclosed_jump_2026_09_06.html")))

    entries = _entries(page)
    assert [getattr(item, "lemma_key", None) for item in entries] == ["br N", "br#2 N"]
    assert [getattr(item, "gloss", None) for item in entries] == ["son", "field, outside"]
    assert _next(page) == "br"


def test_existing_lookup_browse_parser_stays_navigation_agnostic() -> None:
    page = parse_browse_page(_response(_fixture("browse_br_unclosed_jump_2026_09_06.html")))

    assert [item.lemma_key for item in page.entries] == ["br N", "br#2 N"]
    assert getattr(page, "next_continuation", None) is None


@pytest.mark.parametrize(
    "href",
    [
        "https://example.org/browseSKEYheaders.php?direction=1&sortkey=br",
        "legacy/browseSKEYheaders.php?direction=1&sortkey=br",
        "browseSKEYheaders.php?direction=2&sortkey=br",
        "browseSKEYheaders.php?direction=1&sortkey=",
        "browseSKEYheaders.php?direction=1&sortkey=br&extra=1",
        "browseSKEYheaders.php?direction=1&sortkey=br#fragment",
    ],
)
def test_public_browse_parser_fails_closed_on_changed_next_page_route(href: str) -> None:
    html = _fixture("browse_br_unclosed_jump_2026_09_06.html").replace(
        "browseSKEYheaders.php?direction=1&sortkey=br",
        href,
        1,
    )

    with pytest.raises(LexiconParseError):
        _public_parser()(_response(html))


def test_public_browse_parser_rejects_duplicate_next_page_links() -> None:
    html = _fixture("browse_br_unclosed_jump_2026_09_06.html").replace(
        "</body>",
        f"{_NEXT_ANCHOR}</body>",
        1,
    )

    with pytest.raises(LexiconParseError):
        _public_parser()(_response(html))


def test_public_browse_parser_keeps_explicit_no_match_distinct_from_drift() -> None:
    no_match = _public_parser()(
        _response(
            _fixture("not_found.html"),
            url="https://cal.huc.edu/browseSKEYheaders.php?first3=%22zzz%22",
        )
    )
    assert _entries(no_match) == ()
    assert _next(no_match) is None

    with pytest.raises(LexiconParseError):
        _public_parser()(_response("<html><body>replacement page</body></html>"))


class RecordingBrowseTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        params = dict(request.params)
        if "first3" in params:
            query = urlencode(request.params)
            return _response(
                _fixture("browse_br_unclosed_jump_2026_09_06.html"),
                url=f"https://cal.huc.edu/browseSKEYheaders.php?{query}",
            )
        if params == {"direction": "1", "sortkey": "br"}:
            html = _fixture("browse_br_unclosed_jump_2026_09_06.html").replace(
                _NEXT_ANCHOR,
                "",
                1,
            )
            return _response(
                html,
                url="https://cal.huc.edu/browseSKEYheaders.php?direction=1&sortkey=br",
            )
        raise AssertionError(f"unexpected CAL browse request: {request}")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("prefix", "representation", "expected"),
    [
        ("b", None, "b"),
        ("br", None, "br"),
        ("brt", None, "brt"),
        ("בר", InputRepresentation.HEBREW, "br"),
        ("ܒܪ", InputRepresentation.SYRIAC, "br"),
        ("bḥ", InputRepresentation.UNICODE_TRANSLITERATION, "bx"),
        ("w_", InputRepresentation.CAL_CODE, "w_"),
    ],
)
async def test_initial_browse_normalizes_locally_and_submits_one_first3_request(
    prefix: str,
    representation: InputRepresentation | None,
    expected: str,
) -> None:
    transport = RecordingBrowseTransport()
    result = await _service(CalHttpClient(transport=transport)).browse(
        prefix,
        representation=representation,
    )

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("first3", f'"{expected}"'),),
        )
    ]
    assert getattr(result, "normalized_prefix", None) == expected
    assert getattr(result, "next_continuation", None) == "br"
    assert len(transport.requests) == 1, "NEXT PAGE must never be prefetched"


@pytest.mark.anyio
async def test_continuation_is_one_explicit_fixed_endpoint_request() -> None:
    transport = RecordingBrowseTransport()
    result = await _service(CalHttpClient(transport=transport)).browse(
        "br",
        continuation="br",
    )

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("direction", "1"), ("sortkey", "br")),
        )
    ]
    assert getattr(result, "next_continuation", "sentinel") is None


@pytest.mark.anyio
async def test_ambiguous_prefix_conversion_fails_before_transport() -> None:
    transport = RecordingBrowseTransport()

    with pytest.raises(AmbiguousQueryError):
        await _service(CalHttpClient(transport=transport)).browse(
            "שב",
            representation=InputRepresentation.HEBREW,
        )

    assert transport.requests == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("prefix", "representation"),
    [
        ("", None),
        ("brnš", None),
        ("br mlk", None),
        ("br#", InputRepresentation.CAL_CODE),
        ("𐡁𐡓", InputRepresentation.IMPERIAL_ARAMAIC),
    ],
)
async def test_invalid_or_unsupported_browse_prefix_fails_before_transport(
    prefix: str,
    representation: InputRepresentation | None,
) -> None:
    transport = RecordingBrowseTransport()

    with pytest.raises((UnsupportedQueryError, ValueError)):
        await _service(CalHttpClient(transport=transport)).browse(
            prefix,
            representation=representation,
        )

    assert transport.requests == []


@pytest.mark.anyio
async def test_invalid_continuation_fails_before_transport() -> None:
    transport = RecordingBrowseTransport()

    with pytest.raises(ValueError):
        await _service(CalHttpClient(transport=transport)).browse(
            "br",
            continuation="br&direction=9",
        )

    assert transport.requests == []


@pytest.mark.anyio
async def test_public_browse_result_serializes_page_and_provenance() -> None:
    transport = RecordingBrowseTransport()
    result = await _service(CalHttpClient(transport=transport)).browse("br")
    payload = cast(_Serializable, result).to_dict()

    assert payload["prefix"] == "br"
    assert payload["normalized_prefix"] == "br"
    assert [item["lemma_key"] for item in cast(list[dict[str, object]], payload["entries"])] == [
        "br N",
        "br#2 N",
    ]
    assert payload["next_continuation"] == "br"
    provenance = cast(dict[str, object], payload["provenance"])
    assert provenance["source"] == "CAL"
    assert provenance["operation"] == "lexicon_browse"
    assert provenance["original_prefix"] == "br"
    assert provenance["normalized_prefix"] == "br"
    assert provenance["continuation"] is None


def test_release_surface_and_server_export_the_new_browse_tool() -> None:
    release_surface = importlib.import_module("cal_mcp.release_surface")
    server = importlib.import_module("cal_mcp.server")

    assert "cal_lexicon_browse" in release_surface.V01_PUBLIC_TOOLS
    assert callable(getattr(server, "cal_lexicon_browse", None))
