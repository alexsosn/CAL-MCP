from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import (
    LexiconEntry,
    LexiconLookupService,
    LexiconLookupStatus,
    parse_lexicon_entry,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
_RETRIEVED_AT = datetime(2026, 9, 11, tzinfo=UTC)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def _entry(html: str | None = None) -> LexiconEntry:
    return parse_lexicon_entry(
        _response(
            html or _fixture("entry_br_current_citations.html"),
            "https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
        ),
        lemma_key="br N",
    )


def _context_module() -> ModuleType:
    return importlib.import_module("cal_mcp.lexicon_citation_context")


def _parse_context(body: str, requested: str, *, url: str | None = None) -> object:
    parser = getattr(_context_module(), "parse_lexicon_citation_context_page", None)
    assert callable(parser)
    return parser(
        _response(
            body,
            url or f"https://cal.huc.edu/showachapter.php?fullcoord={requested}",
        ),
        requested_full_coordinate=requested,
    )


def _parse_error_type() -> type[Exception]:
    error_type = getattr(_context_module(), "LexiconCitationContextParseError", None)
    assert isinstance(error_type, type)
    assert issubclass(error_type, Exception)
    return error_type


def _status(page: object) -> str | None:
    value = getattr(page, "status", None)
    return getattr(value, "value", None)


def test_canonical_citation_exposes_typed_full_coordinate() -> None:
    citations = _entry().senses[0].citations

    assert [getattr(item, "full_coordinate", None) for item in citations] == [
        None,
        None,
        "7101301076140",
    ]
    assert citations[2].url == (
        "https://cal.huc.edu/showachapter.php?fullcoord=7101301076140"
    )


@pytest.mark.parametrize(
    "href",
    [
        "https://example.org/showachapter.php?fullcoord=7101301076140",
        "/nested/showachapter.php?fullcoord=7101301076140",
        "/showachapter.php?fullcoord=7101301076140&mode=all",
        "/showachapter.php?fullcoord=7101301076140#row",
        "/showachapter.php?fullcoord=ishdan-example",
    ],
)
def test_noncanonical_citation_link_is_not_a_typed_followup(href: str) -> None:
    html = _fixture("entry_br_current_citations.html").replace(
        "/showachapter.php?fullcoord=7101301076140",
        href,
        1,
    )
    citation = _entry(html).senses[0].citations[2]

    assert citation.url is not None
    assert getattr(citation, "full_coordinate", None) is None


class LexiconTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if request.path == "browseSKEYheaders.php":
            return _response(
                _fixture("browse_b.html"),
                "https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22",
            )
        if request.path == "cal_entry_web.php":
            return _response(
                _fixture("entry_br_current_citations.html"),
                "https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
            )
        raise AssertionError(f"unexpected hidden CAL request: {request}")


@pytest.mark.anyio
async def test_lookup_adds_selector_without_prefetching_context() -> None:
    transport = LexiconTransport()
    result = await LexiconLookupService(CalHttpClient(transport=transport)).lookup(
        "br",
        lemma_key="br N",
    )

    assert result.status is LexiconLookupStatus.FOUND
    assert result.entry is not None
    citation = result.entry.senses[0].citations[2]
    assert getattr(citation, "full_coordinate", None) == "7101301076140"
    assert [request.path for request in transport.requests] == [
        "browseSKEYheaders.php",
        "cal_entry_web.php",
    ]


def test_found_context_preserves_source_target_and_tokens() -> None:
    page = _parse_context(
        _fixture("lexicon_citation_context_ezra_4_24.html"),
        "31000424",
    )

    assert _status(page) == "found"
    assert getattr(page, "source_label", None) == "31000: BA Ezra chapter 4"
    assert getattr(page, "source_info_url", None) == (
        "https://cal.huc.edu/get_file_info.php?coord=310004"
    )
    lines = getattr(page, "lines", ())
    assert [line.coordinate for line in lines] == ["31000423", "31000424"]
    assert lines[1].display_coordinate == "4:24"
    assert [token.text for token in lines[1].tokens] == ["target-one", "target-two"]


def test_targum_context_keeps_full_coordinate_opaque() -> None:
    page = _parse_context(
        _fixture("lexicon_citation_context_tgj_ez_31_6.html"),
        "5101431061",
    )

    assert _status(page) == "found"
    assert getattr(page, "source_label", None) == "51014: TgJ Ez"
    assert [line.coordinate for line in getattr(page, "lines", ())] == [
        "5101431051",
        "5101431061",
    ]
    assert not hasattr(page, "file_id")
    assert not hasattr(page, "chapter")


def test_explicit_no_citations_marker_is_not_found() -> None:
    page = _parse_context(
        _fixture("lexicon_citation_context_not_found.html"),
        "999999999999",
    )

    assert _status(page) == "not_found"
    assert getattr(page, "lines", None) == ()
    assert getattr(page, "source_label", None) == "99999:"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/showachapter.php?fullcoord=31000424",
        "https://cal.huc.edu/nested/showachapter.php?fullcoord=31000424",
        "https://cal.huc.edu/showachapter.php?fullcoord=31000424&mode=all",
        "https://cal.huc.edu/showachapter.php?fullcoord=31000425",
        "https://cal.huc.edu/showachapter.php?fullcoord=31000424#row",
    ],
)
def test_context_response_identity_drift_fails(url: str) -> None:
    with pytest.raises(_parse_error_type()):
        _parse_context(
            _fixture("lexicon_citation_context_ezra_4_24.html"),
            "31000424",
            url=url,
        )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            "getlex.php?coord=31000424&word=0",
            "https://example.org/getlex.php?coord=31000424&word=0",
        ),
        ("getlex.php?coord=31000424&word=1", "getlex.php?coord=31000499&word=1"),
        ("getlex.php?coord=31000424&word=1", "getlex.php?coord=31000424&word=0"),
        ("comment.php?coord=31000424", "comment.php?coord=31000499"),
        (">target-one</a>", "></a>"),
    ],
)
def test_context_semantic_link_drift_fails(old: str, new: str) -> None:
    html = _fixture("lexicon_citation_context_ezra_4_24.html").replace(old, new, 1)
    with pytest.raises(_parse_error_type()):
        _parse_context(html, "31000424")


def test_target_line_must_be_unique() -> None:
    html = _fixture("lexicon_citation_context_ezra_4_24.html")
    with pytest.raises(_parse_error_type()):
        _parse_context(html.replace("31000424", "31000425"), "31000424")
    with pytest.raises(_parse_error_type()):
        _parse_context(html.replace("31000423", "31000424"), "31000424")


def test_missing_marker_must_match_request_and_not_mix_with_rows() -> None:
    missing = _fixture("lexicon_citation_context_not_found.html")
    with pytest.raises(_parse_error_type()):
        _parse_context(
            missing.replace("99999 9999999", "99999 9999998"),
            "999999999999",
        )

    found = _fixture("lexicon_citation_context_ezra_4_24.html")
    found += "<div>NO CITATIONS FOR 31000 424 ARE CURRENTLY STORED</div>"
    with pytest.raises(_parse_error_type()):
        _parse_context(found, "31000424")


class ContextTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_context_service_submits_one_exact_request() -> None:
    service_type = getattr(_context_module(), "LexiconCitationContextService", None)
    assert isinstance(service_type, type)
    transport = ContextTransport(
        _response(
            _fixture("lexicon_citation_context_ezra_4_24.html"),
            "https://cal.huc.edu/showachapter.php?fullcoord=31000424",
        )
    )
    result = await service_type(CalHttpClient(transport=transport)).context("31000424")

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="showachapter.php",
            params=(("fullcoord", "31000424"),),
        )
    ]
    payload = result.to_dict()
    assert payload["status"] == "found"
    assert payload["full_coordinate"] == "31000424"


@pytest.mark.anyio
@pytest.mark.parametrize("value", ["", "0", " 31000424", "31a00424", "٣١٠٠٠٤٢٤"])
async def test_context_service_rejects_invalid_selector_before_io(value: str) -> None:
    service_type = getattr(_context_module(), "LexiconCitationContextService", None)
    assert isinstance(service_type, type)

    async def unexpected(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del request, config
        raise AssertionError("invalid selector reached network I/O")

    service = service_type(CalHttpClient(transport=unexpected))
    with pytest.raises(ValueError):
        await service.context(value)


@pytest.mark.anyio
async def test_mcp_registers_url_free_context_tool() -> None:
    server_module = importlib.import_module("cal_mcp.server")
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    schema = tools["cal_lexicon_citation_context"].input_schema
    assert set(schema["properties"]) == {"full_coordinate"}
    assert schema["required"] == ["full_coordinate"]


def test_release_surface_includes_context_tool() -> None:
    release_surface = importlib.import_module("cal_mcp.release_surface")
    assert "cal_lexicon_citation_context" in release_surface.V01_PUBLIC_TOOLS
    assert len(release_surface.V01_PUBLIC_TOOLS) == 33
