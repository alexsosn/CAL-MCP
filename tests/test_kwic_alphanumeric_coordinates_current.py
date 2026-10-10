"""Issue #253: CAL's letter-bearing KWIC subtexts and target coordinates (R-074, D-023)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    ConcordanceService,
    parse_kwic_full_context_page,
)
from cal_mcp.errors import CalInputError

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
IMPERIAL = FIXTURES / "kwic_dialect_mlk_2_alphanumeric_current.html"
JAR = FIXTURES / "kwic_full_context_22352_12_alphanumeric_current.html"
CUSTOMS = FIXTURES / "kwic_full_context_23350_ar_letter_subtext_current.html"
IMPERIAL_URL = "https://cal.huc.edu/show1dialectKWIC.php?lemma=mlk&pos=N&texts=2"
RETRIEVED_AT = datetime(2026, 10, 10, tzinfo=UTC)


def _response(url: str, body: bytes) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _full_context_url(file_id: str, subtext_id: str, target: str) -> str:
    return (
        "https://cal.huc.edu/get_a_kwicchapter.php"
        f"?file={file_id}&sub={subtext_id}&cset=H&target={target}"
    )


class _Transport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


async def _imperial(body: bytes):
    client = CalHttpClient(transport=_Transport(_response(IMPERIAL_URL, body)))
    try:
        return await ConcordanceService(client).kwic_dialect("mlk N", "2")
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_imperial_dialect_kwic_preserves_letter_bearing_selectors() -> None:
    result = await _imperial(IMPERIAL.read_bytes())

    assert result.total == 4
    assert [(hit.file_id, hit.subtext_id, hit.target_coordinate) for hit in result.hits] == [
        ("20301", None, "2030101"),
        ("22352", "12", "2235212A1"),
        ("23350", "AR", "23350AR201"),
        ("27351", "C01", "27351C01R101"),
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new"),
    [
        # A letter-bearing target outside its own file + subtext prefix.
        (b"sub=AR&cset=H&target=23350AR201", b"sub=AR&cset=H&target=23351AR201"),
        (b"sub=AR&cset=H&target=23350AR201", b"sub=BR&cset=H&target=23350AR201"),
        # Punctuation, and a subtext longer than eight characters.
        (b"sub=AR&cset=H&target=23350AR201", b"sub=AR&cset=H&target=23350AR2-1"),
        (b"sub=C01&cset=H&target=27351C01R101", b"sub=C01C01C01&cset=H&target=27351C01R101"),
    ],
)
async def test_other_letter_bearing_shapes_still_fail_closed(old: bytes, new: bytes) -> None:
    body = IMPERIAL.read_bytes()
    assert old in body

    with pytest.raises(ConcordanceParseError):
        await _imperial(body.replace(old, new))


@pytest.mark.parametrize(
    ("fixture", "file_id", "subtext_id", "target", "coordinates", "displays"),
    [
        (
            JAR,
            "22352",
            "12",
            "2235212A1",
            ["2235211A1", "2235212A1", "2235213A1"],
            ["11A1", "12A1", "13A1"],
        ),
        (
            CUSTOMS,
            "23350",
            "AR",
            "23350AR201",
            ["23350AR201", "23350AR202"],
            ["A.R2:01", "A.R2:02"],
        ),
    ],
)
def test_full_context_pages_keep_letter_bearing_row_coordinates(
    fixture: Path,
    file_id: str,
    subtext_id: str,
    target: str,
    coordinates: list[str],
    displays: list[str],
) -> None:
    page = parse_kwic_full_context_page(
        _response(_full_context_url(file_id, subtext_id, target), fixture.read_bytes()),
        requested_file_id=file_id,
        requested_subtext_id=subtext_id,
        requested_target_coordinate=target,
        requested_charset="H",
    )

    assert page.status.value == "found"
    assert [line.coordinate for line in page.lines] == coordinates
    assert [line.display_coordinate for line in page.lines] == displays


def test_full_context_row_coordinate_from_another_file_is_drift() -> None:
    body = CUSTOMS.read_bytes().replace(b"coord=23350AR202", b"coord=23351AR202")

    with pytest.raises(ConcordanceParseError):
        parse_kwic_full_context_page(
            _response(_full_context_url("23350", "AR", "23350AR201"), body),
            requested_file_id="23350",
            requested_subtext_id="AR",
            requested_target_coordinate="23350AR201",
            requested_charset="H",
        )


@pytest.mark.anyio
async def test_full_context_service_accepts_returned_letter_selectors() -> None:
    transport = _Transport(
        _response(_full_context_url("23350", "AR", "23350AR201"), CUSTOMS.read_bytes())
    )
    client = CalHttpClient(transport=transport)
    try:
        result = await ConcordanceService(client).kwic_full_context(
            "23350", "23350AR201", "H", subtext_id="AR"
        )
    finally:
        await client.aclose()

    assert result.target_coordinate == "23350AR201"
    assert result.subtext_id == "AR"
    assert dict(transport.requests[0].params) == {
        "file": "23350",
        "sub": "AR",
        "cset": "H",
        "target": "23350AR201",
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("target", "subtext_id"),
    [("23350AR201", "BR"), ("23351AR201", "AR"), ("23350AR2:01", "AR"), ("23350", "AR")],
)
async def test_full_context_service_rejects_unbound_letter_targets_before_transport(
    target: str, subtext_id: str
) -> None:
    transport = _Transport(
        _response(_full_context_url("23350", "AR", "23350AR201"), CUSTOMS.read_bytes())
    )
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(CalInputError):
            await ConcordanceService(client).kwic_full_context(
                "23350", target, "H", subtext_id=subtext_id
            )
    finally:
        await client.aclose()
    assert transport.requests == []


MISSING = FIXTURES / "kwic_full_context_23350_ar_not_found_current.html"


def test_missing_letter_bearing_target_is_typed_not_found() -> None:
    page = parse_kwic_full_context_page(
        _response(_full_context_url("23350", "AR", "23350AR999"), MISSING.read_bytes()),
        requested_file_id="23350",
        requested_subtext_id="AR",
        requested_target_coordinate="23350AR999",
        requested_charset="H",
    )

    assert page.status.value == "not_found"
    assert page.lines == ()


def test_not_found_marker_naming_another_letter_target_is_drift() -> None:
    with pytest.raises(ConcordanceParseError, match="not-found target differs"):
        parse_kwic_full_context_page(
            _response(_full_context_url("23350", "AR", "23350AR998"), MISSING.read_bytes()),
            requested_file_id="23350",
            requested_subtext_id="AR",
            requested_target_coordinate="23350AR998",
            requested_charset="H",
        )


def test_full_context_lexical_coordinate_from_another_file_is_drift() -> None:
    # The JAR rows carry no comment links, so only the lexical-coordinate check can catch this.
    body = JAR.read_bytes().replace(b"getlex.php?coord=2235213A1", b"getlex.php?coord=9999913A1")

    with pytest.raises(ConcordanceParseError, match="unsupported coordinate"):
        parse_kwic_full_context_page(
            _response(_full_context_url("22352", "12", "2235212A1"), body),
            requested_file_id="22352",
            requested_subtext_id="12",
            requested_target_coordinate="2235212A1",
            requested_charset="H",
        )


@pytest.mark.anyio
async def test_nine_character_subtext_with_a_consistent_target_is_drift() -> None:
    body = IMPERIAL.read_bytes().replace(
        b"sub=C01&cset=H&target=27351C01R101", b"sub=C01C01C01&cset=H&target=27351C01C01C01R1"
    )

    with pytest.raises(ConcordanceParseError, match="subtext_id"):
        await _imperial(body)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("target", "subtext_id"),
    [
        # Exactly the file + subtext prefix, with no coordinate tail.
        ("23350AR", "AR"),
        # Longer than the 32-character coordinate ceiling.
        ("23350AR" + "1" * 26, "AR"),
        ("2" * 33, None),
    ],
)
async def test_full_context_service_rejects_bare_prefix_and_overlong_targets(
    target: str, subtext_id: str | None
) -> None:
    transport = _Transport(
        _response(_full_context_url("23350", "AR", "23350AR201"), CUSTOMS.read_bytes())
    )
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(CalInputError):
            await ConcordanceService(client).kwic_full_context(
                "23350" if subtext_id else "2222", target, "H", subtext_id=subtext_id
            )
    finally:
        await client.aclose()
    assert transport.requests == []
