"""Opt-in two-request CAL line-comment structure diagnostic for issue #343.

Never archive/print upstream HTML, lexical data, citation text or arbitrary errors.
Normal test/CI imports do not make CAL requests; only the module CLI does.
"""

from __future__ import annotations

import asyncio
import json
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalRequest,
    CalResponse,
    CalUpstreamError,
)
from cal_mcp.texts import (
    _LINE_COMMENTS_EMPTY_MARKER,
    TextParseError,
    TextService,
    _clean_text,
    _LineCommentsHTMLParser,
    parse_text_line_comments_page,
)

_KNOWN_ERRORS = {
    "CAL line-comments title does not uniquely match the request": "title_identity",
    "CAL line-comments page lacks one unique summary card": "summary_identity",
    "CAL line-comments summary contains no semantic records": "missing_records",
    "CAL line-comments empty marker conflicts with summary content": "empty_conflict",
    "CAL line-comments page contains no recognizable records": "unknown_records",
    "CAL line-comments record lacks one unique reference": "record_reference",
    "CAL line-comments record citation spans changed unexpectedly": "record_spans",
    "CAL line-comments record lacks one citation/entry break": "record_break",
    "CAL line-comments record lacks one unique lexical-entry link": "record_link",
    "CAL line-comments record repeats gloss markup": "record_gloss",
    "CAL line-comments record semantic field order changed unexpectedly": "record_order",
    "CAL line-comments record lexical-entry phrase changed unexpectedly": "record_phrase",
    "CAL line-comments record has unexpected trailing semantic content": "record_trailing",
    "CAL line-comments page has malformed nested title markup": "nested_title",
    "CAL line-comments page has nested summary cards": "nested_summary",
    "CAL line-comments summary contains nested records": "nested_records",
    "CAL line-comments record has malformed span nesting": "nested_span",
    "CAL line-comments record has nested lexical links": "nested_link",
    "CAL line-comments record has nested gloss markup": "nested_gloss",
    "CAL line-comments record closes with unfinished semantic markup": "unfinished_record",
    "CAL line-comments page ends with unfinished semantic markup": "unfinished_page",
}
_ALLOWED_EVENTS = {"reference", "span:heb", "span:rom", "br", "anchor", "gloss"}
_COORD_RE = re.compile(r"[0-9A-Za-z]{1,64}\Z")


_ALLOWED_SUMMARY_TAGS = frozenset(
    {
        "div",
        "p",
        "span",
        "br",
        "a",
        "b",
        "i",
        "em",
        "strong",
        "table",
        "tr",
        "td",
        "th",
        "ul",
        "li",
    }
)


class _SummaryTagOutline(HTMLParser):
    """Only whitelisted summary HTML tag names; no attrs, text or URLs in the report."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and self.depth == 0:
            if "summary-card" in (dict(attrs).get("class") or "").split():
                self.depth = 1
            return
        if self.depth:
            if tag == "div":
                self.depth += 1
            if len(self.tags) < 32:
                self.tags.append(tag if tag in _ALLOWED_SUMMARY_TAGS else "other")

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.depth:
            self.depth -= 1


def select_comment_coordinate(page: object) -> str | None:
    """Select only a canonical comment link already present on a parsed CAL page."""
    for line in getattr(page, "lines", ()):
        coordinate = getattr(line, "coordinate", None)
        link = getattr(line, "comment_url", None)
        if (
            not isinstance(coordinate, str)
            or _COORD_RE.fullmatch(coordinate) is None
            or not isinstance(link, str)
        ):
            continue
        url = urlsplit(link)
        if (
            url.scheme == "https"
            and url.netloc == "cal.huc.edu"
            and url.path == "/comment.php"
            and url.query == f"coord={coordinate}"
            and not url.fragment
        ):
            return coordinate
    return None


def summarize_response(response: CalResponse, coordinate: str) -> dict[str, object]:
    """Reduce a CAL comment response to structural flags and approved error codes."""
    parser = _LineCommentsHTMLParser()
    try:
        parser.feed(response.body.decode("utf-8", errors="replace"))
        parser.close()
        structure_error: str | None = None
    except TextParseError as exc:
        structure_error = _KNOWN_ERRORS.get(str(exc), "unrecognized_markup")

    outline = _SummaryTagOutline()
    outline.feed(response.body.decode("utf-8", errors="replace"))
    outline.close()
    empty_count = sum(
        _clean_text("".join(record.all_parts)) == _LINE_COMMENTS_EMPTY_MARKER
        for record in parser.records
    )
    signatures = [
        [event if event in _ALLOWED_EVENTS else "other" for event in record.events[:12]]
        for record in parser.records[:3]
    ]
    try:
        parsed = parse_text_line_comments_page(
            response,
            requested_coordinate=coordinate,
        )
        parse_status = parsed.status.value
        parser_reason: str | None = None
    except TextParseError as exc:
        parse_status = "drift"
        parser_reason = _KNOWN_ERRORS.get(str(exc), "unrecognized_structure")

    return {
        "coordinate": coordinate,
        "http_status": response.status_code,
        "content_type_is_html": bool(
            response.content_type and "text/html" in response.content_type.lower()
        ),
        "response_size_bytes": len(response.body),
        "title_count": len(parser.titles),
        "title_matches": parser.titles == [f"CAL: citations and comments for {coordinate}"],
        "summary_cards": parser.summary_count,
        "record_count": len(parser.records),
        "empty_marker_count": empty_count,
        "event_signatures": signatures,
        "summary_tags": outline.tags,
        "parse_status": parse_status,
        "parser_reason": parser_reason,
        "structure_error": structure_error,
    }


async def diagnose_once() -> dict[str, object]:
    """One current CAL page, then at most one matching comment GET after a 60s gap."""
    attempts = 0

    def before_attempt() -> None:
        nonlocal attempts
        if attempts >= 2:
            raise RuntimeError("CAL diagnostic transport budget exhausted")
        attempts += 1

    config = CalClientConfig(
        max_concurrency=1,
        max_retries=0,
        cache_enabled=False,
        min_request_interval_seconds=3.0,
        max_cal_attempts_per_60s=2,
    )

    async with CalHttpClient(
        config=config,
        before_transport_attempt=before_attempt,
    ) as http:
        try:
            page = await TextService(http).page("13250", page=1)
            if page.status.value != "found" or page.page is None:
                return {
                    "status": "blocked",
                    "category": "missing_current_text_page",
                    "actual_cal_transport_attempts": attempts,
                }
            coordinate = select_comment_coordinate(page.page)
            if coordinate is None:
                return {
                    "status": "blocked",
                    "category": "no_canonical_comment_selector",
                    "actual_cal_transport_attempts": attempts,
                }
            await asyncio.sleep(60.0)
            result = await http.fetch(
                CalRequest(
                    method="GET",
                    path="comment.php",
                    params=(("coord", coordinate),),
                ),
                parser=lambda response: summarize_response(response, coordinate),
                cache_namespace="issue-343-structural-diagnostic-v1",
            )
        except CalUpstreamError as exc:
            return {
                "status": "blocked",
                "category": "upstream_http",
                "http_status": exc.status_code,
                "actual_cal_transport_attempts": attempts,
            }
        except Exception:
            return {
                "status": "blocked",
                "category": "harness_or_content",
                "actual_cal_transport_attempts": attempts,
            }

    return {
        "status": "measured",
        "actual_cal_transport_attempts": attempts,
        "max_cal_transport_attempts": 2,
        "structure": result.value,
    }


def main() -> None:
    report = asyncio.run(diagnose_once())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["status"] != "measured":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
