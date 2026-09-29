from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

import pytest

from cal_mcp.bibliography import BibliographyService
from cal_mcp.client import CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    ConcordanceProvenance,
    ConcordanceService,
    TextConcordanceResult,
    parse_text_concordance_page,
)
from cal_mcp.errors import CalInputError

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
        (1, None, "snqly+ws N", "no data found for snqly+ws N", True),
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


@pytest.mark.anyio
@pytest.mark.parametrize("key", ["bwlbrK PN", "$lMn) PN"])
async def test_capital_letter_keys_are_rejected_as_kwic_input_with_guidance(key: str) -> None:
    client = _NoRequestClient()

    with pytest.raises(CalInputError, match="kwic_url of the cal_text_concordance row"):
        await ConcordanceService(client).kwic_texts(key, ["41201"])  # type: ignore[arg-type]
    assert client.requests == 0


@pytest.mark.parametrize("key", ["bwlbr1 PN", "bwlbré PN", "bwl\u212a PN"])
def test_concordance_rows_still_reject_digits_and_non_ascii_letters(key: str) -> None:
    href = "/showKWIC.php?" + urlencode({"lemma": key, "charset": "S", "texts": "41201"})
    body = _fixture().replace(b"/showKWIC.php?lemma=bwlbrK+PN&charset=S&texts=41201", href.encode())

    with pytest.raises(ConcordanceParseError):
        _parse(body)


class _NoRequestClient:
    def __init__(self) -> None:
        self.requests = 0

    async def fetch(self, *args: object, **kwargs: object) -> object:
        self.requests += 1
        raise AssertionError("no CAL request expected")


@pytest.mark.parametrize("key", ["NAME PN", "BAD N", "bwlbrQ PN", "KM PN"])
def test_only_observed_cal_capitals_inside_lower_case_keys_are_accepted(key: str) -> None:
    href = "/showKWIC.php?" + urlencode({"lemma": key, "charset": "S", "texts": "41201"})
    body = _fixture().replace(b"/showKWIC.php?lemma=bwlbrK+PN&charset=S&texts=41201", href.encode())

    with pytest.raises(ConcordanceParseError):
        _parse(body)


@pytest.mark.anyio
async def test_non_kwic_tools_reject_capital_keys_without_kwic_guidance() -> None:
    client = _NoRequestClient()

    with pytest.raises(CalInputError) as caught:
        await BibliographyService(client).lemma("bwlbrK PN")  # type: ignore[arg-type]
    assert "capital letter" in str(caught.value)
    assert "kwic_url" not in str(caught.value)
    assert client.requests == 0


def test_table_layout_no_data_row_is_kept_with_null_key() -> None:
    body = (
        b"<html><body><div>Frequencies of lemmas in text 41201</div><table>"
        b'<tr><td>1:</td><td><a href="/showKWIC.php?lemma=qrb+&charset=S&texts=41201">qrb </a>'
        b"</td><td>: no data found for qrb </td></tr>"
        b'<tr><td>20:</td><td><a href="/showKWIC.php?lemma=%29b+N&charset=S&texts=41201">)b N</a>'
        b"</td><td>: father</td></tr></table></body></html>"
    )

    page = _parse(body)

    assert [(item.lemma_key, item.label, item.cal_reports_no_data) for item in page.lemmas] == [
        (None, "qrb", True),
        (")b N", ")b N", False),
    ]
