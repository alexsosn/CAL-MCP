from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import (
    LexiconLookupService,
    LexiconLookupStatus,
    LexiconParseError,
    parse_browse_page,
    parse_lexicon_entry,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
Parser = Callable[[CalResponse], object]


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def response(name: str, *, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=fixture_text(name).encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )


def test_complete_entry_preserves_senses_scripts_usage_derivatives_and_notes() -> None:
    entry = parse_lexicon_entry(
        response(
            "entry_br_n.html",
            url="https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
        ),
        lemma_key="br N",
    )

    assert entry.lemma.lemma_key == "br N"
    assert entry.lemma.headwords == ("br", "brˀ")
    assert entry.lemma.pronunciation == "bar [ber], brā"
    assert entry.lemma.part_of_speech == "n.m."
    assert entry.lemma.gloss == "son"

    assert [sense.label_path for sense in entry.senses] == [(1,), (1, 1), (1, 2)]
    assert entry.senses[0].definition == "son, child"
    assert entry.senses[0].dialects == ("Common Aramaic",)
    assert entry.senses[2].dialects == ("Syr", "JBA", "LJLA")

    citation = entry.senses[0].citations[0]
    assert citation.reference == "TAD B3.8 R.28"
    assert citation.url.endswith("/citation.php?id=tad-b3-8-r28")
    assert "והן ימות" in citation.text
    assert "ܘܗܢ ܝܡܘܬ" in citation.text

    assert entry.form_usage == (
        "plural: bnīn; absolute: bar in literary and Eastern dialects, ber in Western.",
    )
    assert [(item.headword, item.depth) for item in entry.derivatives] == [
        ("ˀbbr", 0),
        ("ˀbr", 0),
        ("mˀbrn, mˀbrnˀ", 1),
    ]
    assert entry.derivatives[1].lemma_key == ")br V"
    assert entry.derivatives[1].part_of_speech == "vb."
    assert entry.derivatives[1].gloss == "D to make a son"
    assert entry.notes[0] == "Occasionally the Hebrew form בן is found in the singular."


def test_unnumbered_primary_sense_and_nested_sense_are_preserved() -> None:
    entry = parse_lexicon_entry(
        response(
            "entry_nmy_x.html",
            url="https://cal.huc.edu/oneentry.php?cits=all&lemma=nmy+X",
        ),
        lemma_key="nmy X",
    )

    assert entry.lemma.headwords == ("nmy",)
    assert entry.lemma.part_of_speech == "adv."
    assert [sense.label_path for sense in entry.senses] == [(), (1,)]
    assert entry.senses[0].definition == "also"
    assert entry.senses[0].dialects == ("JBA", "JBAg", "LJLA")
    assert entry.senses[1].definition == "אינמי = אי נמי : or also"
    assert entry.notes == ("Attested as a corruption in the Yerushalmi Talmud: see DJPA s.v.",)


def test_missing_optional_sections_are_empty_not_parser_drift() -> None:
    entry = parse_lexicon_entry(
        response(
            "entry_bysh_n.html",
            url="https://cal.huc.edu/cal_entry_web.php?lemma=bysh+N",
        ),
        lemma_key="bysh N",
    )

    assert entry.form_usage == ()
    assert entry.derivatives == ()
    assert entry.notes == ()


@pytest.mark.parametrize(
    "html",
    [
        "<html><body><div>1</div><div>son, child</div></body></html>",
        "<html><body><header>br, brˀ (bar) n.m. son</header><div>1</div></body></html>",
    ],
)
def test_missing_required_entry_semantics_fail_explicitly(html: str) -> None:
    with pytest.raises(LexiconParseError):
        parse_lexicon_entry(
            CalResponse(
                status_code=200,
                url="https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
                body=html.encode(),
                content_type="text/html",
                retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
            ),
            lemma_key="br N",
        )


def test_browse_parser_preserves_aliases_and_homograph_keys() -> None:
    browse = parse_browse_page(
        response(
            "browse_b.html",
            url="https://cal.huc.edu/browseSKEYheaders.php?first3=%22b%22",
        )
    )

    alias_target = next(item for item in browse.entries if item.lemma_key == "bysh N")
    assert alias_target.aliases == ("bˀyšh", "bˀyštˀ")
    assert alias_target.headwords == ("byšh", "byštˀ")

    br_keys = [item.lemma_key for item in browse.entries if item.headwords[0] == "br"]
    assert br_keys == ["br N", "br#2 N"]


def test_browse_markup_without_entries_or_explicit_not_found_is_parser_drift() -> None:
    with pytest.raises(LexiconParseError):
        parse_browse_page(
            CalResponse(
                status_code=200,
                url="https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22",
                body=b"<html><body>unexpected replacement page</body></html>",
                content_type="text/html",
                retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
            )
        )


class FixtureTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []
        self.entry_calls: dict[str, int] = {}

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        params = dict(request.params)

        if request.path == "browseSKEYheaders.php":
            if params.get("first3") == '"zzz"':
                return response(
                    "not_found.html",
                    url="https://cal.huc.edu/browseSKEYheaders.php?first3=%22zzz%22",
                )
            return response(
                "browse_b.html",
                url="https://cal.huc.edu/browseSKEYheaders.php?first3=%22b%22",
            )

        if request.path == "cal_entry_web.php":
            lemma_key = params["lemma"]
            self.entry_calls[lemma_key] = self.entry_calls.get(lemma_key, 0) + 1
            fixture = {
                "br N": "entry_br_n.html",
                "bysh N": "entry_bysh_n.html",
            }[lemma_key]
            return response(
                fixture,
                url=f"https://cal.huc.edu/cal_entry_web.php?lemma={lemma_key.replace(' ', '+')}",
            )

        raise AssertionError(f"unexpected CAL request: {request}")


@pytest.mark.anyio
async def test_lookup_uses_bounded_browse_then_exact_entry_and_provenance() -> None:
    transport = FixtureTransport()
    service = LexiconLookupService(CalHttpClient(transport=transport))

    result = await service.lookup("bˀyšh")

    assert result.status is LexiconLookupStatus.FOUND
    assert result.entry is not None
    assert result.entry.lemma.lemma_key == "bysh N"
    assert result.provenance is not None
    assert result.provenance.source == "CAL"
    assert result.provenance.original_query == "bˀyšh"
    assert result.provenance.normalized_query == "bˀyšh"
    assert result.provenance.upstream_id == "bysh N"
    assert result.provenance.source_url.endswith("lemma=bysh+N")
    assert result.provenance.retrieved_at == datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

    assert transport.requests[0] == CalRequest(
        method="GET",
        path="browseSKEYheaders.php",
        params=(("first3", '"bˀy"'),),
    )
    assert transport.requests[1] == CalRequest(
        method="GET",
        path="cal_entry_web.php",
        params=(("lemma", "bysh N"),),
    )
    assert len(transport.requests) == 2


@pytest.mark.anyio
async def test_ambiguous_root_returns_candidates_without_guessing_or_entry_request() -> None:
    transport = FixtureTransport()
    service = LexiconLookupService(CalHttpClient(transport=transport))

    result = await service.lookup("br")

    assert result.status is LexiconLookupStatus.AMBIGUOUS
    assert result.entry is None
    assert [item.lemma_key for item in result.matches] == ["br N", "br#2 N"]
    assert len(transport.requests) == 1


@pytest.mark.anyio
async def test_explicit_lemma_key_disambiguates_only_a_matching_candidate() -> None:
    transport = FixtureTransport()
    service = LexiconLookupService(CalHttpClient(transport=transport))

    result = await service.lookup("br", lemma_key="br N")
    assert result.status is LexiconLookupStatus.FOUND
    assert result.entry is not None
    assert result.entry.lemma.gloss == "son"

    with pytest.raises(ValueError, match="lemma_key"):
        await service.lookup("br", lemma_key="unrelated N")


@pytest.mark.anyio
async def test_not_found_is_a_structured_result_distinct_from_parser_or_network_failure() -> None:
    transport = FixtureTransport()
    service = LexiconLookupService(CalHttpClient(transport=transport))

    result = await service.lookup("zzz")

    assert result.status is LexiconLookupStatus.NOT_FOUND
    assert result.entry is None
    assert result.matches == ()
    assert result.provenance is not None
    assert len(transport.requests) == 1


@pytest.mark.anyio
async def test_maintenance_failure_stays_a_content_failure_before_lexicon_parser() -> None:
    calls = 0

    async def maintenance_transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal calls
        del request, config
        calls += 1
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/browseSKEYheaders.php",
            body=b"<html><title>Maintenance</title><body>try later</body></html>",
            content_type="text/html",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        )

    service = LexiconLookupService(CalHttpClient(transport=maintenance_transport))
    with pytest.raises(CalContentError, match="maintenance"):
        await service.lookup("br")
    assert calls == 1
