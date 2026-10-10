"""Current CAL browse no-headwords wording must be a true empty result (#252)."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlencode

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import (
    LexiconLookupService,
    LexiconLookupStatus,
    LexiconParseError,
    parse_browse_page,
)
from cal_mcp.lexicon_browse import LexiconBrowseService, parse_lexicon_browse_page

_NOW = datetime(2026, 10, 10, 17, 45, tzinfo=UTC)


def _empty(prefix: str) -> str:
    # Reduced source-shape fixture from CAL browseSKEYheaders.php?first3="qqq"
    return (
        "<html><body><table><tr><td>"
        f"There are no headwords beginning with: {prefix}"
        "</td></tr></table></body></html>"
    )


def _response(content: str, *, prefix: str = "qqq", url: str | None = None) -> CalResponse:
    source = url or (
        "https://cal.huc.edu/browseSKEYheaders.php?"
        + urlencode({"first3": f'"{prefix}"'})
    )
    return CalResponse(
        status_code=200,
        url=source,
        body=content.encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_NOW,
    )


def test_current_explicit_marker_means_empty_lookup_browse_page() -> None:
    page = parse_browse_page(_response(_empty("qqq")))
    assert page.entries == ()


def test_current_explicit_marker_means_empty_public_browse_page() -> None:
    page = parse_lexicon_browse_page(_response(_empty("qqq")))
    assert page.rows == ()
    assert page.entries == ()
    assert page.next_continuation is None


@pytest.mark.parametrize(
    "body",
    [
        "<html><body>unexpected replacement page</body></html>",
        "<html><body>There are almost no headwords beginning with: qqq</body></html>",
        "<html><body>There are no headwords beginning with:</body></html>",
    ],
)
def test_unknown_or_incomplete_page_stays_parser_drift(body: str) -> None:
    for parser in (parse_browse_page, parse_lexicon_browse_page):
        with pytest.raises(LexiconParseError):
            parser(_response(body))


class _NoHeadwordsTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        assert request.path == "browseSKEYheaders.php"
        prefix = dict(request.params)["first3"].strip('"')
        return _response(_empty(prefix), prefix=prefix)


@pytest.mark.anyio
async def test_lookup_current_empty_page_returns_not_found_with_provenance() -> None:
    transport = _NoHeadwordsTransport()
    result = await LexiconLookupService(CalHttpClient(transport=transport)).lookup("qqqqzz")
    assert result.status is LexiconLookupStatus.NOT_FOUND
    assert result.entry is None
    assert result.matches == ()
    assert result.provenance is not None
    assert result.provenance.source == "CAL"
    assert result.provenance.source_url.startswith("https://cal.huc.edu/browseSKEYheaders.php?")
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("first3", '"qqq"'),),
        )
    ]


@pytest.mark.anyio
async def test_public_browse_current_empty_page_returns_no_continuation() -> None:
    transport = _NoHeadwordsTransport()
    result = await LexiconBrowseService(CalHttpClient(transport=transport)).browse("qqq")
    assert result.rows == ()
    assert result.entries == ()
    assert result.next_continuation is None
    assert len(transport.requests) == 1


@pytest.mark.anyio
async def test_bare_hebrew_shin_ignores_empty_sin_prefix_and_keeps_shin_candidate() -> None:
    class HebrewTransport:
        def __init__(self) -> None:
            self.requests: list[CalRequest] = []

        async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
            del config
            self.requests.append(request)
            if request.path == "browseSKEYheaders.php":
                prefix = dict(request.params)["first3"].strip('"')
                if prefix == "$lm":
                    return _response(
                        '<html><body><div><a href="/oneentry.php?cits=all&amp;lemma=%24lm+N">'
                        "šlm n.m.</a></div><div>peace</div></body></html>",
                        prefix=prefix,
                    )
                assert prefix == "&lm"
                return _response(_empty(prefix), prefix=prefix)
            assert request.path == "cal_entry_web.php"
            assert request.params == (("lemma", "$lm N"),)
            return _response(
                "<html><body><header>šlm n.m. peace</header>"
                "<div>1</div><div>peace</div><div>Common Aramaic</div>"
                "</body></html>",
                url="https://cal.huc.edu/cal_entry_web.php?lemma=%24lm+N",
            )

    transport = HebrewTransport()
    result = await LexiconLookupService(CalHttpClient(transport=transport)).lookup("שלם")
    assert result.status is LexiconLookupStatus.FOUND
    assert result.entry is not None
    assert result.entry.lemma.lemma_key == "$lm N"
    assert result.provenance is not None
    assert result.provenance.browse_prefixes == ("$lm", "&lm")
    assert result.provenance.selected_cal_code_candidates == ("$lm",)
    assert [request.path for request in transport.requests] == [
        "browseSKEYheaders.php",
        "browseSKEYheaders.php",
        "cal_entry_web.php",
    ]
