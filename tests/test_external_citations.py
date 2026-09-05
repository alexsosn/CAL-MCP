from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.external_citations import (
    ExternalCitationParseError,
    ExternalCitationService,
    parse_external_citation_dialects_page,
    parse_external_citation_sources_page,
    parse_external_citations_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 5, 18, 0, tzinfo=UTC)


def _fixture_response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _inline_response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def test_dialect_discovery_preserves_cal_order_ids_and_labels() -> None:
    page = parse_external_citation_dialects_page(
        _fixture_response(
            "external_citation_dialects.html",
            "https://cal.huc.edu/citfinder.html",
        )
    )

    assert [(item.dialect_id, item.label) for item in page.dialects] == [
        ("1", "Old Aramaic"),
        ("2", "Imperial/Official Aramaic"),
        ("6", "Syriac"),
    ]


def test_source_discovery_preserves_order_description_and_exact_navigation() -> None:
    page = parse_external_citation_sources_page(
        _fixture_response(
            "external_citation_sources_syriac.html",
            "https://cal.huc.edu/display.notext.abbrevs.php?dial=6&dial1=6",
        )
    )

    assert [item.abbreviation for item in page.sources] == ["1CorH", "1KgdHex"]
    assert page.sources[0].description is not None
    assert "Harklean version" in page.sources[0].description
    assert page.sources[0].citations_url == (
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH"
    )
    assert page.sources[1].description is None


def test_source_discovery_explicit_empty_marker_is_empty() -> None:
    page = parse_external_citation_sources_page(
        _fixture_response(
            "external_citation_sources_empty.html",
            "https://cal.huc.edu/display.notext.abbrevs.php?dial=999&dial1=6",
        )
    )

    assert page.sources == ()


def test_external_citations_preserve_order_unicode_and_nullable_fields() -> None:
    page = parse_external_citations_page(
        _fixture_response(
            "external_citations_1corh.html",
            "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH",
        )
    )

    assert page.source_abbrev == "1CorH"
    assert page.total == 3
    assert len(page.citations) == 3

    first = page.citations[0]
    assert first.lemma_key == "qwbrny+w N"
    assert first.lemma_label == "qwbrnyṭw, qwbrnyṭwtˀ"
    assert first.part_of_speech == "n.f."
    assert first.reference == "1CorH 12:28"
    assert first.gloss == "“steering, piloting”"
    assert first.source_text is None
    assert first.translation is None
    assert first.entry_url == "https://cal.huc.edu/oneentry.php?lemma=qwbrny%2Bw+N&cits=all"

    second = page.citations[1]
    assert second.lemma_key == "mtqytr N"
    assert second.part_of_speech is None
    assert second.gloss is None
    assert second.source_text == "ܡܐ ܕܡܙܕܡܪ ܐܘ ܕܡܬܩܝܬܪ"
    assert second.translation == "what is sung(!) or strung"

    third = page.citations[2]
    assert third.lemma_key == "(byr A"
    assert third.reference == "1CorH 7:36"
    assert third.part_of_speech is None
    assert third.gloss is None
    assert third.source_text is None
    assert third.translation is None


def test_external_citations_explicit_empty_marker_is_empty() -> None:
    page = parse_external_citations_page(
        _fixture_response(
            "external_citations_empty.html",
            "https://cal.huc.edu/displaycits.abbrev.php?abbrev=Qqqqqq",
        )
    )

    assert page.source_abbrev == "Qqqqqq"
    assert page.total == 0
    assert page.citations == ()


@pytest.mark.parametrize(
    "body",
    [
        '<html><body><div class="section-title">Choose a Dialect</div></body></html>',
        (
            '<html><body><div class="section-title">Choose a Dialect</div><div class="card">'
            '<a href="https://example.org/display.notext.abbrevs.php?dial=6">Syriac</a>'
            "</div></body></html>"
        ),
        (
            '<html><body><div class="section-title">Choose a Dialect</div><div class="card">'
            '<a href="/wrong.php?dial=6">Syriac</a></div></body></html>'
        ),
        (
            '<html><body><div class="section-title">Choose a Dialect</div><div class="card">'
            '<a href="/display.notext.abbrevs.php?dial=6">Syriac</a>'
            '<a href="/display.notext.abbrevs.php?dial=6">Again</a>'
            "</div></body></html>"
        ),
    ],
)
def test_malformed_dialect_discovery_is_parser_drift(body: str) -> None:
    with pytest.raises(ExternalCitationParseError):
        parse_external_citation_dialects_page(
            _inline_response(body, "https://cal.huc.edu/citfinder.html")
        )


@pytest.mark.parametrize(
    "body",
    [
        "<html><body><h1>Texts With Citations, No Full Text Yet</h1><p>changed</p></body></html>",
        (
            "<html><body><h1>Texts With Citations, No Full Text Yet</h1>"
            '<div class="cit-row"><a class="cit-abbrev" '
            'href="https://example.org/displaycits.abbrev.php?abbrev=1CorH">1CorH</a></div>'
            "</body></html>"
        ),
        (
            "<html><body><h1>Texts With Citations, No Full Text Yet</h1>"
            '<div class="cit-row"><a class="cit-abbrev" '
            'href="/displaycits.abbrev.php?abbrev=1CorH&amp;abbrev=ON">1CorH</a></div>'
            "</body></html>"
        ),
        (
            "<html><body><h1>Texts With Citations, No Full Text Yet</h1>"
            "<p>No extra citations for that dialect are currently found.</p>"
            '<div class="cit-row"><a class="cit-abbrev" '
            'href="/displaycits.abbrev.php?abbrev=1CorH">1CorH</a></div>'
            "</body></html>"
        ),
    ],
)
def test_malformed_or_contradictory_source_list_is_parser_drift(body: str) -> None:
    with pytest.raises(ExternalCitationParseError):
        parse_external_citation_sources_page(
            _inline_response(
                body,
                "https://cal.huc.edu/display.notext.abbrevs.php?dial=6&dial1=6",
            )
        )


@pytest.mark.parametrize(
    "body",
    [
        "<html><body><h1>Citations for 1CorH</h1><p>changed</p></body></html>",
        (
            "<html><body><h1>Citations for 1CorH</h1>"
            '<span class="result-count">2 citations</span>'
            '<div class="cit-entry"><a class="cit-lemma" '
            'href="/oneentry.php?lemma=mtqytr+N&amp;cits=all">mtqytr</a>'
            '<span class="cit-coord">1CorH 14:7</span></div></body></html>'
        ),
        (
            "<html><body><h1>Citations for 1CorH</h1>"
            '<span class="result-count">1 citation</span>'
            '<div class="cit-entry"><a class="cit-lemma" '
            'href="https://example.org/oneentry.php?lemma=mtqytr+N&amp;cits=all">mtqytr</a>'
            '<span class="cit-coord">1CorH 14:7</span></div></body></html>'
        ),
        (
            "<html><body><h1>Citations for 1CorH</h1>"
            '<span class="result-count">1 citation</span>'
            '<div class="cit-entry"><a class="cit-lemma" '
            'href="/oneentry.php?lemma=mtqytr+N&amp;lemma=other+N&amp;cits=all">mtqytr</a>'
            '<span class="cit-coord">1CorH 14:7</span></div></body></html>'
        ),
        (
            "<html><body><h1>Citations for 1CorH</h1>"
            '<span class="result-count">1 citation</span>'
            '<div class="cit-entry"><a class="cit-lemma" '
            'href="/oneentry.php?lemma=bad&amp;cits=all">bad</a>'
            '<span class="cit-coord">1CorH 14:7</span></div></body></html>'
        ),
        (
            "<html><body><h1>Citations for 1CorH</h1>"
            '<p>No citations for "1CorH" are currently stored.</p>'
            '<span class="result-count">1 citation</span>'
            '<div class="cit-entry"><a class="cit-lemma" '
            'href="/oneentry.php?lemma=mtqytr+N&amp;cits=all">mtqytr</a>'
            '<span class="cit-coord">1CorH 14:7</span></div></body></html>'
        ),
    ],
)
def test_malformed_or_contradictory_citation_page_is_parser_drift(body: str) -> None:
    with pytest.raises(ExternalCitationParseError):
        parse_external_citations_page(
            _inline_response(
                body,
                "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH",
            )
        )


def test_style_and_script_do_not_create_false_external_citation_semantics() -> None:
    response = _inline_response(
        "<html><body><style>.x{content:'No citations for "
        "&quot;1CorH&quot; are currently stored.'}</style>"
        "<script>const x = 'cit-entry';</script><h1>Citations for 1CorH</h1><p>changed</p>"
        "</body></html>",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH",
    )

    with pytest.raises(ExternalCitationParseError):
        parse_external_citations_page(response)


def test_unclosed_ignored_subtree_is_parser_drift() -> None:
    response = _inline_response(
        "<html><body><h1>Citations for 1CorH</h1><script>changed",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH",
    )

    with pytest.raises(ExternalCitationParseError):
        parse_external_citations_page(response)


class RecordingTransport:
    def __init__(self, responses: dict[str, CalResponse]) -> None:
        self.responses = responses
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.responses[request.path]


def _service() -> tuple[ExternalCitationService, RecordingTransport]:
    transport = RecordingTransport(
        {
            "citfinder.html": _fixture_response(
                "external_citation_dialects.html",
                "https://cal.huc.edu/citfinder.html",
            ),
            "display.notext.abbrevs.php": _fixture_response(
                "external_citation_sources_syriac.html",
                "https://cal.huc.edu/display.notext.abbrevs.php?dial=6&dial1=6",
            ),
            "displaycits.abbrev.php": _fixture_response(
                "external_citations_1corh.html",
                "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH",
            ),
        }
    )
    return ExternalCitationService(CalHttpClient(transport=transport)), transport


@pytest.mark.anyio
async def test_services_map_each_public_operation_to_exactly_one_cal_request() -> None:
    service, transport = _service()

    dialects = await service.dialects()
    sources = await service.sources(" 6 ")
    citations = await service.citations(" 1CorH ")

    assert dialects.dialects[-1].label == "Syriac"
    assert sources.sources[0].abbreviation == "1CorH"
    assert citations.citations[1].reference == "1CorH 14:7"

    assert transport.requests == [
        CalRequest(method="GET", path="citfinder.html"),
        CalRequest(
            method="GET",
            path="display.notext.abbrevs.php",
            params=(("dial1", "6"), ("dial", "6")),
        ),
        CalRequest(
            method="GET",
            path="displaycits.abbrev.php",
            params=(("abbrev", "1CorH"),),
        ),
    ]

    assert dialects.provenance.operation == "external_citation_dialects"
    assert dialects.provenance.source == "CAL"
    assert dialects.provenance.retrieved_at == RETRIEVED_AT
    assert sources.provenance.operation == "external_citation_sources"
    assert sources.provenance.dialect_id == "6"
    assert citations.provenance.operation == "external_citations"
    assert citations.provenance.source_abbrev == "1CorH"


@pytest.mark.anyio
async def test_wrong_source_result_heading_is_parser_drift_not_silent_success() -> None:
    transport = RecordingTransport(
        {
            "displaycits.abbrev.php": _fixture_response(
                "external_citations_1corh.html",
                "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH",
            )
        }
    )
    service = ExternalCitationService(CalHttpClient(transport=transport))

    with pytest.raises(ExternalCitationParseError):
        await service.citations("ON")

    assert len(transport.requests) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "value"),
    [
        ("sources", ""),
        ("sources", "abcdef"),
        ("sources", "1234567"),
        ("sources", "١"),
        ("sources", "6\n"),
        ("citations", ""),
        ("citations", "   "),
        ("citations", "A\tB"),
        ("citations", "A\nB"),
        ("citations", "x" * 129),
    ],
)
async def test_invalid_external_citation_values_fail_before_transport(
    operation: str,
    value: str,
) -> None:
    service, transport = _service()
    method = getattr(service, operation)

    with pytest.raises(ValueError):
        await method(value)

    assert transport.requests == []
