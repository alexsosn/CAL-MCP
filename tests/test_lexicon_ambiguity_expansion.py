from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LexiconLookupService, LexiconLookupStatus


def _browse_response(prefix: str, *entries: tuple[str, str]) -> CalResponse:
    if entries:
        body = (
            "<html><body>"
            + "".join(
                f'<div><a href="/oneentry.php?lemma={lemma_key}">{headword} n.m.</a></div>'
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
        url=f"https://cal.huc.edu/cal_entry_web.php?lemma={lemma_key}",
        body=(
            "<html><body>"
            f"<div>{headword} n.m. selected gloss</div>"
            "<div>1.</div><div>selected sense</div>"
            "</body></html>"
        ).encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 7, tzinfo=UTC),
    )


@pytest.mark.anyio
async def test_bare_hebrew_shin_searches_both_cal_prefixes_and_aggregates_matches() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        assert request.path == "browseSKEYheaders.php"
        prefix = dict(request.params)["first3"].strip('"')
        if prefix == "$lm":
            return _browse_response(prefix, ("$lm N", "$lm"))
        if prefix == "&lm":
            return _browse_response(prefix, ("&lm N", "&lm"))
        raise AssertionError(f"unexpected CAL browse prefix: {prefix}")

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("שלם")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.AMBIGUOUS
    assert [item.lemma_key for item in result.matches] == ["$lm N", "&lm N"]
    assert [dict(request.params)["first3"] for request in requests] == ['"$lm"', '"&lm"']


@pytest.mark.anyio
async def test_ambiguity_after_browse_prefix_does_not_duplicate_request() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        assert request.path == "browseSKEYheaders.php"
        prefix = dict(request.params)["first3"].strip('"')
        assert prefix == "mlk"
        return _browse_response(
            prefix,
            ("mlk$ N", "mlk$"),
            ("mlk& N", "mlk&"),
        )

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("מלכש")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.AMBIGUOUS
    assert [item.lemma_key for item in result.matches] == ["mlk$ N", "mlk& N"]
    assert len(requests) == 1


@pytest.mark.anyio
async def test_ambiguous_encoding_fetches_only_one_entry_after_explicit_selection() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        if request.path == "browseSKEYheaders.php":
            prefix = dict(request.params)["first3"].strip('"')
            if prefix == "$lm":
                return _browse_response(prefix, ("$lm N", "$lm"))
            if prefix == "&lm":
                return _browse_response(prefix, ("&lm N", "&lm"))
            raise AssertionError(f"unexpected CAL browse prefix: {prefix}")
        if request.path == "cal_entry_web.php":
            lemma_key = dict(request.params)["lemma"]
            assert lemma_key == "&lm N"
            return _entry_response(lemma_key, "&lm")
        raise AssertionError(f"unexpected CAL path: {request.path}")

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("שלם", lemma_key="&lm N")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.FOUND
    assert result.entry is not None
    assert result.entry.lemma.lemma_key == "&lm N"
    assert [request.path for request in requests].count("browseSKEYheaders.php") == 2
    assert [request.path for request in requests].count("cal_entry_web.php") == 1
