from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 5, 13, 13, tzinfo=UTC)

EXPECTED_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("jastrow", "J", "Jastrow"),
    ("lexicon_syriacum", "L", "Lexicon Syriacum"),
    ("syriac_lexicon", "K", "A Syriac Lexicon"),
    ("compendious_syriac_dictionary", "j", "A Compendious Syriac Dictionary"),
    ("djba", "B", "A Dictionary of Jewish Babylonian Aramaic"),
    ("djpa", "P", "A Dictionary of Jewish Palestinian Aramaic"),
    ("levy_targumim", "V", "Levy, Chaldäisches Wörterbuch ü.die Targumim"),
    ("mandaic_dictionary", "M", "A Mandaic Dictionary"),
    ("dnsi", "W", "Dictionary of the Northwest Semitic Inscriptions"),
    ("thesaurus_syriacus", "T", "Thesaurus Syriacus"),
    ("samaritan_aramaic", "R", "Dictionary of Samaritan Aramaic"),
    ("schulthess", "S", "Schulthess Lexicon Syropalaestinum"),
    ("dcpa", "C", "A Dictionary of Christian Palestinian Aramaic"),
    ("judean_aramaic", "D", "A Dictionary of Judean Aramaic"),
    ("qumran_aramaic", "Q", "Dictionary of Qumran Aramaic Page"),
)


def _module() -> Any:
    return importlib.import_module("cal_mcp.dictionary_collation")


def _fixture_response(name: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/searchdicts.php",
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _inline_response(body: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/searchdicts.php",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _result_html(page: str, label: str, *, empty: bool = False) -> str:
    row = (
        '<p class="red">No data available for that page.</p>'
        if empty
        else '<p><a href="oneentry.php?lemma=br+N&amp;cits=no">br N</a> : son</p>'
    )
    return (
        "<html><head>"
        f"<title>CAL: entries for page {page} of {label}</title>"
        "</head><body>"
        '<div class="summary-card">'
        f"<h3>CAL entries corresponding to page {page} of</h3>"
        f"<p>{label}</p>"
        "<p>Click on a lemma to see an outline entry.</p>"
        f"{row}</div></body></html>"
    )


def test_success_parser_preserves_order_alias_targets_and_punctuation() -> None:
    module = _module()
    page = module.parse_dictionary_collation_page(
        _fixture_response("dictionary_collation_jastrow_705.html")
    )

    assert page.page == "705"
    assert page.source_label == "Jastrow"
    assert page.explicit_empty is False
    assert [entry.display_lemma for entry in page.entries] == [
        "l)w N",
        "lxt V",
        "lTw N",
        "lTy#2 V",
        "lT$ V",
        "l(w N",
    ]
    assert [entry.target_lemma_key for entry in page.entries] == [
        "l)w N",
        "lht V",
        "l+w N",
        "l+y#2 V",
        "l+$ V",
        "l(w N",
    ]
    assert page.entries[0].gloss == "work, labor"
    assert page.entries[1].gloss == "to pant → lht V"
    assert page.entries[1].display_lemma != page.entries[1].target_lemma_key
    assert page.entries[0].entry_url == (
        "https://cal.huc.edu/oneentry.php?lemma=l%29w+N&cits=no"
    )


def test_explicit_no_data_marker_is_successful_empty_result() -> None:
    module = _module()
    page = module.parse_dictionary_collation_page(
        _fixture_response("dictionary_collation_jastrow_empty.html")
    )

    assert page.page == "99999"
    assert page.source_label == "Jastrow"
    assert page.entries == ()
    assert page.explicit_empty is True


@pytest.mark.parametrize(
    "body",
    [
        # Missing page identity.
        (
            "<html><body><div class='summary-card'>"
            '<p><a href="oneentry.php?lemma=br+N">br N</a> : son</p>'
            "</div></body></html>"
        ),
        # Missing summary card.
        (
            "<html><head><title>CAL: entries for page 705 of Jastrow</title></head>"
            "<body></body></html>"
        ),
        # Duplicate summary cards.
        (
            "<html><head><title>CAL: entries for page 705 of Jastrow</title></head><body>"
            '<div class="summary-card"><p class="red">No data available for that page.</p></div>'
            '<div class="summary-card"><p class="red">No data available for that page.</p></div>'
            "</body></html>"
        ),
        # Explicit empty contradicts a data row.
        (
            "<html><head><title>CAL: entries for page 705 of Jastrow</title></head><body>"
            '<div class="summary-card">'
            '<p><a href="oneentry.php?lemma=br+N">br N</a> : son</p>'
            '<p class="red">No data available for that page.</p>'
            "</div></body></html>"
        ),
        # Result row has no gloss.
        (
            "<html><head><title>CAL: entries for page 705 of Jastrow</title></head><body>"
            '<div class="summary-card"><p><a href="oneentry.php?lemma=br+N">br N</a></p></div>'
            "</body></html>"
        ),
        # Cross-origin row link.
        (
            "<html><head><title>CAL: entries for page 705 of Jastrow</title></head><body>"
            '<div class="summary-card"><p>'
            '<a href="https://example.org/oneentry.php?lemma=br+N">br N</a> : son'
            "</p></div></body></html>"
        ),
        # Multiple lemma query values.
        (
            "<html><head><title>CAL: entries for page 705 of Jastrow</title></head><body>"
            '<div class="summary-card"><p>'
            '<a href="oneentry.php?lemma=br+N&amp;lemma=bt+N">br N</a> : son'
            "</p></div></body></html>"
        ),
        # Unexpected entry-link query control.
        (
            "<html><head><title>CAL: entries for page 705 of Jastrow</title></head><body>"
            '<div class="summary-card"><p>'
            '<a href="oneentry.php?lemma=br+N&amp;extra=1">br N</a> : son'
            "</p></div></body></html>"
        ),
        # Unexpected entry endpoint.
        (
            "<html><head><title>CAL: entries for page 705 of Jastrow</title></head><body>"
            '<div class="summary-card"><p>'
            '<a href="cal_entry_web.php?lemma=br+N">br N</a> : son'
            "</p></div></body></html>"
        ),
        # No rows and no explicit empty state.
        (
            "<html><head><title>CAL: entries for page 705 of Jastrow</title></head><body>"
            '<div class="summary-card"><p>changed result markup</p></div>'
            "</body></html>"
        ),
    ],
)
def test_malformed_or_contradictory_markup_fails_closed(body: str) -> None:
    module = _module()
    with pytest.raises(module.DictionaryCollationParseError):
        module.parse_dictionary_collation_page(_inline_response(body))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("705", "705"),
        (" 1:134 ", "1:134"),
        ("1:134,2:212", "1:134, 2:212"),
        (" 1:134 ,   2:212 ", "1:134, 2:212"),
        ("001:0007, 9", "001:0007, 9"),
    ],
)
def test_documented_page_reference_forms_are_normalized(raw: str, expected: str) -> None:
    module = _module()
    assert module._normalize_page_reference(raw) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "1:",
        ":1",
        "1::2",
        "1-2",
        "xii",
        "1,,2",
        "1,\n2",
        "1\t2",
        "1:2:3",
        "9" * 97,
        ",".join(str(index) for index in range(1, 18)),
    ],
)
def test_undocumented_or_unbounded_page_references_fail_locally(value: str) -> None:
    module = _module()
    with pytest.raises(ValueError):
        module._normalize_page_reference(value)


class RecordingTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []
        self.override_page: str | None = None
        self.override_label: str | None = None

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        form = dict(request.data)
        code_to_label = {code: label for _, code, label in EXPECTED_SOURCES}
        label = self.override_label or code_to_label[form["dict"]]
        page = self.override_page or form["page"]
        return _inline_response(_result_html(page, label))


@pytest.mark.anyio
async def test_all_sources_map_to_unique_current_codes_and_one_request_each() -> None:
    module = _module()
    assert tuple(item.value for item in module.DictionarySource) == tuple(
        source for source, _, _ in EXPECTED_SOURCES
    )

    transport = RecordingTransport()
    service = module.DictionaryCollationService(CalHttpClient(transport=transport))

    for source, code, label in EXPECTED_SOURCES:
        result = await service.collate(source, "705")
        assert result.source.value == source
        assert result.source_label == label
        assert result.page == "705"
        assert result.entries[0].target_lemma_key == "br N"
        assert transport.requests[-1] == CalRequest(
            method="POST",
            path="searchdicts.php",
            data=(("dict", code), ("page", "705")),
        )

    assert len({request.data[0][1] for request in transport.requests}) == len(EXPECTED_SOURCES)
    assert transport.requests[0].data[0] == ("dict", "J")
    assert transport.requests[3].data[0] == ("dict", "j")


@pytest.mark.anyio
async def test_service_normalizes_page_and_preserves_provenance() -> None:
    module = _module()
    transport = RecordingTransport()
    service = module.DictionaryCollationService(CalHttpClient(transport=transport))

    result = await service.collate("jastrow", " 1:134,2:212 ")

    assert transport.requests == [
        CalRequest(
            method="POST",
            path="searchdicts.php",
            data=(("dict", "J"), ("page", "1:134, 2:212")),
        )
    ]
    assert result.page == "1:134, 2:212"
    assert result.provenance.source == "CAL"
    assert result.provenance.source_url == "https://cal.huc.edu/searchdicts.php"
    assert result.provenance.retrieved_at == RETRIEVED_AT
    assert result.provenance.operation == "dictionary_collation"
    assert result.provenance.dictionary_source.value == "jastrow"
    assert result.provenance.original_page == " 1:134,2:212 "
    assert result.provenance.submitted_page == "1:134, 2:212"

    serialized = result.to_dict()
    assert serialized["source"] == "jastrow"
    assert serialized["page"] == "1:134, 2:212"
    assert serialized["provenance"]["retrieved_at"] == RETRIEVED_AT.isoformat()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("override_page", "override_label"),
    [("706", None), (None, "Lexicon Syriacum")],
)
async def test_service_rejects_result_identity_mismatch(
    override_page: str | None,
    override_label: str | None,
) -> None:
    module = _module()
    transport = RecordingTransport()
    transport.override_page = override_page
    transport.override_label = override_label
    service = module.DictionaryCollationService(CalHttpClient(transport=transport))

    with pytest.raises(module.DictionaryCollationParseError):
        await service.collate("jastrow", "705")

    assert len(transport.requests) == 1


@pytest.mark.anyio
async def test_invalid_source_and_page_fail_before_transport() -> None:
    module = _module()
    transport = RecordingTransport()
    service = module.DictionaryCollationService(CalHttpClient(transport=transport))

    with pytest.raises(ValueError):
        await service.collate("not_a_dictionary", "705")
    with pytest.raises(ValueError):
        await service.collate("jastrow", "bad-page")

    assert transport.requests == []


def _collect_enums(value: object) -> list[list[object]]:
    found: list[list[object]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "enum" and isinstance(item, list):
                found.append(item)
            found.extend(_collect_enums(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_collect_enums(item))
    return found


@pytest.mark.anyio
async def test_mcp_exposes_readable_source_enum_without_cal_form_controls() -> None:
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    schema = tools["cal_dictionary_collation"].input_schema
    assert set(schema["properties"]) == {"source", "page"}
    assert schema["required"] == ["source", "page"]
    assert list(source for source, _, _ in EXPECTED_SOURCES) in _collect_enums(schema)
    for private_name in ("dict", "searchdicts.php", "code", "offset", "limit"):
        assert private_name not in schema["properties"]
