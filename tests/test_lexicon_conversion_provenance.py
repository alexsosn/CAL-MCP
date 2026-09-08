from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from urllib.parse import quote

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LexiconLookupResult, LexiconLookupService, LexiconLookupStatus


def _browse_response(prefix: str, *entries: tuple[str, str]) -> CalResponse:
    if entries:
        body = (
            "<html><body>"
            + "".join(
                f'<div><a href="/oneentry.php?lemma={quote(lemma_key)}">{headword} n.m.</a></div>'
                f"<div>test gloss</div>"
                for lemma_key, headword in entries
            )
            + "</body></html>"
        )
    else:
        body = "<html><body>No matching lexical entries were found</body></html>"
    return CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/browseSKEYheaders.php?first3={prefix}",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 7, tzinfo=UTC),
    )


def _entry_response(lemma_key: str, headword: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/cal_entry_web.php?lemma={quote(lemma_key)}",
        body=(
            "<html><body>"
            f"<div>{headword} n.m. selected gloss</div>"
            "<div>1.</div><div>selected sense</div>"
            "</body></html>"
        ).encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 7, tzinfo=UTC),
    )


def _provenance_tuple(result: LexiconLookupResult, field: str) -> object:
    provenance = result.provenance
    assert provenance is not None
    return getattr(provenance, field, None)


@pytest.mark.anyio
async def test_ambiguous_not_found_preserves_candidates_and_requested_prefixes() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        prefix = dict(request.params)["first3"].strip('"')
        return _browse_response(prefix)

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("שלם")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.NOT_FOUND
    assert _provenance_tuple(result, "cal_code_word_candidates") == (("$lm", "&lm"),)
    assert _provenance_tuple(result, "cal_code_query_candidates") == ("$lm", "&lm")
    assert _provenance_tuple(result, "browse_prefixes") == ("$lm", "&lm")
    assert _provenance_tuple(result, "selected_cal_code_candidates") == ()
    assert [dict(request.params)["first3"] for request in requests] == ['"$lm"', '"&lm"']


@pytest.mark.anyio
async def test_deduplicated_lemma_retains_every_matching_encoding_candidate() -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        if request.path == "browseSKEYheaders.php":
            prefix = dict(request.params)["first3"].strip('"')
            if prefix == "$lm":
                return _browse_response(prefix, ("shared N", "$lm"))
            if prefix == "&lm":
                return _browse_response(prefix, ("shared N", "&lm"))
        if request.path == "cal_entry_web.php":
            return _entry_response("shared N", "$lm")
        raise AssertionError(f"unexpected request: {request}")

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("שלם")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.FOUND
    assert [item.lemma_key for item in result.matches] == ["shared N"]
    assert _provenance_tuple(result, "selected_cal_code_candidates") == ("$lm", "&lm")


@pytest.mark.anyio
async def test_explicit_selection_records_only_candidates_matching_selected_lemma() -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        if request.path == "browseSKEYheaders.php":
            prefix = dict(request.params)["first3"].strip('"')
            if prefix == "$lm":
                return _browse_response(prefix, ("shin N", "$lm"))
            if prefix == "&lm":
                return _browse_response(prefix, ("sin N", "&lm"))
        if request.path == "cal_entry_web.php":
            return _entry_response("sin N", "&lm")
        raise AssertionError(f"unexpected request: {request}")

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("שלם", lemma_key="sin N")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.FOUND
    assert _provenance_tuple(result, "selected_cal_code_candidates") == ("&lm",)


@pytest.mark.anyio
async def test_deterministic_dedicated_script_records_converted_search_path() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        prefix = dict(request.params)["first3"].strip('"')
        assert prefix == "$um"
        return _browse_response(prefix)

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("ࡔࡅࡌࡇ")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.NOT_FOUND
    assert _provenance_tuple(result, "cal_code_word_candidates") == (("$umH",),)
    assert _provenance_tuple(result, "cal_code_query_candidates") == ("$umH",)
    assert _provenance_tuple(result, "browse_prefixes") == ("$um",)
    assert _provenance_tuple(result, "selected_cal_code_candidates") == ()
    assert len(requests) == 1


@pytest.mark.anyio
async def test_legacy_syriac_search_records_prefix_without_conversion_candidates() -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        prefix = dict(request.params)["first3"].strip('"')
        assert prefix == "ܡܠܟ"
        return _browse_response(prefix)

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("ܡܠܟ")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.NOT_FOUND
    assert _provenance_tuple(result, "cal_code_word_candidates") == ()
    assert _provenance_tuple(result, "cal_code_query_candidates") == ()
    assert _provenance_tuple(result, "browse_prefixes") == ("ܡܠܟ",)
    assert _provenance_tuple(result, "selected_cal_code_candidates") == ()


@pytest.mark.anyio
async def test_serialized_provenance_has_stable_conversion_path_keys() -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        prefix = dict(request.params)["first3"].strip('"')
        return _browse_response(prefix)

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("שלם")
    finally:
        await client.aclose()

    payload = result.to_dict()
    provenance = cast(dict[str, object], payload["provenance"])
    assert provenance["cal_code_word_candidates"] == [["$lm", "&lm"]]
    assert provenance["cal_code_query_candidates"] == ["$lm", "&lm"]
    assert provenance["browse_prefixes"] == ["$lm", "&lm"]
    assert provenance["selected_cal_code_candidates"] == []
