"""Issue #246: exact, typed followup of one CAL Targum concordance text-ID group."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalInputError
from cal_mcp.targum import parse_targum_concordance_page

SOURCE = "https://cal.huc.edu/show1dialectKWIC.php?lemma=klb&pos=N&texts=51001+51002&charset=H"
STAMP = datetime(2026, 10, 10, 17, 30, tzinfo=UTC)

# Synthetic scholar text, structural markup derived from bounded CAL observation
# 38059641146. This intentionally is NOT a full copied CAL HTML page.
BODY = (
    "<html><body><form>"
    "<div>Looking for <b>klb N</b> in 51001 51002</div>"
    '<div><span class="heb"><div><br><b>Click on the target line coordinate '
    "to see the text in a full context</b><br><p>"
    '<span class="mono">510011100</span> Before first<br>'
    '<a href="/get_a_kwicchapter.php?file=51001&amp;sub=&amp;target=510011101&amp;cset=H">'
    '<span class="mono">510011101</span></a> Synthetic first '
    '<b><span class="red">target one</span></b> context<br>'
    '<span class="mono">510011102</span> After first<br>'
    "</p></div></span></div>"
    '<div><span class="heb"><div><br><b>Click on the target line coordinate '
    "to see the text in a full context</b><br><p>"
    '<span class="mono">510021100</span> Before second<br>'
    '<a href="/get_a_kwicchapter.php?file=51002&amp;sub=&amp;target=510021101&amp;cset=H">'
    '<span class="mono">510021101</span></a> Synthetic second '
    '<b><span class="red">target two</span></b> context<br>'
    '<span class="mono">510021102</span> After second<br>'
    "</p></div></span></div>"
    "<div><b>2</b> examples found for <b>klb N</b> in dialect 51001 51002</div>"
    "</form></body></html>"
)


def response(body: str = BODY, source: str = SOURCE) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=source,
        body=body.encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=STAMP,
    )


def parse(body: str = BODY, source: str = SOURCE):
    mod = import_module("cal_mcp.targum_concordance_examples")
    return mod.parse_targum_concordance_examples_page(
        response(body, source), lemma_key="klb N", text_ids=("51001", "51002")
    )


def test_quoted_cal_text_group_has_two_ordered_hits_and_targets() -> None:
    page = parse()
    assert page.total == 2
    assert [item.file_id for item in page.hits] == ["51001", "51002"]
    assert [item.target_coordinate for item in page.hits] == ["510011101", "510021101"]
    assert [item.target_text for item in page.hits] == ["target one", "target two"]
    assert all(item.charset == "H" for item in page.hits)


@pytest.mark.parametrize(
    "bad_source",
    [
        SOURCE.replace("cal.huc.edu", "malicious.example"),
        SOURCE.replace("charset=H", "charset=R"),
        SOURCE.replace("texts=51001+51002", "texts=51002+51001"),
        SOURCE + "&texts=51001",
        SOURCE + "#fragment",
        SOURCE.replace("show1dialectKWIC.php", "showdialectKWIC.php"),
    ],
)
def test_bad_result_origin_and_group_are_parser_drift(bad_source: str) -> None:
    mod = import_module("cal_mcp.targum_concordance_examples")
    with pytest.raises(mod.TargumConcordanceExamplesParseError):
        parse(source=bad_source)


@pytest.mark.parametrize(
    "bad_html",
    [
        BODY.replace("Looking for <b>klb N</b>", "Looking for <b>ktb V</b>"),
        BODY.replace("2</b> examples found", "3</b> examples found"),
        BODY.replace("in dialect 51001 51002", "in dialect 51001 51003"),
        BODY.replace("get_a_kwicchapter.php", "oneentry.php"),
        BODY.replace('class="red">target one', 'class="red">'),
        BODY.replace("examples found for", "matches found for"),
    ],
)
def test_bad_page_identity_totals_or_targets_are_drift(bad_html: str) -> None:
    mod = import_module("cal_mcp.targum_concordance_examples")
    with pytest.raises(mod.TargumConcordanceExamplesParseError):
        parse(bad_html)


@pytest.mark.anyio
async def test_service_one_fixed_get_with_exact_ordered_selectors() -> None:
    mod = import_module("cal_mcp.targum_concordance_examples")
    requests: list[CalRequest] = []

    async def fixture_transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return response()

    service = mod.TargumConcordanceExamplesService(CalHttpClient(transport=fixture_transport))
    data = (await service.examples("klb N", ["51001", "51002"])).to_dict()
    assert requests == [
        CalRequest(
            method="GET",
            path="show1dialectKWIC.php",
            params=(
                ("lemma", "klb"),
                ("pos", "N"),
                ("texts", "51001 51002"),
                ("charset", "H"),
            ),
        )
    ]
    assert data["lemma_key"] == "klb N"
    assert data["text_ids"] == ["51001", "51002"]
    assert data["total"] == 2
    assert data["provenance"]["source_url"] == SOURCE
    assert data["provenance"]["operation"] == "targum_concordance_examples"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "ids",
    [
        ["51001", "51001"],
        ["51001", "not-an-id"],
        ["51001", ""],
        [],
        ["1"] * 33,
    ],
)
async def test_bad_text_group_rejected_before_transport(ids: list[str]) -> None:
    mod = import_module("cal_mcp.targum_concordance_examples")
    requests: list[CalRequest] = []

    async def rejecting(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        raise AssertionError("invalid selector contacted CAL")

    service = mod.TargumConcordanceExamplesService(CalHttpClient(transport=rejecting))
    with pytest.raises(CalInputError):
        await service.examples("klb N", ids)
    assert requests == []


def test_parent_concordance_exposes_ordered_typed_followup_group() -> None:
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "cal" / "targum_concordance_klb_current.html"
    parent = parse_targum_concordance_page(
        response(fixture.read_text(encoding="utf-8"), "https://cal.huc.edu/showtargumKWIC.php"),
        lemma_key="klb N",
    )
    # The actual parent response exposes the selectors without asking clients to parse URLs.
    from cal_mcp.targum import _concordance_row_to_dict

    row = _concordance_row_to_dict(parent.rows[0])
    assert row["text_ids"] == ["51001", "51002", "51003", "51004", "51005"]


@pytest.mark.anyio
async def test_new_mcp_tool_has_exact_public_selector_schema() -> None:
    server = import_module("cal_mcp.server")
    async with Client(server.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
    schema = tools["cal_targum_concordance_examples"].input_schema
    assert set(schema["properties"]) == {"lemma_key", "text_ids"}
    assert set(schema["required"]) == {"lemma_key", "text_ids"}
