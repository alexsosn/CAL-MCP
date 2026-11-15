"""Safe offline invariants for a targeted, two-request CAL comment drift diagnostic."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from scripts.diagnose_cal_comment_343 import select_comment_coordinate, summarize_response

from cal_mcp.client import CalResponse

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _response(filename: str, coordinate: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/comment.php?coord={coordinate}",
        body=(FIXTURES / filename).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 10, tzinfo=UTC),
    )


def test_positive_comment_structural_summary_excludes_raw_content() -> None:
    response = _response("text_line_comments_pj_gen8_21.html", "8100110821")
    report = summarize_response(response, "8100110821")
    assert report["parse_status"] == "found"
    assert report["title_matches"] is True
    assert report["summary_cards"] == 1
    assert report["record_count"] == 2
    assert "וקבל" not in json.dumps(report, ensure_ascii=False)
    assert "source_text" not in report
    assert "body" not in report
    assert "html" not in report


def test_empty_comment_report_preserves_explicit_empty_state_without_raw_text() -> None:
    report = summarize_response(
        _response("text_line_comments_none.html", "999999999999"),
        "999999999999",
    )
    assert report["parse_status"] == "no_citations"
    assert report["empty_marker_count"] == 1
    assert report["record_count"] == 1
    assert report["parser_reason"] is None


def test_wrong_title_yields_only_an_allowlisted_reason() -> None:
    raw = _response("text_line_comments_none.html", "999999999999")
    altered = CalResponse(
        status_code=200,
        url=raw.url,
        body=raw.body.replace(b"999999999999</title>", b"111</title>", 1),
        content_type=raw.content_type,
        retrieved_at=raw.retrieved_at,
    )
    report = summarize_response(altered, "999999999999")
    assert report["parse_status"] == "drift"
    assert report["parser_reason"] == "title_identity"
    assert "CAL: citations" not in json.dumps(report)


def test_comment_selector_uses_only_exact_cal_returned_canonical_link() -> None:
    page = SimpleNamespace(
        lines=[
            SimpleNamespace(coordinate="1325001", comment_url=None),
            SimpleNamespace(
                coordinate="1325002",
                comment_url="https://cal.huc.edu/comment.php?coord=1325002",
            ),
        ]
    )
    assert select_comment_coordinate(page) == "1325002"


def test_selector_never_falls_back_to_a_line_without_a_comment_url() -> None:
    page = SimpleNamespace(
        lines=[SimpleNamespace(coordinate="1325001", comment_url=None)]
    )
    assert select_comment_coordinate(page) is None


def test_selector_rejects_external_or_modified_comment_urls() -> None:
    for url in (
        "https://evil.example/comment.php?coord=1325002",
        "http://cal.huc.edu/comment.php?coord=1325002",
        "https://cal.huc.edu/comment.php?coord=1325002&extra=1",
        "https://cal.huc.edu/comment.php?coord=1325002#frag",
        "https://cal.huc.edu/comment.php?coord=1325003",
    ):
        page = SimpleNamespace(
            lines=[SimpleNamespace(coordinate="1325002", comment_url=url)]
        )
        assert select_comment_coordinate(page) is None
