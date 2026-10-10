"""Issue #247 RED: bounded, explicit Onqelos/Neofiti reflex verse examples."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse

RETRIEVED_AT = datetime(2026, 10, 10, 14, 25, tzinfo=UTC)
ONQELOS_URL = "https://cal.huc.edu/getOMT.php?MT=1751&cal=tyq%232+N"

# Reduced source structure from issue #109 bounded current CAL DOM audit
# (run 38059641146). Synthetic text, no full CAL verse transcriptions.
ONQELOS_BODY = (
    "<html><body><center>"
    "<h3>Onqelos verses where MT מַעֲקֶה</h3>"
    '<h3>is rendered by Aramaic <a href="/oneentry.php?cits=all&amp;lemma=tyq%232+N">'
    "tyq#2 N</a></h3>"
    "Click the Aramaic lemma to see the full entry<br>"
    '<div><span class="heb">MT line A Deut 22:8<br>'
    "MT line B Deut 22:8</span><br>"
    '<div><span class="heb">Targum line A</span></div></div><hr>'
    '<div><span class="heb">MT line A Deut 22:8<br>'
    "MT line B Deut 22:8</span><br>"
    '<div><span class="heb">Targum line A</span></div></div>'
    "</center></body></html>"
)


def _response(body: str = ONQELOS_BODY, url: str = ONQELOS_URL) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _parse(
    body: str = ONQELOS_BODY,
    *,
    targum: str = "onqelos",
    mt_lemma_id: str = "1751",
    lemma_key: str = "tyq#2 N",
):
    module = import_module("cal_mcp.targum_examples")
    return module.parse_targum_reflex_examples_page(
        _response(body),
        targum=targum,
        mt_lemma_id=mt_lemma_id,
        lemma_key=lemma_key,
    )


def test_onqelos_example_page_preserves_order_and_repeated_verses() -> None:
    page = _parse()
    assert page.source_label == "Onqelos"
    assert page.mt_hebrew_lemma == "מַעֲקֶה"
    assert page.lemma_key == "tyq#2 N"
    assert len(page.examples) == 2
    assert page.examples[0].mt_text == "MT line A Deut 22:8\nMT line B Deut 22:8"
    assert page.examples[0].targum_text == "Targum line A"
    assert page.examples[1] == page.examples[0]


@pytest.mark.parametrize(
    "bad",
    [
        ONQELOS_BODY.replace("tyq#2 N</a>", "br N</a>"),
        ONQELOS_BODY.replace("oneentry.php", "getOMT.php"),
        ONQELOS_BODY.replace("cits=all", "cits=other"),
        ONQELOS_BODY.replace("MT מַעֲקֶה", "MT "),
        ONQELOS_BODY.replace('<span class="heb">Targum line A</span>', ""),
        ONQELOS_BODY.replace('<span class="heb">MT line A', '<span class="rom">MT line A'),
    ],
)
def test_mismatched_link_or_missing_example_semantics_are_drift(bad: str) -> None:
    module = import_module("cal_mcp.targum_examples")
    with pytest.raises(module.TargumReflexExamplesParseError):
        _parse(bad)


@pytest.mark.anyio
async def test_service_requests_only_one_fixed_get_and_records_source_provenance() -> None:
    module = import_module("cal_mcp.targum_examples")
    requests: list[CalRequest] = []

    async def fixture_transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return _response()

    service = module.TargumReflexExamplesService(CalHttpClient(transport=fixture_transport))
    result = await service.examples("onqelos", "1751", "tyq#2 N")

    assert requests == [
        CalRequest(
            method="GET",
            path="getOMT.php",
            params=(("MT", "1751"), ("cal", "tyq#2 N")),
        )
    ]
    payload = result.to_dict()
    assert payload["targum"] == "onqelos"
    assert payload["lemma_key"] == "tyq#2 N"
    assert payload["mt_lemma_id"] == "1751"
    assert payload["provenance"]["source_url"] == ONQELOS_URL
    assert len(payload["examples"]) == 2


@pytest.mark.anyio
async def test_new_tool_schema_is_explicit_and_has_no_arbitrary_url() -> None:
    module = import_module("cal_mcp.server")
    async with Client(module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
    assert "cal_targum_reflex_examples" in tools
    schema = tools["cal_targum_reflex_examples"].input_schema
    assert set(schema["properties"]) == {"targum", "mt_lemma_id", "lemma_key"}
    assert set(schema["required"]) == {"targum", "mt_lemma_id", "lemma_key"}


def test_neofiti_examples_use_distinct_route_and_same_observed_block_semantics() -> None:
    module = import_module("cal_mcp.targum_examples")
    url = "https://cal.huc.edu/getNMT.php?MT=1751&cal=gypwp+N"
    body = (
        "<html><body><center>"
        "<h3>Neofiti verses where MT מַעֲקֶה</h3>"
        '<h3>is rendered by Aramaic <a href="/oneentry.php?lemma=gypwp+N&amp;cits=all">'
        "gypwp N</a></h3>"
        "Click the Aramaic lemma to see the full entry<br>"
        '<div><span class="heb">MT line A Deut 22:8</span><br>'
        '<div><span class="heb">Neofiti Aramaic verse</span></div></div>'
        "</center></body></html>"
    )
    page = module.parse_targum_reflex_examples_page(
        _response(body, url),
        targum="neofiti",
        mt_lemma_id="1751",
        lemma_key="gypwp N",
    )
    assert page.source_label == "Neofiti"
    assert len(page.examples) == 1
    assert page.examples[0].targum_text == "Neofiti Aramaic verse"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("targum", "mt_lemma_id", "lemma_key"),
    [
        ("nonsense", "1751", "tyq#2 N"),
        ("onqelos", "wrong", "tyq#2 N"),
        ("onqelos", "1751", "not a canonical key"),
        ("neofiti", "1751", "tyq%232 N"),
    ],
)
async def test_invalid_selector_is_rejected_before_cal_transport(
    targum: str,
    mt_lemma_id: str,
    lemma_key: str,
) -> None:
    module = import_module("cal_mcp.targum_examples")
    requests: list[CalRequest] = []

    async def rejecting_transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        raise AssertionError("invalid input reached CAL")

    service = module.TargumReflexExamplesService(CalHttpClient(transport=rejecting_transport))
    with pytest.raises(ValueError):
        await service.examples(targum, mt_lemma_id, lemma_key)
    assert requests == []


def test_visible_unrecognized_cal_content_is_not_silently_dropped() -> None:
    """A result with valid pairs plus an additional warning is still drift."""

    module = import_module("cal_mcp.targum_examples")
    unexpected = ONQELOS_BODY.replace(
        "Click the Aramaic lemma to see the full entry",
        "Click the Aramaic lemma to see the full entry"
        "<div>Notice: some examples are unavailable</div>",
    )
    with pytest.raises(module.TargumReflexExamplesParseError):
        _parse(unexpected)


def test_source_query_must_match_all_three_caller_selectors() -> None:
    module = import_module("cal_mcp.targum_examples")
    invalid = _response(url=ONQELOS_URL.replace("MT=1751", "MT=1752"))
    with pytest.raises(module.TargumReflexExamplesParseError):
        module.parse_targum_reflex_examples_page(
            invalid,
            targum="onqelos",
            mt_lemma_id="1751",
            lemma_key="tyq#2 N",
        )
