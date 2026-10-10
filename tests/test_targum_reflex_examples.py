"""Issue #247 RED: bounded, explicit Onqelos/Neofiti reflex verse examples."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path

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
    "MT line B Deut 22:8</span></div><br>"
    '<div><span class="heb">Targum line A</span></div><hr>'
    '<div><span class="heb">MT line A Deut 22:8<br>'
    "MT line B Deut 22:8</span></div><br>"
    '<div><span class="heb">Targum line A</span></div><hr><hr>'
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
        '<div><span class="heb">MT line A Deut 22:8</span></div><br>'
        '<div><span class="heb">Neofiti Aramaic verse</span></div><hr><hr>'
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


@pytest.mark.anyio
async def test_public_mcp_reflex_followup_preserves_source_shape_without_recursive_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cal_mcp import server as server_module

    requests: list[CalRequest] = []

    async def fixture_transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return _response()

    def make_client() -> CalHttpClient:
        return CalHttpClient(transport=fixture_transport)

    monkeypatch.setattr(server_module, "CalHttpClient", make_client)
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool(
            "cal_targum_reflex_examples",
            {"targum": "onqelos", "mt_lemma_id": "1751", "lemma_key": "tyq#2 N"},
        )

    assert result.is_error is False
    content = result.structured_content
    assert content is not None
    assert content["source_label"] == "Onqelos"
    assert content["mt_hebrew_lemma"] == "מַעֲקֶה"
    assert len(content["examples"]) == 2
    assert content["examples"][0] == content["examples"][1]
    assert content["provenance"]["source_url"] == ONQELOS_URL
    assert requests == [
        CalRequest(
            method="GET",
            path="getOMT.php",
            params=(("MT", "1751"), ("cal", "tyq#2 N")),
        )
    ]


def test_boolean_style_html_attribute_does_not_escape_as_python_exception() -> None:
    module = import_module("cal_mcp.targum_examples")
    malformed = ONQELOS_BODY.replace('class="heb"', "class")
    with pytest.raises(module.TargumReflexExamplesParseError):
        _parse(malformed)


def test_malformed_source_port_is_reported_as_parser_drift() -> None:
    module = import_module("cal_mcp.targum_examples")
    unsafe = ONQELOS_URL.replace("cal.huc.edu", "cal.huc.edu:bad")
    with pytest.raises(module.TargumReflexExamplesParseError):
        module.parse_targum_reflex_examples_page(
            _response(url=unsafe),
            targum="onqelos",
            mt_lemma_id="1751",
            lemma_key="tyq#2 N",
        )


def test_nested_mt_and_aramaic_blocks_are_not_current_cal_pairing() -> None:
    """RED: reject the old invented nested fixture even if its words look plausible."""
    module = import_module("cal_mcp.targum_examples")
    nested = ONQELOS_BODY.replace(
        "</span></div><br><div><span",
        "</span><br><div><span",
    ).replace(
        "Targum line A</span></div><hr>",
        "Targum line A</span></div></div><hr>",
    )
    with pytest.raises(module.TargumReflexExamplesParseError):
        _parse(nested)


def test_unseparated_consecutive_pairs_are_parser_drift() -> None:
    module = import_module("cal_mcp.targum_examples")
    no_separator = ONQELOS_BODY.replace(
        "Targum line A</span></div><hr><div>",
        "Targum line A</span></div><div>",
    )
    with pytest.raises(module.TargumReflexExamplesParseError):
        _parse(no_separator)


def test_missing_second_sibling_block_is_parser_drift() -> None:
    module = import_module("cal_mcp.targum_examples")
    only_mt = ONQELOS_BODY.replace(
        '<div><span class="heb">Targum line A</span></div>',
        "",
    )
    with pytest.raises(module.TargumReflexExamplesParseError):
        _parse(only_mt)


def test_server_instructions_expose_explicit_targum_reflex_followup() -> None:
    instructions = (
        Path("src/cal_mcp/server.py")
        .read_text(encoding="utf-8")
        .split("instructions=(", 1)[1]
        .split("version=__version__", 1)[0]
    )
    assert "cal_targum_hebrew_reflexes" in instructions
    assert "cal_targum_reflex_examples" in instructions
    assert "mt_lemma_id" in instructions
    assert "example_url" in instructions
