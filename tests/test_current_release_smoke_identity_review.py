"""Issue #330 independent release-smoke review: verify recent CAL source identity.

The synthetic payloads contain no CAL data or network access.
"""

from __future__ import annotations

import pytest

from cal_mcp.stdio_live_smoke import _has_representative_content

RECENT_URL = "https://cal.huc.edu/getrecentbib.php"


def _payload(heading: str, source_url: str, operation: str) -> dict[str, object]:
    return {
        "heading": heading,
        "records": [{"citation": "one recognized reference"}],
        "provenance": {"source_url": source_url, "operation": operation},
    }


@pytest.mark.parametrize(
    ("heading", "source_url", "operation"),
    [
        ("CAL Bibliography for TADA", RECENT_URL, "bibliography_recent"),
        (
            "CAL Recent Bibliography",
            "https://cal.huc.edu/getbiblemma.php?myauthor=cly+V",
            "bibliography_recent",
        ),
        ("CAL Recent Bibliography", RECENT_URL, "bibliography_lemma"),
        ("CAL Recent Bibliography", "", "bibliography_recent"),
    ],
)
def test_recent_smoke_rejects_plausible_records_from_wrong_cal_surface(
    heading: str, source_url: str, operation: str
) -> None:
    assert not _has_representative_content(
        "recent_bibliography", _payload(heading, source_url, operation)
    )


def test_recent_smoke_accepts_exact_cal_heading_url_and_operation() -> None:
    assert _has_representative_content(
        "recent_bibliography",
        _payload("CAL Recent Bibliography", RECENT_URL, "bibliography_recent"),
    )
