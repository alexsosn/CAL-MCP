"""Issue #257: CAL backslash-escapes ``$`` and ``(`` when echoing a bibliography lemma key."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote_plus

import pytest

from cal_mcp.bibliography import BibliographyParseError, BibliographyService
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
AYIN = FIXTURES / "bibliography_lemma_ayin_escaped_current.html"
SHIN_EMPTY = FIXTURES / "bibliography_lemma_shin_escaped_empty_current.html"


async def _lemma(lemma_key: str, body: bytes, *, path: str = "getbiblemma.php"):
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        assert request.path == path
        assert dict(request.params) == {"myauthor": lemma_key}
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/{path}?myauthor={quote_plus(lemma_key)}",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        return await BibliographyService(client).lemma(lemma_key)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_ayin_key_with_escaped_echo_returns_cal_records() -> None:
    result = await _lemma("(bd V", AYIN.read_bytes())

    assert result.query == "(bd V"
    assert result.provenance.submitted_query == "(bd V"
    assert result.heading == "CAL Bibliography for \\(bd V"
    assert len(result.records) == 2
    assert result.records[0].citation.startswith("Greenfield, Jonas C.")


@pytest.mark.anyio
async def test_shin_key_with_escaped_no_data_echo_is_an_empty_result() -> None:
    result = await _lemma("$lm N", SHIN_EMPTY.read_bytes())

    assert result.query == "$lm N"
    assert result.records == ()


@pytest.mark.anyio
async def test_unescaped_echo_of_the_same_key_is_still_accepted() -> None:
    body = SHIN_EMPTY.read_bytes().replace(b"\\$lm N", b"$lm N")

    result = await _lemma("$lm N", body)

    assert result.records == ()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("key", "fixture", "old", "new"),
    [
        # Escaped echo of a different key.
        ("(bd V", AYIN, b"\\(bd V</h1>", b"\\(bd N</h1>"),
        # Escaping a character CAL does not escape.
        (
            "$lm N",
            SHIN_EMPTY,
            b"<h1>CAL Bibliography for \\$lm N",
            b"<h1>CAL Bibliography for \\$l\\m N",
        ),
        # Partly escaped heading against a fully escaped no-data marker.
        (
            "$lm N",
            SHIN_EMPTY,
            b"<h1>CAL Bibliography for \\$lm N",
            b"<h1>CAL Bibliography for $lm N",
        ),
    ],
)
async def test_other_echo_differences_still_fail_closed(
    key: str, fixture: Path, old: bytes, new: bytes
) -> None:
    body = fixture.read_bytes()
    assert old in body

    with pytest.raises(BibliographyParseError):
        await _lemma(key, body.replace(old, new))


@pytest.mark.anyio
async def test_escaped_echo_is_accepted_only_for_lemma_queries() -> None:
    # R-075 evidence covers getbiblemma.php only; the author route keeps the exact echo.
    body = SHIN_EMPTY.read_bytes()

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        assert request.path == "getbibauthor.php"
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/getbibauthor.php?myauthor=%24lm+N",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(BibliographyParseError, match="heading does not match"):
            await BibliographyService(client).author("$lm N")
    finally:
        await client.aclose()
