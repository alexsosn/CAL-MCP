"""Issue #155: CAL verse labels are presentation metadata, not MT text."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.syriac import SyriacParseError, parse_syriac_peshitta_page
from cal_mcp.targum import TargumParseError, parse_targum_parallel_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _response(body: str, *, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 8, tzinfo=UTC),
    )


def test_targum_current_mt_text_excludes_repeated_psalm_coordinate() -> None:
    page = parse_targum_parallel_page(
        _response(
            _fixture("targum_parallel_ps_23_1_current.html"),
            url="https://cal.huc.edu/showtargum.php",
        ),
        book="Psalms",
        chapter=23,
        verse=1,
    )

    assert page.mt_text == "מִזְמוֹר לְדָוִד יְהוָה רֹעִי לֹא אֶחְסָר׃"
    assert "Ps 23:1" not in page.mt_text


def test_peshitta_current_multiline_mt_text_excludes_repeated_coordinate() -> None:
    page = parse_syriac_peshitta_page(
        _response(
            _fixture("syriac_peshitta_gen_1_1.html"),
            url="https://cal.huc.edu/showpesh.php",
        ),
        book="Gen",
        chapter=1,
        verse=1,
    )

    assert page.mt_text == (
        "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ"
    )
    assert "Gen 1:1" not in page.mt_text


def test_peshitta_current_psalm_mt_text_excludes_coordinate() -> None:
    page = parse_syriac_peshitta_page(
        _response(
            _fixture("syriac_peshitta_ps_23_1_current.html"),
            url="https://cal.huc.edu/showpesh.php",
        ),
        book="Psalms",
        chapter=23,
        verse=1,
    )

    assert page.mt_text == "מִזְמוֹר לְדָוִד יְהוָה רֹעִי לֹא אֶחְסָר׃"
    assert "Ps 23:1" not in page.mt_text


def test_legacy_clean_targum_mt_text_stays_unchanged() -> None:
    page = parse_targum_parallel_page(
        _response(
            _fixture("targum_parallel_gen_1_1.html"),
            url="https://cal.huc.edu/showtargum.php",
        ),
        book="Gen",
        chapter=1,
        verse=1,
    )

    assert page.mt_text == "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ"


def _targum_html(mt: str) -> str:
    return (
        "<html><body>"
        "<h1>MT and targums for Gen 1:1</h1>"
        f'<div class="targum-block"><span class="heb">{mt}</span></div>'
        '<div class="targum-block">Onqelos:<br>'
        '<span class="heb">בקדמין ברא</span></div>'
        "</body></html>"
    )


def _peshitta_html(mt: str) -> str:
    return (
        "<html><body>"
        "<center>MT and Peshitta for Gen 1:1</center>"
        f'<div><span class="heb">{mt}</span></div>'
        '<div><a href="/get_a_chapter.php?file=62001&sub=01&cset=U">Peshitta:</a>'
        '<br><span class="syr">ܒܪܫܝܬ ܒܪܐ</span></div>'
        "</body></html>"
    )


ParserCase = tuple[Callable[[str], str], type[Exception]]


def _parse_targum(body: str) -> str:
    page = parse_targum_parallel_page(
        _response(body, url="https://cal.huc.edu/showtargum.php"),
        book="Gen",
        chapter=1,
        verse=1,
    )
    assert page.mt_text is not None
    return page.mt_text


def _parse_peshitta(body: str) -> str:
    page = parse_syriac_peshitta_page(
        _response(body, url="https://cal.huc.edu/showpesh.php"),
        book="Gen",
        chapter=1,
        verse=1,
    )
    assert page.mt_text is not None
    return page.mt_text


@pytest.mark.parametrize(
    ("build", "parse", "error"),
    [
        (_targum_html, _parse_targum, TargumParseError),
        (_peshitta_html, _parse_peshitta, SyriacParseError),
    ],
    ids=["targum", "peshitta"],
)
@pytest.mark.parametrize(
    "mt",
    [
        "בְּרֵאשִׁית Gen 1:1<br>וְאֵת הָאָרֶץ",
        "בְּרֵאשִׁית Gen 1:2<br>",
        "בְּרֵאשִׁית Gen 1:1<br>Gen 1:1<br>",
        "בְּרֵאשִׁית Gen 1:1 extra<br>",
    ],
    ids=[
        "mixed-labeled-unlabeled",
        "wrong-coordinate",
        "coordinate-only-line",
        "embedded-coordinate",
    ],
)
def test_parallel_mt_coordinate_drift_fails_closed(
    build: Callable[[str], str],
    parse: Callable[[str], str],
    error: type[Exception],
    mt: str,
) -> None:
    with pytest.raises(error):
        parse(build(mt))
