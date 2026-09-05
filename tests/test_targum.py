from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.targum import (
    TargumParallelStatus,
    TargumParseError,
    TargumService,
    parse_hebrew_lemma_options_page,
    parse_targum_concordance_page,
    parse_targum_parallel_page,
    parse_targum_reflex_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 5, 11, 11, tzinfo=UTC)


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


def test_parallel_parser_preserves_mt_ordered_sources_unicode_and_links() -> None:
    page = parse_targum_parallel_page(
        _fixture_response(
            "targum_parallel_gen_1_1.html",
            "https://cal.huc.edu/showtargum.php",
        ),
        book="Gen",
        chapter=1,
        verse=1,
    )

    assert page.status is TargumParallelStatus.FOUND
    assert page.mt_text == "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ"
    assert [reading.label for reading in page.readings] == [
        "Onqelos:",
        "Pseudo Jonathan:",
        "Neofiti:",
        "FTP Gn",
        "Peshitta:",
    ]
    assert page.readings[0].chapter_url == (
        "https://cal.huc.edu/get_a_chapter.php?file=51001&sub=01&cset=H"
    )
    assert page.readings[3].chapter_url is None
    assert "ܒܪܫܝܬ" in page.readings[-1].text
    assert all("Samaritan" not in reading.label for reading in page.readings)


def test_parallel_explicit_coordinate_error_is_typed_not_found() -> None:
    page = parse_targum_parallel_page(
        _fixture_response(
            "targum_parallel_not_found.html",
            "https://cal.huc.edu/showtargum.php",
        ),
        book="Gen",
        chapter=1,
        verse=99,
    )

    assert page.status is TargumParallelStatus.NOT_FOUND
    assert page.mt_text is None
    assert page.readings == ()


def test_parallel_heading_must_match_requested_reference() -> None:
    with pytest.raises(TargumParseError):
        parse_targum_parallel_page(
            _fixture_response(
                "targum_parallel_gen_1_1.html",
                "https://cal.huc.edu/showtargum.php",
            ),
            book="Exod",
            chapter=1,
            verse=1,
        )


@pytest.mark.parametrize(
    "body",
    [
        "<html><body><h1>MT and targums for Gen 1:1</h1><p>changed</p></body></html>",
        (
            "<html><body><h1>MT and targums for Gen 1:1</h1>"
            '<div class="targum-block"><span class="heb">MT</span></div>'
            '<div class="targum-block"><a href="https://example.org/x">Onqelos:</a>'
            '<span class="heb">text</span></div></body></html>'
        ),
        (
            "<html><body><h1>MT and targums for Gen 1:1</h1><p>error in coordinate</p>"
            '<div class="targum-block"><span class="heb">MT</span></div>'
            '<div class="targum-block">Onqelos: <span class="heb">text</span></div>'
            "</body></html>"
        ),
    ],
)
def test_parallel_changed_cross_origin_or_contradictory_markup_is_drift(body: str) -> None:
    with pytest.raises(TargumParseError):
        parse_targum_parallel_page(
            _inline_response(body, "https://cal.huc.edu/showtargum.php"),
            book="Gen",
            chapter=1,
            verse=1,
        )


def test_targum_concordance_preserves_sections_counts_order_and_links() -> None:
    page = parse_targum_concordance_page(
        _fixture_response(
            "targum_concordance_klb.html",
            "https://cal.huc.edu/showtargumKWIC.php",
        ),
        lemma_key="klb N",
    )

    assert page.total == 59
    assert [(row.section, row.label, row.count) for row in page.rows] == [
        ("Torah", "Onqelos", 3),
        ("Torah", "Targum Pseudo-Jonathan", 4),
        ("Torah", "Targum Neofiti", 4),
        ("Writing Prophets", "Targum Psalms", 48),
    ]
    assert page.rows[0].example_url.startswith(
        "https://cal.huc.edu/show1dialectKWIC.php?lemma=klb&pos=N"
    )


def test_targum_concordance_complete_zero_table_is_valid_empty_result() -> None:
    page = parse_targum_concordance_page(
        _fixture_response(
            "targum_concordance_zero.html",
            "https://cal.huc.edu/showtargumKWIC.php",
        ),
        lemma_key="zzzzzz N",
    )

    assert page.total == 0
    assert page.rows
    assert all(row.count == 0 for row in page.rows)


@pytest.mark.parametrize(
    "body",
    [
        (
            "<h1>CAL: Targum KWIC counts for klb N</h1><table>"
            '<tr><td><a href="/show1dialectKWIC.php?lemma=klb&amp;pos=N&amp;'
            'texts=1">Onqelos</a></td><td>3</td></tr>'
            "</table><p>total examples: 4</p>"
        ),
        (
            "<h1>CAL: Targum KWIC counts for klb N</h1><table>"
            '<tr><td><a href="https://example.org/x">Onqelos</a></td><td>3</td></tr>'
            "</table><p>total examples: 3</p>"
        ),
        "<h1>CAL: Targum KWIC counts for klb N</h1><p>total examples: 0</p>",
    ],
)
def test_targum_concordance_incomplete_or_inconsistent_markup_is_drift(body: str) -> None:
    with pytest.raises(TargumParseError):
        parse_targum_concordance_page(
            _inline_response(body, "https://cal.huc.edu/showtargumKWIC.php"),
            lemma_key="klb N",
        )


def test_hebrew_lemma_chooser_preserves_opaque_ids_unicode_labels_and_pos() -> None:
    page = parse_hebrew_lemma_options_page(
        _fixture_response(
            "targum_hebrew_lemmas_mem_onqelos.html",
            "https://cal.huc.edu/Omtlemmas/memMTlemma.html",
        ),
        targum="onqelos",
    )

    assert [(item.mt_lemma_id, item.label, item.pos) for item in page.candidates] == [
        ("1751", "מַעֲקֶה n", "n"),
        ("1752", "מַעֲרֶכֶת n", "n"),
        ("1806", "משח v", "v"),
    ]


def test_hebrew_lemma_chooser_requires_source_specific_action_and_unique_ids() -> None:
    wrong_source = _fixture_response(
        "targum_hebrew_lemmas_mem_neofiti.html",
        "https://cal.huc.edu/mtlemmas/memMTlemma.html",
    )
    with pytest.raises(TargumParseError):
        parse_hebrew_lemma_options_page(wrong_source, targum="onqelos")

    duplicate = _inline_response(
        "<h1>CAL: MT lemma chooser</h1><form method='post' action='/getOmtlemma.php'>"
        "<label><input type='radio' name='R1' value='1751'>מַעֲקֶה n</label>"
        "<label><input type='radio' name='R1' value='1751'>מַעֲרֶכֶת n</label>"
        "</form>",
        "https://cal.huc.edu/Omtlemmas/memMTlemma.html",
    )
    with pytest.raises(TargumParseError):
        parse_hebrew_lemma_options_page(duplicate, targum="onqelos")


def test_onqelos_reflex_parser_preserves_mt_lemma_cal_key_display_and_frequency() -> None:
    page = parse_targum_reflex_page(
        _fixture_response(
            "targum_reflex_onqelos_1751.html",
            "https://cal.huc.edu/getOmtlemma.php",
        ),
        targum="onqelos",
        mt_lemma_id="1751",
    )

    assert page.source_label == "Onkelos"
    assert page.mt_hebrew_lemma == "מַעֲקֶה"
    assert len(page.reflexes) == 1
    assert page.reflexes[0].lemma_key == "tyq#2 N"
    assert page.reflexes[0].label == "תיק #2 N"
    assert page.reflexes[0].frequency == 2
    assert page.reflexes[0].example_url == ("https://cal.huc.edu/getOMT.php?MT=1751&cal=tyq%232+N")


def test_neofiti_reflex_parser_preserves_multiple_ordered_correspondences() -> None:
    page = parse_targum_reflex_page(
        _fixture_response(
            "targum_reflex_neofiti_1751.html",
            "https://cal.huc.edu/getNmtlemma.php",
        ),
        targum="neofiti",
        mt_lemma_id="1751",
    )

    assert page.source_label == "Neofiti"
    assert [item.lemma_key for item in page.reflexes] == ["gypwp N", "syyg N"]
    assert [item.frequency for item in page.reflexes] == [1, 1]


@pytest.mark.parametrize(
    "body",
    [
        (
            "<h1>Onkelos correspondences to</h1><table>"
            '<tr><td><a href="/getOMT.php?MT=999999&amp;cal=br+N">בר N</a></td>'
            "<td>1634</td></tr></table>"
        ),
        (
            "<h1>Onkelos correspondences to מַעֲקֶה</h1><table>"
            '<tr><td><a href="/getOMT.php?MT=1752&amp;cal=tyq%232+N">תיק #2 N</a>'
            "</td><td>2</td></tr></table>"
        ),
        (
            "<h1>Onkelos correspondences to מַעֲקֶה</h1><table>"
            '<tr><td><a href="https://example.org/getOMT.php?MT=1751&amp;'
            'cal=tyq%232+N">תיק #2 N</a></td><td>2</td></tr></table>'
        ),
    ],
)
def test_reflex_invalid_id_fallback_or_link_contradiction_is_drift(body: str) -> None:
    with pytest.raises(TargumParseError):
        parse_targum_reflex_page(
            _inline_response(body, "https://cal.huc.edu/getOmtlemma.php"),
            targum="onqelos",
            mt_lemma_id="1751",
        )


class RecordingTransport:
    def __init__(self, responses: dict[str, CalResponse]) -> None:
        self.responses = responses
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.responses[request.path]


def _service() -> tuple[TargumService, RecordingTransport]:
    transport = RecordingTransport(
        {
            "showtargum.php": _fixture_response(
                "targum_parallel_gen_1_1.html",
                "https://cal.huc.edu/showtargum.php",
            ),
            "showtargumKWIC.php": _fixture_response(
                "targum_concordance_klb.html",
                "https://cal.huc.edu/showtargumKWIC.php",
            ),
            "Omtlemmas/memMTlemma.html": _fixture_response(
                "targum_hebrew_lemmas_mem_onqelos.html",
                "https://cal.huc.edu/Omtlemmas/memMTlemma.html",
            ),
            "getOmtlemma.php": _fixture_response(
                "targum_reflex_onqelos_1751.html",
                "https://cal.huc.edu/getOmtlemma.php",
            ),
        }
    )
    return TargumService(CalHttpClient(transport=transport)), transport


@pytest.mark.anyio
async def test_services_use_one_request_per_operation_and_preserve_provenance() -> None:
    service, transport = _service()

    parallel = await service.parallel(
        "Gen",
        1,
        1,
        include_peshitta=True,
        include_samaritan=True,
    )
    concordance = await service.concordance(" klb N ")
    lemmas = await service.hebrew_lemmas("mem", "onqelos")
    reflexes = await service.hebrew_reflexes("onqelos", "1751")

    assert parallel.status is TargumParallelStatus.FOUND
    assert concordance.total == 59
    assert lemmas.candidates[0].mt_lemma_id == "1751"
    assert reflexes.reflexes[0].lemma_key == "tyq#2 N"

    assert transport.requests == [
        CalRequest(
            method="POST",
            path="showtargum.php",
            data=(
                ("bookname", "01"),
                ("chapter", "01"),
                ("verse", "01"),
                ("Peshitta", "ON"),
                ("Sam", "ON"),
            ),
        ),
        CalRequest(
            method="POST",
            path="showtargumKWIC.php",
            data=(("lemma", "klb"), ("pos", "N")),
        ),
        CalRequest(method="GET", path="Omtlemmas/memMTlemma.html"),
        CalRequest(
            method="POST",
            path="getOmtlemma.php",
            data=(("R1", "1751"),),
        ),
    ]

    assert parallel.provenance.operation == "targum_parallel"
    assert parallel.provenance.book == "Gen"
    assert parallel.provenance.book_id == "01"
    assert parallel.provenance.chapter == 1
    assert parallel.provenance.verse == 1
    assert parallel.provenance.retrieved_at == RETRIEVED_AT
    assert concordance.provenance.lemma_key == "klb N"
    assert lemmas.provenance.initial == "mem"
    assert lemmas.provenance.targum == "onqelos"
    assert reflexes.provenance.mt_lemma_id == "1751"


@pytest.mark.anyio
async def test_invalid_public_inputs_fail_before_transport() -> None:
    service, transport = _service()

    invalid_calls = [
        lambda: service.parallel("Genesis", 1, 1),
        lambda: service.parallel("Gen", 0, 1),
        lambda: service.parallel("Gen", 1, 1000),
        lambda: service.concordance("klb"),
        lambda: service.hebrew_lemmas("memm", "onqelos"),
        lambda: service.hebrew_lemmas("mem", "pseudo_jonathan"),
        lambda: service.hebrew_reflexes("pseudo_jonathan", "1751"),
        lambda: service.hebrew_reflexes("onqelos", ""),
        lambda: service.hebrew_reflexes("onqelos", "0"),
        lambda: service.hebrew_reflexes("onqelos", "abc"),
        lambda: service.hebrew_reflexes("onqelos", "123456789"),
    ]

    for call in invalid_calls:
        with pytest.raises(ValueError):
            await call()

    assert transport.requests == []


@pytest.mark.anyio
async def test_mcp_exposes_task_level_targum_tools_without_private_cal_parameters() -> None:
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    expected = {
        "cal_targum_parallel": {
            "book",
            "chapter",
            "verse",
            "include_peshitta",
            "include_samaritan",
        },
        "cal_targum_concordance": {"lemma_key"},
        "cal_targum_hebrew_lemmas": {"initial", "targum"},
        "cal_targum_hebrew_reflexes": {"targum", "mt_lemma_id"},
    }
    for name, properties in expected.items():
        assert name in tools
        assert set(tools[name].input_schema["properties"]) == properties
        for private in (
            "bookname",
            "Peshitta",
            "Sam",
            "R1",
            "lemma",
            "pos",
            "texts",
            "charset",
        ):
            assert private not in tools[name].input_schema["properties"]
