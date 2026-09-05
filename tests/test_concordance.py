from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    ConcordanceService,
    KwicScopeKind,
    parse_kwic_dialect_options,
    parse_kwic_result,
    parse_text_concordance_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _fixture_response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )


def test_text_concordance_preserves_frequency_lemma_gloss_and_kwic_link() -> None:
    page = parse_text_concordance_page(
        _fixture_response(
            "concordance_text_13250.html",
            "https://cal.huc.edu/newconcord.php?text=13250&cset=S",
        ),
        requested_text_id="13250",
        requested_charset="S",
    )

    assert [(item.frequency, item.lemma_key, item.gloss) for item in page.lemmas] == [
        (4, ")b N", "father"),
        (2, "br N", "son"),
        (6, "mlk N", "king"),
    ]
    assert page.lemmas[-1].kwic_url == (
        "https://cal.huc.edu/showKWIC.php?lemma=mlk+N&charset=S&texts=13250"
    )


def test_multi_text_kwic_preserves_order_duplicates_context_and_empty_scope() -> None:
    page = parse_kwic_result(
        _fixture_response(
            "kwic_texts_mlk.html",
            "https://cal.huc.edu/showdialectKWIC.php",
        ),
        lemma_key="mlk N",
        scope_kind=KwicScopeKind.TEXTS,
        scope_ids=("12250", "13250"),
    )

    assert page.total == 3
    assert page.empty_scope_ids == ("12250",)
    assert [hit.target_coordinate for hit in page.hits] == [
        "1325003",
        "1325006",
        "1325006",
    ]
    assert [hit.file_id for hit in page.hits] == ["13250", "13250", "13250"]
    assert page.hits[0].subtext_id is None
    assert page.hits[0].charset == "R"
    assert "wy$kb" in page.hits[0].context
    assert page.hits[1].context != page.hits[2].context
    assert page.hits[0].full_context_url.startswith(
        "https://cal.huc.edu/get_a_kwicchapter.php?"
    )


def test_explicit_zero_total_kwic_is_empty_not_parser_drift() -> None:
    page = parse_kwic_result(
        _fixture_response(
            "kwic_texts_empty.html",
            "https://cal.huc.edu/showdialectKWIC.php",
        ),
        lemma_key="qzxk N",
        scope_kind=KwicScopeKind.TEXTS,
        scope_ids=("13250",),
    )

    assert page.total == 0
    assert page.hits == ()
    assert page.empty_scope_ids == ("13250",)


def test_dialect_selector_preserves_current_cal_ids_and_labels() -> None:
    page = parse_kwic_dialect_options(
        _fixture_response(
            "kwic_dialects_aryk2_a.html",
            "https://cal.huc.edu/dKWIC.php?lemma=%29ryk%232+A",
        ),
        lemma_key=")ryk#2 A",
    )

    assert [(item.dialect_id, item.label) for item in page.dialects] == [
        ("1", "Old Aramaic"),
        ("2", "Imperial/Official Aramaic"),
        ("3", "Biblical Aramaic"),
        ("6", "Syriac"),
        ("71", "Babylonian Talmudic"),
        ("74", "Mandaic"),
    ]


def test_one_dialect_kwic_preserves_subtext_charset_context_and_target() -> None:
    page = parse_kwic_result(
        _fixture_response(
            "kwic_dialect_aryk2_a_biblical.html",
            "https://cal.huc.edu/show1dialectKWIC.php?lemma=%29ryk%232&pos=A&texts=3",
        ),
        lemma_key=")ryk#2 A",
        scope_kind=KwicScopeKind.DIALECT,
        scope_ids=("3",),
    )

    assert page.total == 1
    assert page.empty_scope_ids == ()
    assert len(page.hits) == 1
    hit = page.hits[0]
    assert hit.file_id == "31000"
    assert hit.subtext_id == "4"
    assert hit.target_coordinate == "31000414"
    assert hit.charset == "H"
    assert "אֲרִיךְ" in hit.context


def test_positive_total_must_equal_number_of_parsed_target_links() -> None:
    body = (FIXTURES / "kwic_texts_mlk.html").read_text().replace(
        "total examples: 3", "total examples: 4"
    )
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/showdialectKWIC.php",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )

    with pytest.raises(ConcordanceParseError):
        parse_kwic_result(
            response,
            lemma_key="mlk N",
            scope_kind=KwicScopeKind.TEXTS,
            scope_ids=("12250", "13250"),
        )


@pytest.mark.parametrize(
    "body",
    [
        """<html><body>
<div>Looking for mlk N in dialect 13250</div>
<div>13250:</div>
<table><tr><td>left</td><td><a href="/get_a_kwicchapter.php?file=oops&amp;sub=&amp;cset=R&amp;target=1325003">1325003</a></td><td>right</td></tr></table>
<div>total examples: 1</div>
</body></html>""",
        """<html><body>
<div>Looking for mlk N in dialect 13250</div>
<div>13250:</div>
<table><tr><td></td><td><a href="/get_a_kwicchapter.php?file=13250&amp;sub=&amp;cset=R&amp;target=1325003">1325003</a></td><td></td></tr></table>
<div>total examples: 1</div>
</body></html>""",
        """<html><body>
<div>Looking for mlk N in dialect 13250</div>
<div>13250:</div>
<table><tr><td>left</td><td><a href="/get_a_kwicchapter.php?file=13250&amp;sub=&amp;cset=R&amp;target=1325003">1325999</a></td><td>right</td></tr></table>
<div>total examples: 1</div>
</body></html>""",
    ],
)
def test_malformed_or_contextless_target_row_is_parser_drift(body: str) -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/showdialectKWIC.php",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )

    with pytest.raises(ConcordanceParseError):
        parse_kwic_result(
            response,
            lemma_key="mlk N",
            scope_kind=KwicScopeKind.TEXTS,
            scope_ids=("13250",),
        )


class RecordingTransport:
    def __init__(self, responses: dict[str, CalResponse]) -> None:
        self.responses = responses
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.responses[request.path]


def _service() -> tuple[ConcordanceService, RecordingTransport]:
    transport = RecordingTransport(
        {
            "newconcord.php": _fixture_response(
                "concordance_text_13250.html",
                "https://cal.huc.edu/newconcord.php?text=13250&cset=S",
            ),
            "showdialectKWIC.php": _fixture_response(
                "kwic_texts_mlk.html",
                "https://cal.huc.edu/showdialectKWIC.php",
            ),
            "dKWIC.php": _fixture_response(
                "kwic_dialects_aryk2_a.html",
                "https://cal.huc.edu/dKWIC.php?lemma=%29ryk%232+A",
            ),
            "show1dialectKWIC.php": _fixture_response(
                "kwic_dialect_aryk2_a_biblical.html",
                "https://cal.huc.edu/show1dialectKWIC.php?lemma=%29ryk%232&pos=A&texts=3",
            ),
        }
    )
    return ConcordanceService(CalHttpClient(transport=transport)), transport


@pytest.mark.anyio
async def test_services_map_each_public_operation_to_exactly_one_cal_request() -> None:
    service, transport = _service()

    concordance = await service.text_concordance("13250", script="semitic")
    text_kwic = await service.kwic_texts(
        "mlk N", ["12250", "13250"], script="roman"
    )
    dialects = await service.kwic_dialects(")ryk#2 A")
    dialect_kwic = await service.kwic_dialect(")ryk#2 A", "3")

    assert concordance.text_id == "13250"
    assert concordance.provenance.script == "semitic"
    assert text_kwic.total == 3
    assert text_kwic.provenance.scope_ids == ("12250", "13250")
    assert dialects.dialects[2].dialect_id == "3"
    assert dialect_kwic.hits[0].target_coordinate == "31000414"

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="newconcord.php",
            params=(("text", "13250"), ("cset", "S")),
        ),
        CalRequest(
            method="POST",
            path="showdialectKWIC.php",
            data=(
                ("lemma", "mlk"),
                ("pos", "N"),
                ("texts", "12250 13250"),
                ("charset", "R"),
            ),
        ),
        CalRequest(
            method="GET",
            path="dKWIC.php",
            params=(("lemma", ")ryk#2 A"),),
        ),
        CalRequest(
            method="GET",
            path="show1dialectKWIC.php",
            params=(("lemma", ")ryk#2"), ("pos", "A"), ("texts", "3")),
        ),
    ]

    assert all("lth" not in dict(request.params + request.data) for request in transport.requests)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "args", "kwargs"),
    [
        ("text_concordance", ("abc",), {}),
        ("text_concordance", ("13250",), {"script": "roman"}),
        ("kwic_texts", ("mlk", ["13250"]), {}),
        ("kwic_texts", ("mlk !", ["13250"]), {}),
        ("kwic_texts", ("mlk N", []), {}),
        ("kwic_texts", ("mlk N", ["13250", "13250"]), {}),
        ("kwic_texts", ("mlk N", [str(index) for index in range(9)]), {}),
        ("kwic_texts", ("mlk N", ["x"]), {}),
        ("kwic_texts", ("mlk N", ["13250"]), {"script": "semitic"}),
        ("kwic_dialects", ("mlk",), {}),
        ("kwic_dialect", ("mlk N", "x"), {}),
    ],
)
async def test_invalid_concordance_requests_fail_before_transport(
    operation: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> None:
    service, transport = _service()
    method = getattr(service, operation)

    with pytest.raises(ValueError):
        await method(*args, **kwargs)

    assert transport.requests == []


def test_result_serialization_preserves_provenance_and_duplicate_hits() -> None:
    page = parse_kwic_result(
        _fixture_response(
            "kwic_texts_mlk.html",
            "https://cal.huc.edu/showdialectKWIC.php",
        ),
        lemma_key="mlk N",
        scope_kind=KwicScopeKind.TEXTS,
        scope_ids=("12250", "13250"),
    )
    service, _ = _service()

    assert page.hits[1].target_coordinate == page.hits[2].target_coordinate
    assert service is not None
