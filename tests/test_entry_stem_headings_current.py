from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import LexiconParseError, parse_lexicon_entry

_FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "entry_stem_headers_current.txt"
# Verbatim div.stem-header elements, in page order per lemma (see the fixture's provenance).
_STEMS: dict[str, list[str]] = {}
for _line in _FIXTURE.read_text(encoding="utf-8").splitlines():
    if "\t" in _line:
        _key, _element = _line.split("\t", 1)
        _STEMS.setdefault(_key, []).append(_element)

# A minimal synthetic current header; the stem headers below are verbatim.
_HEADER = (
    '<div class="lemma-header"><span class="lemma-formal"><b>ktb</b></span> '
    '<span class="lemma-pos">vb.</span> <span class="lemma-gloss"><b>to write</b></span></div>'
    "<div>G D C Gt</div>"
)


def _numbered(count: int, label: str) -> str:
    return "".join(
        f"<div>{number}</div><div>{label} sense {number}</div><div>Syr</div>"
        for number in range(1, count + 1)
    )


def _entry(body: str) -> object:
    return parse_lexicon_entry(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/cal_entry_web.php?lemma=ktb+V",
            body=f"<html><body>{_HEADER}{body}</body></html>".encode(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 9, tzinfo=UTC),
        ),
        lemma_key="ktb V",
    )


def _ktb_body() -> str:
    g, d, c, gt = _STEMS["ktb V"]
    return (
        g
        + _numbered(2, "G")
        + d
        + "<div>D only sense</div><div>Syr</div>"
        + c
        + _numbered(3, "C")
        + gt
        + _numbered(2, "Gt")
    )


def test_current_stem_headings_are_read_structurally_for_every_sense() -> None:
    entry = _entry(_ktb_body())

    assert entry.grammar == ("G D C Gt",)  # type: ignore[attr-defined]
    assert [(s.heading, s.label_path, s.definition) for s in entry.senses] == [  # type: ignore[attr-defined]
        ("G pəˁal to write", (1,), "G sense 1"),
        ("G pəˁal to write", (2,), "G sense 2"),
        ("D paˁˁel to enroll, register : see s.v. kwtb", (), "D only sense"),
        ("C ˀafˁel to dictate", (1,), "C sense 1"),
        ("C ˀafˁel to dictate", (2,), "C sense 2"),
        ("C ˀafˁel to dictate", (3,), "C sense 3"),
        ("Gt ˀeṯpəˁel to be written", (1,), "Gt sense 1"),
        ("Gt ˀeṯpəˁel to be written", (2,), "Gt sense 2"),
    ]


def test_single_stem_verb_has_no_fabricated_sense() -> None:
    (g,) = _STEMS["(hr V"]
    entry = _entry(g + _numbered(2, "G"))

    assert [(s.heading, s.label_path) for s in entry.senses] == [  # type: ignore[attr-defined]
        ("G pəˁal (animals) to be sexually aroused. lustful", (1,)),
        ("G pəˁal (animals) to be sexually aroused. lustful", (2,)),
    ]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        # The declared count disagrees with the senses parsed for the stem.
        ('<span class="stem-count">3 senses</span>', '<span class="stem-count">4 senses</span>'),
        # An unknown span in the stem header.
        ('<span class="stem-name">ˀafˁel</span>', '<span class="stem-mood">x</span>'),
        # No stem label.
        ('<span class="stem-label">C</span>', ""),
        # A count that is not "N sense(s)".
        ('<span class="stem-count">3 senses</span>', '<span class="stem-count">three</span>'),
    ],
    ids=["count-mismatch", "unknown-span", "missing-label", "malformed-count"],
)
def test_stem_header_drift_fails_closed(old: str, new: str) -> None:
    body = _ktb_body()
    assert old in body
    with pytest.raises(LexiconParseError):
        _entry(body.replace(old, new, 1))
