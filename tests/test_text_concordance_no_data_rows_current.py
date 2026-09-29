from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    ConcordanceProvenance,
    KwicScopeKind,
    TextConcordanceResult,
    parse_kwic_result,
    parse_text_concordance_page,
)
from cal_mcp.errors import CalInputError
from cal_mcp.lemma_key import validate_lemma_key

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
SOURCE_URL = "https://cal.huc.edu/newconcord.php?text=41201&cset=S"
KWIC = "https://cal.huc.edu/showKWIC.php?lemma={}&charset=S&texts=41201"


def _response(body: bytes) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=SOURCE_URL,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
    )


def _fixture() -> bytes:
    return (FIXTURES / "text_concordance_41201_no_data_current.html").read_bytes()


def _parse(body: bytes):
    return parse_text_concordance_page(
        _response(body), requested_text_id="41201", requested_charset="S"
    )


def test_no_data_rows_are_kept_in_cal_order_with_nullable_keys() -> None:
    page = _parse(_fixture())

    assert [
        (item.frequency, item.lemma_key, item.label, item.gloss, item.cal_reports_no_data)
        for item in page.lemmas
    ] == [
        (1, None, "snqly+ws N", "no data found for  snqly+ws N", True),
        (20, ")b N", "ˀb, ˀbˀ n.m.", "father", False),
        (1, "z(yd N", "z(yd N", "no data found for z(yd N", True),
        (1, None, "qrb", "no data found for qrb", True),
        (1, None, "430 b", "no data found for 430 b", True),
        (3, ")b) PN", ")b) PN", "proper noun", False),
        (1, "bwlbrK PN", "bwlbrK PN", "proper noun", False),
        (1, "$lMn) PN", "$lMn) PN", "proper noun", False),
    ]
    assert [item.kwic_url for item in page.lemmas] == [
        KWIC.format("+snqlyTws+N"),
        KWIC.format("%29b+N"),
        KWIC.format("z%28yd+N"),
        KWIC.format("qrb+"),
        KWIC.format("430+n"),
        KWIC.format("%29b%29+PN"),
        KWIC.format("bwlbrK+PN"),
        KWIC.format("%24lMn%29+PN"),
    ]


def test_public_result_serializes_null_key_and_no_data_flag() -> None:
    page = _parse(_fixture())
    result = TextConcordanceResult(
        text_id="41201",
        script="semitic",
        lemmas=page.lemmas,
        provenance=ConcordanceProvenance(
            source="CAL",
            source_url=SOURCE_URL,
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
            operation="text_concordance",
            text_id="41201",
        ),
    )

    lemmas = result.to_dict()["lemmas"]
    assert isinstance(lemmas, list)
    assert lemmas[0]["lemma_key"] is None
    assert lemmas[0]["cal_reports_no_data"] is True
    assert lemmas[1]["lemma_key"] == ")b N"
    assert lemmas[1]["cal_reports_no_data"] is False


def test_invalid_key_on_a_normal_row_still_fails_closed() -> None:
    body = _fixture().replace(
        b"no data found for  snqly+ws N<br>", b"a gloss CAL did not mark as empty<br>"
    )

    with pytest.raises(ConcordanceParseError):
        _parse(body)


def test_no_data_marker_naming_another_label_fails_closed() -> None:
    body = _fixture().replace(b"no data found for qrb <br>", b"no data found for xyz<br>")

    with pytest.raises(ConcordanceParseError):
        _parse(body)


def test_no_data_row_link_must_still_match_the_request() -> None:
    body = _fixture().replace(
        b"lemma=qrb+&charset=S&texts=41201", b"lemma=qrb+&charset=S&texts=41202"
    )

    with pytest.raises(ConcordanceParseError):
        _parse(body)


@pytest.mark.parametrize("key", ["bwlbrK PN", "$lMn) PN"])
def test_cal_capital_letter_keys_are_accepted_verbatim(key: str) -> None:
    assert validate_lemma_key(key)[2] == key


@pytest.mark.parametrize("key", ["bwlbr1 PN", "bwlbré PN", "bwl\u212a PN"])
def test_lemma_keys_still_reject_digits_and_non_ascii_letters(key: str) -> None:
    with pytest.raises(CalInputError):
        validate_lemma_key(key)


def test_kwic_for_a_capital_letter_key_round_trips() -> None:
    response = CalResponse(
        status_code=200,
        url=KWIC.format("bwlbrK+PN"),
        body=(FIXTURES / "kwic_texts_bwlbrK_41201_current.html").read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 29, tzinfo=UTC),
    )

    page = parse_kwic_result(
        response,
        lemma_key="bwlbrK PN",
        scope_kind=KwicScopeKind.TEXTS,
        scope_ids=("41201",),
    )

    assert page.total == 1
    assert [hit.target_coordinate for hit in page.hits] == ["412012251002"]
