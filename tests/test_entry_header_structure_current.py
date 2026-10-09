from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import LexiconParseError, parse_lexicon_entry

_FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "entry_lemma_headers_current.txt"
# Verbatim div.lemma-header lines from current exact entries (see the fixture's provenance comment).
_HEADERS = dict(
    line.split("\t", 1)
    for line in _FIXTURE.read_text(encoding="utf-8").splitlines()
    if "\t" in line
)

# Minimal synthetic sense lines so that only the header decides the outcome.
_SENSES = "<div>1</div><div>sense text</div><div>Syriac</div>"


def _entry(header: str, lemma_key: str) -> object:
    return parse_lexicon_entry(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/cal_entry_web.php",
            body=f"<html><body>{header}{_SENSES}</body></html>".encode(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 9, tzinfo=UTC),
        ),
        lemma_key=lemma_key,
    )


@pytest.mark.parametrize(
    ("lemma_key", "headwords", "pronunciation", "part_of_speech", "gloss"),
    [
        ("mlk N", ("mlk", "mlkˀ"), "mleḵ, malkā", "n.m.", "king"),
        (")mr V", ("ˀmr",), "a/a", "vb.", "to say"),
        ("(hr A", ("ˁhr",), "ˁāhar", "adj.", "lustful"),
        ("tly N", ("tly", "tlyˀ"), "tlāy, tlāyā", "v.n.", "suspension"),
        ("$lh N", ("šlh",), None, "n.f.?", "watering(?)"),
        ("$yp#2 N", ("šyp", "šypˀ"), None, None, "a type of marsh reed"),
    ],
    ids=[c for c in ("noun", "verb", "adjective", "verbal-noun", "uncertain-pos", "no-pos")],
)
def test_current_entry_header_fields_are_read_structurally(
    lemma_key: str,
    headwords: tuple[str, ...],
    pronunciation: str | None,
    part_of_speech: str | None,
    gloss: str,
) -> None:
    lemma = _entry(_HEADERS[lemma_key], lemma_key).lemma  # type: ignore[attr-defined]

    assert (lemma.headwords, lemma.pronunciation, lemma.part_of_speech, lemma.gloss) == (
        headwords,
        pronunciation,
        part_of_speech,
        gloss,
    )
    assert lemma.lemma_key == lemma_key


_NOUN = _HEADERS["mlk N"]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        # An unknown span inside the header block.
        (
            '<span class="lemma-gloss">',
            '<span class="lemma-extra">x</span> <span class="lemma-gloss">',
        ),
        # Stray rendered text directly inside the block.
        ('<span class="lemma-gloss">', 'stray <span class="lemma-gloss">'),
        # No gloss span.
        ('<span class="lemma-gloss"><b>king</b></span>', ""),
        # Two POS spans.
        (
            '<span class="lemma-pos">n.m.</span>',
            '<span class="lemma-pos">n.m.</span> <span class="lemma-pos">n.f.</span>',
        ),
        # An empty POS span is not CAL's "no POS" (that is an absent span).
        ('<span class="lemma-pos">n.m.</span>', '<span class="lemma-pos"></span>'),
        # A vocalization that is not one parenthesized group.
        ("(mleḵ, malkā)", "mleḵ, malkā"),
        # Empty headwords.
        ("<b>mlk, mlkˀ</b>", "<b> </b>"),
    ],
    ids=[
        "unknown-span",
        "stray-text",
        "missing-gloss",
        "duplicate-pos",
        "empty-pos",
        "unparenthesized-vocalization",
        "empty-headwords",
    ],
)
def test_current_header_shape_drift_fails_closed(old: str, new: str) -> None:
    assert old in _NOUN
    with pytest.raises(LexiconParseError):
        _entry(_NOUN.replace(old, new, 1), "mlk N")


def test_older_layout_without_a_header_first_line_fails_closed() -> None:
    # #224: prose before any header must not let later header-looking prose become the lemma.
    body = (
        "<html><body><div>See DNWSI 17 for other suggestions. Compare CPA šlyh.</div>"
        "<div>šlh n.f. watering</div>" + _SENSES + "</body></html>"
    )
    with pytest.raises(LexiconParseError):
        parse_lexicon_entry(
            CalResponse(
                status_code=200,
                url="https://cal.huc.edu/cal_entry_web.php",
                body=body.encode(),
                content_type="text/html; charset=UTF-8",
                retrieved_at=datetime(2026, 10, 9, tzinfo=UTC),
            ),
            lemma_key="$lh N",
        )
