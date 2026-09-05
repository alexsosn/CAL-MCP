from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.bibliography import (
    BibliographyParseError,
    BibliographyQueryKind,
    BibliographyService,
    parse_author_options_page,
    parse_bibliography_page,
)
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 5, 10, 5, tzinfo=UTC)


def _fixture_response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _inline_response(body: str, url: str = "https://cal.huc.edu/getbibsigla.php") -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def test_author_prefix_parser_preserves_ordered_exact_candidates() -> None:
    page = parse_author_options_page(
        _fixture_response(
            "bibliography_authors_kau.html",
            "https://cal.huc.edu/browsenames.php",
        )
    )

    assert [(item.value, item.label) for item in page.candidates] == [
        ("Kaufhold, H.", "Kaufhold, H."),
        ("Kaufman, Stephen A.", "Kaufman, Stephen A."),
        ("Kaukhchishvili, S.", "Kaukhchishvili, S."),
        ("Kautzsch, E.", "Kautzsch, E."),
    ]


def test_author_prefix_parser_preserves_explicit_empty_state() -> None:
    page = parse_author_options_page(
        _fixture_response(
            "bibliography_authors_empty.html",
            "https://cal.huc.edu/browsenames.php",
        )
    )

    assert page.candidates == ()


def test_author_bibliography_preserves_order_unicode_and_link_semantics() -> None:
    page = parse_bibliography_page(
        _fixture_response(
            "bibliography_author_kaufman.html",
            "https://cal.huc.edu/getbibauthor.php?myauthor=Kaufman%2C+Stephen+A.",
        )
    )

    assert page.heading == "CAL Bibliography for Kaufman, Stephen A."
    assert len(page.records) == 2
    assert page.records[0].citation.startswith("Kaufman, Stephen A.,")
    assert "אכדית וארמית בבלית" in page.records[1].citation

    first_link = page.records[0].links[0]
    assert first_link.label == "Nerab"
    assert first_link.url == "https://cal.huc.edu/getbibsigla.php?myauthor=Nerab"
    assert first_link.query_kind is BibliographyQueryKind.KEYWORD
    assert first_link.query_value == "Nerab"

    lemma_link = page.records[1].links[-1]
    assert lemma_link.label == ")wwr N"
    assert lemma_link.query_kind is BibliographyQueryKind.LEMMA
    assert lemma_link.query_value == ")wwr N"


def test_keyword_bibliography_preserves_ordered_records_and_exact_tags() -> None:
    page = parse_bibliography_page(
        _fixture_response(
            "bibliography_keyword_tada.html",
            "https://cal.huc.edu/getbibsigla.php?myauthor=TADA",
        )
    )

    assert len(page.records) == 2
    assert "Textbook of Aramaic Documents" in page.records[0].citation
    assert "מכתבים ארמיים" in page.records[1].citation
    assert [link.query_value for link in page.records[0].links] == ["Collections", "TADA"]
    assert all(
        link.query_kind is BibliographyQueryKind.KEYWORD for link in page.records[0].links
    )


def test_lemma_bibliography_preserves_linked_lemma_keys() -> None:
    page = parse_bibliography_page(
        _fixture_response(
            "bibliography_lemma_cly_v.html",
            "https://cal.huc.edu/getbiblemma.php?myauthor=cly+V",
        )
    )

    assert len(page.records) == 1
    assert [link.query_value for link in page.records[0].links] == ["sxr V", "yqr V", "cly V"]
    assert all(link.query_kind is BibliographyQueryKind.LEMMA for link in page.records[0].links)


def test_final_bibliography_explicit_no_data_marker_is_empty() -> None:
    page = parse_bibliography_page(
        _fixture_response(
            "bibliography_empty.html",
            "https://cal.huc.edu/getbibsigla.php?myauthor=CALMCP_NONEXISTENT_20260905",
        )
    )

    assert page.records == ()
    assert page.heading == "CAL Bibliography for CALMCP_NONEXISTENT_20260905"


@pytest.mark.parametrize(
    "body",
    [
        "<html><body><h1>CAL Bibliography for TADA</h1><p>changed markup</p></body></html>",
        (
            "<html><body><h1>CAL Bibliography for TADA</h1>"
            '<div class="card"><a href="/getbibsigla.php?myauthor=TADA">TADA</a></div>'
            "</body></html>"
        ),
        (
            "<html><body><h1>CAL Bibliography for TADA</h1>"
            '<div class="card">citation <a href="https://example.org/x">outside</a></div>'
            "</body></html>"
        ),
        (
            "<html><body><h1>CAL Bibliography for TADA</h1>"
            '<div class="card">citation '
            '<a href="/getbibsigla.php?myauthor=TADA&amp;myauthor=AECT">bad</a></div>'
            "</body></html>"
        ),
        (
            "<html><body><h1>CAL Bibliography for TADA</h1>"
            "<p>NO data FOR TADA ARE CURRENTLY STORED</p>"
            '<div class="card">citation</div></body></html>'
        ),
    ],
)
def test_malformed_or_contradictory_result_markup_is_parser_drift(body: str) -> None:
    with pytest.raises(BibliographyParseError):
        parse_bibliography_page(_inline_response(body))


def test_author_selector_without_valid_selector_or_empty_marker_is_parser_drift() -> None:
    response = _inline_response(
        "<html><body><h1>CAL Bibliography — Author Select</h1><p>changed</p></body></html>",
        "https://cal.huc.edu/browsenames.php",
    )

    with pytest.raises(BibliographyParseError):
        parse_author_options_page(response)


class RecordingTransport:
    def __init__(self, responses: dict[str, CalResponse]) -> None:
        self.responses = responses
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.responses[request.path]


def _service() -> tuple[BibliographyService, RecordingTransport]:
    transport = RecordingTransport(
        {
            "browsenames.php": _fixture_response(
                "bibliography_authors_kau.html",
                "https://cal.huc.edu/browsenames.php",
            ),
            "getbibauthor.php": _fixture_response(
                "bibliography_author_kaufman.html",
                "https://cal.huc.edu/getbibauthor.php?myauthor=Kaufman%2C+Stephen+A.",
            ),
            "getbibsigla.php": _fixture_response(
                "bibliography_keyword_tada.html",
                "https://cal.huc.edu/getbibsigla.php?myauthor=TADA",
            ),
            "getbiblemma.php": _fixture_response(
                "bibliography_lemma_cly_v.html",
                "https://cal.huc.edu/getbiblemma.php?myauthor=cly+V",
            ),
        }
    )
    return BibliographyService(CalHttpClient(transport=transport)), transport


@pytest.mark.anyio
async def test_services_map_each_public_operation_to_exactly_one_cal_request() -> None:
    service, transport = _service()

    authors = await service.authors(" Kau ")
    author = await service.author(" Kaufman, Stephen A. ")
    keyword = await service.keyword(" TADA ")
    lemma = await service.lemma(" cly V ")

    assert authors.candidates[1].value == "Kaufman, Stephen A."
    assert author.records[1].citation.startswith("Kaufman, Stephen A.,")
    assert keyword.query_kind is BibliographyQueryKind.KEYWORD
    assert lemma.query_kind is BibliographyQueryKind.LEMMA

    assert transport.requests == [
        CalRequest(
            method="POST",
            path="browsenames.php",
            data=(("first3", "Kau"),),
        ),
        CalRequest(
            method="GET",
            path="getbibauthor.php",
            params=(("myauthor", "Kaufman, Stephen A."),),
        ),
        CalRequest(
            method="GET",
            path="getbibsigla.php",
            params=(("myauthor", "TADA"),),
        ),
        CalRequest(
            method="GET",
            path="getbiblemma.php",
            params=(("myauthor", "cly V"),),
        ),
    ]

    assert authors.provenance.original_query == " Kau "
    assert authors.provenance.submitted_query == "Kau"
    assert authors.provenance.operation == "bibliography_authors"
    assert authors.provenance.source == "CAL"
    assert authors.provenance.retrieved_at == RETRIEVED_AT
    assert author.provenance.operation == "bibliography_author"
    assert keyword.provenance.operation == "bibliography_keyword"
    assert lemma.provenance.operation == "bibliography_lemma"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "value"),
    [
        ("authors", ""),
        ("authors", "       "),
        ("authors", "abcdefg"),
        ("authors", "Ka\nu"),
        ("authors", "Ka\tu"),
        ("author", ""),
        ("author", "A\nB"),
        ("author", "x" * 161),
        ("keyword", ""),
        ("keyword", "A\tB"),
        ("keyword", "x" * 129),
        ("lemma", ""),
        ("lemma", "cly"),
        ("lemma", "cly !"),
        ("lemma", "x" * 129),
    ],
)
async def test_invalid_bibliography_values_fail_before_transport(
    operation: str,
    value: str,
) -> None:
    service, transport = _service()
    method = getattr(service, operation)

    with pytest.raises(ValueError):
        await method(value)

    assert transport.requests == []
