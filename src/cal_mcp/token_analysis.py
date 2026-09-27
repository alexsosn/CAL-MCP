from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from cal_mcp.client import CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalInputError, CalParseError
from cal_mcp.identifiers import is_cal_machine_coordinate
from cal_mcp.lexicon import (
    LemmaRef,
    _lemma_key_from_href,
    _lemma_to_dict,
    _parse_lemma_header,
    _parse_lines,
)

_ANALYSIS_MARKER = "click on a headword to see a complete lexicon entry"
_NO_DATA_MARKER = "there is no data for this word"
_NO_LEMMA_MARKER = "unrecognizable query or no such lemma found"
_REDIRECT_SUFFIX_RE = re.compile(r"(?P<source>\S+\s+\S+)\s+-->\s+(?P<target>\S+\s+\S+)\s*$")


class TokenAnalysisParseError(CalParseError):
    """Raised when a CAL token-analysis page no longer exposes required semantics."""


class TokenAnalysisStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class TokenAnalysisCandidate:
    analysis_label: str
    lemma: LemmaRef
    analyzed_lemma_key: str | None = None


@dataclass(frozen=True, slots=True)
class TokenAnalysisPage:
    candidates: tuple[TokenAnalysisCandidate, ...]
    unlinked_summaries: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TokenAnalysisProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    coordinate: str
    word_index: int


@dataclass(frozen=True, slots=True)
class TokenAnalysisResult:
    status: TokenAnalysisStatus
    coordinate: str
    word_index: int
    candidates: tuple[TokenAnalysisCandidate, ...]
    provenance: TokenAnalysisProvenance
    unlinked_summaries: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "coordinate": self.coordinate,
            "word_index": self.word_index,
            "candidates": [_candidate_to_dict(item) for item in self.candidates],
            "unlinked_summaries": list(self.unlinked_summaries),
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(slots=True)
class _CurrentLinkBuilder:
    href: str
    classes: tuple[str, ...]
    parts: list[str]


@dataclass(frozen=True, slots=True)
class _CurrentLink:
    href: str
    classes: tuple[str, ...]
    text: str


class _CurrentLinkedRedirectParser(HTMLParser):
    """Read the bounded current lexlink result-table shape without consuming its sense outline."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.marker_h2_count = 0
        self._in_h2 = False
        self._h2_parts: list[str] = []
        self._after_marker = False
        self.label_parts: list[str] = []
        self.table_started = False
        self.table_closed = False
        self.table_depth = 0
        self.nested_table = False
        self.row_count = 0
        self.cell_count = 0
        self.links: list[_CurrentLink] = []
        self.table_loose_parts: list[str] = []
        self._open_link: _CurrentLinkBuilder | None = None
        self.unclosed_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = dict(attrs)
        if tag == "h2":
            self._in_h2 = True
            self._h2_parts = []
            return

        if not self._after_marker:
            return

        if not self.table_started:
            if tag == "table":
                self.table_started = True
                self.table_depth = 1
            return

        if self.table_depth < 1:
            return
        if tag == "table":
            self.nested_table = True
            self.table_depth += 1
        elif tag == "tr":
            self.row_count += 1
        elif tag == "td":
            self.cell_count += 1
        elif tag == "a":
            if self._open_link is not None:
                self.unclosed_link = True
            classes = tuple((attrs_d.get("class") or "").split())
            self._open_link = _CurrentLinkBuilder(
                href=attrs_d.get("href") or "",
                classes=classes,
                parts=[],
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._in_h2:
            marker = _clean_text("".join(self._h2_parts))
            if marker.lower() == _ANALYSIS_MARKER:
                self.marker_h2_count += 1
                self._after_marker = True
            self._in_h2 = False
            self._h2_parts = []
            return

        if not self.table_started or self.table_depth < 1:
            return
        if tag == "a" and self._open_link is not None:
            self.links.append(
                _CurrentLink(
                    href=self._open_link.href,
                    classes=self._open_link.classes,
                    text=_clean_text("".join(self._open_link.parts)),
                )
            )
            self._open_link = None
        elif tag == "table":
            self.table_depth -= 1
            if self.table_depth == 0:
                if self._open_link is not None:
                    self.unclosed_link = True
                self.table_closed = True

    def handle_data(self, data: str) -> None:
        if self._in_h2:
            self._h2_parts.append(data)
            return
        if not self._after_marker:
            return
        if not self.table_started:
            self.label_parts.append(data)
        elif self.table_depth > 0:
            if self._open_link is not None:
                self._open_link.parts.append(data)
            else:
                self.table_loose_parts.append(data)


def _current_linked_redirect_candidate(response: CalResponse) -> TokenAnalysisCandidate | None:
    parser = _CurrentLinkedRedirectParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    analysis_label = _clean_text("".join(parser.label_parts))
    redirect = _REDIRECT_SUFFIX_RE.search(analysis_label)
    current_shape_hint = parser.marker_h2_count > 0 and parser.table_started
    if not current_shape_hint:
        return None

    if not analysis_label:
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate has an empty analysis label"
        )
    if "-->" in analysis_label and (analysis_label.count("-->") != 1 or redirect is None):
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate has malformed redirect notation"
        )

    if parser.marker_h2_count != 1:
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate lacks one unique result marker"
        )
    if not parser.table_started or not parser.table_closed or parser.table_depth != 0:
        raise TokenAnalysisParseError("CAL current token-analysis candidate table is incomplete")
    if parser.nested_table or parser.row_count != 1 or parser.cell_count != 1:
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate table has an unexpected structure"
        )
    if _clean_text("".join(parser.table_loose_parts)):
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate table has rendered text outside its linked header"
        )
    if parser.unclosed_link or len(parser.links) != 1:
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate does not have exactly one linked header"
        )
    link = parser.links[0]
    if link.classes != ("lexlink",):
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate is missing its lexlink header"
        )
    parsed_href = urlsplit(link.href)
    if (
        parsed_href.scheme
        or parsed_href.netloc
        or parsed_href.fragment
        or parsed_href.path not in {"oneentry.php", "/oneentry.php"}
    ):
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate has an unexpected lemma-link route"
        )
    query = parse_qs(parsed_href.query, keep_blank_values=True)
    if set(query) != {"lemma", "cits"} or query.get("cits") != ["all"]:
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate lemma link has unexpected selectors"
        )
    lemma_values = query.get("lemma")
    if lemma_values is None or len(lemma_values) != 1 or not lemma_values[0].strip():
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate lemma link lacks one lemma key"
        )
    lemma_key = _lemma_key_from_href(link.href)
    if lemma_key is None or lemma_key != lemma_values[0]:
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate lemma link has an invalid lemma key"
        )

    analyzed_lemma_key: str | None = None
    if redirect is not None:
        analyzed_lemma_key = redirect.group("source")
        rendered_target = redirect.group("target")
        if rendered_target != lemma_key:
            raise TokenAnalysisParseError(
                "CAL token-analysis redirect target differs from its linked lemma key"
            )

    lemma = _parse_lemma_header(
        link.text,
        lemma_key=lemma_key,
        require_gloss=True,
    )
    if lemma is None:
        raise TokenAnalysisParseError(
            "CAL current token-analysis candidate has an unrecognized lemma header"
        )
    return TokenAnalysisCandidate(
        analysis_label=analysis_label,
        lemma=lemma,
        analyzed_lemma_key=analyzed_lemma_key,
    )


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _current_linkless_summaries(
    response: CalResponse,
    lines: tuple[object, ...],
    *,
    marker_index: int,
) -> tuple[str, ...] | None:
    """Preserve current H2-marker summaries without inventing lemma candidates."""

    structure = _CurrentLinkedRedirectParser()
    structure.feed(response.body.decode("utf-8", errors="replace"))
    structure.close()

    if structure.marker_h2_count == 0:
        return None
    if structure.marker_h2_count != 1:
        raise TokenAnalysisParseError(
            "CAL current linkless token-analysis page lacks one unique H2 result marker"
        )
    if structure.table_started:
        # Any current H2 + table shape belongs to the strict linked-table parser above.
        raise TokenAnalysisParseError(
            "CAL current token-analysis result table did not satisfy the linked-table contract"
        )

    summaries: list[str] = []
    saw_return = False
    for line in lines[marker_index + 1 :]:
        links = tuple(getattr(line, "links", ()))
        return_links = tuple(
            link for link in links if urlsplit(link.href).path.endswith("newtextmenu.html")
        )
        if return_links:
            if len(links) != 1 or len(return_links) != 1:
                raise TokenAnalysisParseError(
                    "CAL current linkless token-analysis return boundary contains extra links"
                )
            saw_return = True
            break
        if links:
            raise TokenAnalysisParseError(
                "CAL current linkless token-analysis summary unexpectedly contains links"
            )
        text = _clean_text(getattr(line, "text", ""))
        if text:
            summaries.append(text)

    if not saw_return:
        raise TokenAnalysisParseError(
            "CAL current linkless token-analysis page lacks its return-navigation boundary"
        )
    if not summaries:
        raise TokenAnalysisParseError(
            "CAL current linkless token-analysis result marker has no summary text"
        )
    return tuple(summaries)


def parse_token_analysis_page(response: CalResponse) -> TokenAnalysisPage:
    lines = _parse_lines(response)
    page_text = " ".join(line.text.lower() for line in lines)
    marker_indices = [
        index for index, line in enumerate(lines) if line.text.lower() == _ANALYSIS_MARKER
    ]
    has_lemma_path = any(_is_lemma_path(link.href) for line in lines for link in line.links)

    if _NO_DATA_MARKER in page_text:
        if marker_indices or has_lemma_path:
            raise TokenAnalysisParseError(
                "CAL token-analysis page mixes explicit no-data with analysis markup"
            )
        return TokenAnalysisPage(candidates=())

    if _NO_LEMMA_MARKER in page_text:
        if len(marker_indices) != 1 or has_lemma_path:
            raise TokenAnalysisParseError(
                "CAL token-analysis page has inconsistent current no-lemma markup"
            )
        return TokenAnalysisPage(candidates=())

    if len(marker_indices) != 1:
        raise TokenAnalysisParseError("CAL token-analysis page is missing its unique result marker")

    current_candidate = _current_linked_redirect_candidate(response)
    if current_candidate is not None:
        return TokenAnalysisPage(candidates=(current_candidate,))

    unlinked_summaries = _current_linkless_summaries(
        response,
        tuple(lines),
        marker_index=marker_indices[0],
    )
    if unlinked_summaries is not None:
        return TokenAnalysisPage(candidates=(), unlinked_summaries=unlinked_summaries)

    candidates: list[TokenAnalysisCandidate] = []
    index = marker_indices[0] + 1
    while index < len(lines):
        label_line = lines[index]
        if _is_return_to_text_browser(label_line):
            break
        if index + 1 >= len(lines):
            raise TokenAnalysisParseError(
                "CAL token-analysis page ends with an incomplete candidate"
            )

        lemma_line = lines[index + 1]
        lemma_path_links = tuple(link for link in lemma_line.links if _is_lemma_path(link.href))
        if not lemma_path_links:
            if (
                _parse_lemma_header(
                    lemma_line.text,
                    lemma_key="placeholder",
                    require_gloss=True,
                )
                is not None
            ):
                raise TokenAnalysisParseError(
                    "CAL token-analysis candidate lemma header is missing its lemma link"
                )
            if candidates:
                break
            raise TokenAnalysisParseError(
                "CAL token-analysis result marker is not followed by a candidate"
            )

        if label_line.links:
            raise TokenAnalysisParseError("CAL token-analysis label unexpectedly contains links")
        analysis_label = label_line.text.strip()
        if not analysis_label:
            raise TokenAnalysisParseError(
                "CAL token-analysis candidate has an empty analysis label"
            )
        if len(lemma_path_links) != 1:
            raise TokenAnalysisParseError(
                "CAL token-analysis candidate has multiple lemma-entry links"
            )

        lemma_link = lemma_path_links[0]
        lemma_key = _lemma_key_from_href(lemma_link.href)
        if lemma_key is None:
            raise TokenAnalysisParseError(
                "CAL token-analysis candidate lemma link is missing its lemma key"
            )
        lemma = _parse_lemma_header(
            lemma_link.text,
            lemma_key=lemma_key,
            require_gloss=True,
        )
        if lemma is None:
            raise TokenAnalysisParseError(
                "CAL token-analysis candidate has an unrecognized lemma header"
            )

        candidates.append(
            TokenAnalysisCandidate(
                analysis_label=analysis_label,
                lemma=lemma,
                analyzed_lemma_key=None,
            )
        )
        index += 2

    if not candidates:
        raise TokenAnalysisParseError(
            "CAL token-analysis page has neither candidates nor explicit no-data"
        )
    return TokenAnalysisPage(candidates=tuple(candidates))


class TokenAnalysisService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def analyze(self, coordinate: str, word_index: int) -> TokenAnalysisResult:
        normalized_coordinate = _validate_coordinate(coordinate)
        normalized_word_index = _validate_word_index(word_index)

        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="getlex.php",
                params=(
                    ("coord", normalized_coordinate),
                    ("word", str(normalized_word_index)),
                ),
            ),
            parser=parse_token_analysis_page,
            cache_namespace="token-analysis-v1",
        )
        status = (
            TokenAnalysisStatus.FOUND
            if result.value.candidates or result.value.unlinked_summaries
            else TokenAnalysisStatus.NOT_FOUND
        )
        provenance = TokenAnalysisProvenance(
            source="CAL",
            source_url=result.source_url,
            retrieved_at=result.retrieved_at,
            coordinate=normalized_coordinate,
            word_index=normalized_word_index,
        )
        return TokenAnalysisResult(
            status=status,
            coordinate=normalized_coordinate,
            word_index=normalized_word_index,
            candidates=result.value.candidates,
            provenance=provenance,
            unlinked_summaries=result.value.unlinked_summaries,
        )


def _validate_coordinate(value: str) -> str:
    if not is_cal_machine_coordinate(value):
        raise CalInputError(
            "coordinate must be a CAL decimal coordinate or contain one lowercase letter "
            "between decimal segments"
        )
    return value


def _validate_word_index(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CalInputError("word_index must be a non-negative integer")
    return value


def _is_lemma_path(href: str) -> bool:
    path = urlsplit(href).path
    return path.endswith("oneentry.php") or path.endswith("cal_entry_web.php")


def _is_return_to_text_browser(line: object) -> bool:
    links = getattr(line, "links", ())
    return any(urlsplit(link.href).path.endswith("newtextmenu.html") for link in links)


def _candidate_to_dict(candidate: TokenAnalysisCandidate) -> dict[str, object]:
    return {
        "analysis_label": candidate.analysis_label,
        "analyzed_lemma_key": candidate.analyzed_lemma_key,
        "lemma": _lemma_to_dict(candidate.lemma),
    }


def _provenance_to_dict(provenance: TokenAnalysisProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "coordinate": provenance.coordinate,
        "word_index": provenance.word_index,
    }


__all__ = [
    "TokenAnalysisCandidate",
    "TokenAnalysisPage",
    "TokenAnalysisParseError",
    "TokenAnalysisProvenance",
    "TokenAnalysisResult",
    "TokenAnalysisService",
    "TokenAnalysisStatus",
    "parse_token_analysis_page",
]
