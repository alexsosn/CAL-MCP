"""Issue #252: CAL's current explicit "no headwords beginning with" browse page is a no-match."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import (
    LexiconLookupService,
    LexiconLookupStatus,
    LexiconParseError,
    parse_browse_page,
)
from cal_mcp.lexicon_browse import LexiconBrowseService, parse_lexicon_browse_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 10, 10, 17, 0, tzinfo=UTC)
_FIXTURE_BY_PREFIX = {
    "qqq": "browse_no_headwords_qqq_current.html",
    "&lm": "browse_no_headwords_amp_lm_current.html",
    # CAL echoes Hebrew/Syriac prefixes in CAL code (`qqq`).
    "קקק": "browse_no_headwords_hebrew_qof_current.html",
    "ܩܩܩ": "browse_no_headwords_syriac_qof_current.html",
}
_PARSERS = [parse_browse_page, parse_lexicon_browse_page]


def _url(prefix: str) -> str:
    return "https://cal.huc.edu/browseSKEYheaders.php?first3=" + quote(f'"{prefix}"', safe="")


def _no_headwords_response(prefix: str, *, body: str | None = None) -> CalResponse:
    if body is None:
        body = (FIXTURES / _FIXTURE_BY_PREFIX[prefix]).read_text(encoding="utf-8")
    return CalResponse(
        status_code=200,
        url=_url(prefix),
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _entries_response(prefix: str, lemma_key: str, headword: str) -> CalResponse:
    body = (
        "<html><body>"
        f'<div><a href="/oneentry.php?lemma={quote(lemma_key)}">{headword} n.m.</a></div>'
        "<div>test gloss</div></body></html>"
    )
    return CalResponse(
        status_code=200,
        url=_url(prefix),
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


@pytest.mark.parametrize("parser", _PARSERS)
@pytest.mark.parametrize("prefix", sorted(_FIXTURE_BY_PREFIX))
def test_current_no_headwords_page_is_an_explicit_no_match(parser: object, prefix: str) -> None:
    page = parser(_no_headwords_response(prefix))  # type: ignore[operator]

    assert page.entries == ()


def test_public_browse_no_headwords_page_has_no_rows_or_continuation() -> None:
    page = parse_lexicon_browse_page(_no_headwords_response("qqq"))

    assert page.rows == ()
    assert page.next_continuation is None


@pytest.mark.parametrize("parser", _PARSERS)
def test_no_headwords_marker_naming_another_prefix_is_drift(parser: object) -> None:
    body = (FIXTURES / _FIXTURE_BY_PREFIX["qqq"]).read_text(encoding="utf-8")
    response = _no_headwords_response("mlk", body=body)

    with pytest.raises(LexiconParseError, match="requested prefix"):
        parser(response)  # type: ignore[operator]


@pytest.mark.parametrize("parser", _PARSERS)
@pytest.mark.parametrize("prefix", ["מלכ", "ש"])
def test_script_prefix_marker_must_echo_its_one_deterministic_cal_code(
    parser: object, prefix: str
) -> None:
    body = (FIXTURES / _FIXTURE_BY_PREFIX["qqq"]).read_text(encoding="utf-8")
    response = _no_headwords_response(prefix, body=body)

    with pytest.raises(LexiconParseError, match="requested prefix"):
        parser(response)  # type: ignore[operator]


@pytest.mark.anyio
async def test_hebrew_lookup_without_headwords_is_not_found() -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        prefix = dict(request.params)["first3"].strip('"')
        return _no_headwords_response(prefix)

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("קקקא")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.NOT_FOUND


@pytest.mark.parametrize("parser", _PARSERS)
def test_page_without_rows_or_any_marker_is_still_drift(parser: object) -> None:
    body = (FIXTURES / _FIXTURE_BY_PREFIX["qqq"]).read_text(encoding="utf-8")
    body = body.replace("There are no headwords beginning with: qqq", "")

    with pytest.raises(LexiconParseError, match="neither"):
        parser(_no_headwords_response("qqq", body=body))  # type: ignore[operator]


@pytest.mark.parametrize("parser", _PARSERS)
def test_no_headwords_marker_beside_entries_is_drift(parser: object) -> None:
    body = (FIXTURES / _FIXTURE_BY_PREFIX["qqq"]).read_text(encoding="utf-8")
    body = body.replace(
        "</body>",
        '<div><a href="/oneentry.php?lemma=qqq%20N">qqq n.m.</a></div><div>gloss</div></body>',
    )

    with pytest.raises(LexiconParseError, match="no-headwords"):
        parser(_no_headwords_response("qqq", body=body))  # type: ignore[operator]


@pytest.mark.anyio
async def test_lookup_with_only_no_headwords_prefix_is_not_found() -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        prefix = dict(request.params)["first3"].strip('"')
        assert prefix == "qqq"
        return _no_headwords_response(prefix)

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("qqqqzz")
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.NOT_FOUND
    assert result.matches == ()
    assert result.provenance.source_url == _url("qqq")


@pytest.mark.anyio
async def test_bare_hebrew_shin_lookup_resolves_when_sin_prefix_has_no_headwords() -> None:
    requests: list[str] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        if request.path != "browseSKEYheaders.php":
            return CalResponse(
                status_code=200,
                url="https://cal.huc.edu/cal_entry_web.php?lemma=%24lm+N",
                body=(
                    "<html><body><div>šlm n.m. peace</div>"
                    "<div>1.</div><div>peace</div></body></html>"
                ).encode(),
                content_type="text/html; charset=UTF-8",
                retrieved_at=RETRIEVED_AT,
            )
        prefix = dict(request.params)["first3"].strip('"')
        requests.append(prefix)
        if prefix == "$lm":
            return _entries_response(prefix, "$lm N", "šlm")
        if prefix == "&lm":
            return _no_headwords_response(prefix)
        raise AssertionError(f"unexpected CAL browse prefix: {prefix}")

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup("שלם")
    finally:
        await client.aclose()

    assert requests == ["$lm", "&lm"]
    assert result.status is LexiconLookupStatus.FOUND
    assert [item.lemma_key for item in result.matches] == ["$lm N"]


@pytest.mark.anyio
async def test_public_browse_service_returns_empty_page_for_no_headwords() -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        assert dict(request.params)["first3"] == '"qqq"'
        return _no_headwords_response("qqq")

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconBrowseService(client).browse("qqq")
    finally:
        await client.aclose()

    assert result.rows == ()
    assert result.next_continuation is None
