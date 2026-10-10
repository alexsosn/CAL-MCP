from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import (
    CAL_BASE_URL,
    CalHttpClient,
    CalRequest,
    CalResponse,
)
from cal_mcp.errors import CalInputError, CalOutOfRangeError, CalParseError, CalRejectedInputError
from cal_mcp.identifiers import (
    has_subtext_letter_suffix,
    is_cal_machine_coordinate,
    is_cal_mandaic_machine_coordinate,
    is_cal_subtext_id,
)
from cal_mcp.lexicon import _Line, _Link, _parse_lines
from cal_mcp.syriac import syriac_text_category_slugs

_ID_RE = re.compile(r"^\d+$")
_LINE_COMMENT_COORD_RE = re.compile(r"^[A-Za-z0-9]{1,64}$")
_PAGE_MARKER_RE = re.compile(
    r"^Page\s+(?P<page>\d+)\s+of\s+(?P<count>\d+)"
    r"(?:\s+\((?P<total>\d+)\s+lines total\))?$",
    re.IGNORECASE,
)
_PAGE_MARKER_ANYWHERE_RE = re.compile(r"\bPage\s+\d+\s+of\s+\d+", re.IGNORECASE)
_TEXT_CELL_TAGS = frozenset({"a", "span", "cal-variant", "td", "tr", "table"})
_RAW_TEXT_LT_RE = re.compile(r"<(?![A-Za-z][A-Za-z0-9-]*[\s/>]|/[A-Za-z][A-Za-z0-9-]*\s*>|!|\?)")
_NO_LINES_RE = re.compile(
    r"^NO LINES FOR (?P<file>\d+)(?: (?P<selector>\d+))? ARE CURRENTLY STORED$",
    re.IGNORECASE,
)
_NO_LINES_ANYWHERE_RE = re.compile(
    r"NO LINES FOR.*ARE CURRENTLY STORED",
    re.IGNORECASE,
)
_TEXT_SEARCH_MARKER = "cal search for texts like:"
_SCRIPT_TOGGLE_RE = re.compile(r"[A-Z]")
_FOLLOW_UP_TEXT_PAGE = "cal_text_page"
_FOLLOW_UP_CATALOGUE = "cal_text_catalogue"
# Script selectors on catalogue-node search links: H (Neofiti) and U (Peshitta) are observed;
# R and S are CAL's other script codes (R-053).
_SCRIPT_CSETS = frozenset({"R", "H", "S", "U", "T"})
# Mandaic collection links: M observed in search, R in CAL's Mandaic catalogue (R-053).
_MANDAIC_SEARCH_CSETS = frozenset({"M", "R"})
# CPA catalogue nodes use CAL's own CPA script selector (R-083).
_CPA_SEARCH_CSETS = frozenset({"C"})
_SEARCH_LABEL_SEPARATOR_RE = re.compile(r":(?=\s|$)")
_TEXT_SEARCH_EMPTY_MARKER = "there are no files associated with the search term"
# CAL echoes the term it actually searched; it may differ from the submitted query (R-077).
_TEXT_SEARCH_ECHO_RE = re.compile(
    r"CAL search for texts like: (.*?)\. Click on the file number to view\.", re.IGNORECASE
)
_TEXT_SEARCH_EMPTY_ECHO_RE = re.compile(
    r"There are no files associated with the search term (.*?)$", re.IGNORECASE
)
_TEXT_SEARCH_REJECTED_RE = re.compile(r'"(.*?)" is not a valid search string')
_TEXT_INFORMATION_HEADING = "Text Information"
_TEXT_INFORMATION_MISSING_MARKER = "No information on record for this text."
_LINE_COMMENTS_EMPTY_MARKER = "NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED"
_LINE_COMMENTS_IGNORED_TAGS = frozenset({"script", "style"})
_MANDAIC_COLLECTION_PREFIX = "74"
_MANDAIC_CATEGORY_ID = "74"
_MANDAIC_CATALOGUE_PATH = "show_Mandaic.php"
_MANDAIC_ROOT_LABEL = "Mandaic"
_CPA_SUBDIVIDED_FILE_IDS = frozenset(
    {
        "55000",
        "55001",
        "55003",
        "55006",
        "55007",
        "55400",
        "55401",
        "55402",
        "55403",
        "55404",
        "55405",
        "55420",
        "55421",
        "55422",
        "55423",
    }
)
_CPA_DIRECT_FILE_IDS = frozenset({"55002", "55406", "55407", "55430"})
_CPA_PAGINATED_DIRECT_FILE_IDS = frozenset({"55430"})
_CPA_TEXT_FILE_IDS = _CPA_SUBDIVIDED_FILE_IDS | _CPA_DIRECT_FILE_IDS
_MANDAIC_SUBDIVIDED_FILE_IDS = frozenset(
    {
        "74401",
        "74402",
        "74410",
        "74411",
        "74421",
        "74422",
        "74423",
        "74428",
        "74430",
        "74432",
        "74700",
        "74701",
        "74702",
        "74711",
        "74714",
        "74923",
    }
)
_MANDAIC_PAGINATED_DIRECT_FILE_IDS = frozenset({"74501"})
_MANDAIC_ALPHANUMERIC_COORDINATE_FILE_IDS = frozenset({"74425", "74429"})
_MANDAIC_SPECIAL_COORDINATE_PREFIXES = frozenset({"74421col", "74425", "74429"})
_ONKELOS_JONATHAN_CATEGORY_ID = "51"
_ONKELOS_JONATHAN_PATH = "targum_onkelos_jonathan.html"
_ONKELOS_JONATHAN_LABEL = "Targums Onkelos and Jonathan to the Prophets"
_SYRIAC_COLLECTION_KEY = "syriac"
_SYRIAC_ROOT_PATH = "AvailSyr.html"
_SYRIAC_ROOT_LABEL = "Syriac"
_SYRIAC_FOLLOW_UP_TOOL = "cal_syriac_texts"
_SYRIAC_SELECTOR_NAME = "category"
_ROOT_CATALOGUE_PATH = "newtextmenu.html"


class TextParseError(CalParseError):
    """Raised when a CAL text page no longer exposes the required semantics."""


class TextPageStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class TextInformationStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class TextLineCommentsStatus(StrEnum):
    FOUND = "found"
    NO_CITATIONS = "no_citations"


@dataclass(frozen=True, slots=True)
class TextRef:
    file_id: str
    subtext_id: str | None
    label: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class TextCategoryRef:
    category_id: str
    label: str


@dataclass(frozen=True, slots=True)
class TextSpecializedCollectionRef:
    collection_key: str
    label: str
    follow_up_tool: str
    selector_name: str
    supported_selectors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TextToken:
    coordinate: str
    word_index: int
    text: str
    lexical_url: str


@dataclass(frozen=True, slots=True)
class TextLine:
    coordinate: str | None
    display_coordinate: str | None
    text: str
    tokens: tuple[TextToken, ...]
    comment_url: str | None
    empty_word_indexes: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class TextPage:
    text: TextRef
    page: int
    page_count: int | None
    total_lines: int | None
    previous_page: int | None
    next_page: int | None
    lines: tuple[TextLine, ...]
    previous_subtext_id: str | None = None
    next_subtext_id: str | None = None


@dataclass(frozen=True, slots=True)
class TextCataloguePage:
    categories: tuple[TextCategoryRef, ...]
    texts: tuple[TextRef, ...]
    specialized_collections: tuple[TextSpecializedCollectionRef, ...] = ()


@dataclass(frozen=True, slots=True)
class TextSearchMatch:
    """One text-search result and the tool that follows it (R-053).

    A readable text has ``file_id`` (and any ``subtext_id``); a catalogue node has only
    ``category_id``.
    """

    file_id: str | None
    subtext_id: str | None
    category_id: str | None
    label: str
    description: str | None
    follow_up_tool: str


@dataclass(frozen=True, slots=True)
class TextSearchPage:
    matches: tuple[TextSearchMatch, ...]


@dataclass(frozen=True, slots=True)
class TextInformationPage:
    status: TextInformationStatus
    metadata: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TextLineCommentRecord:
    reference: str
    source_text: str | None
    translation: str | None
    lemma_key: str
    headword: str
    part_of_speech: str | None
    gloss: str | None
    entry_url: str


@dataclass(frozen=True, slots=True)
class TextLineCommentsPage:
    status: TextLineCommentsStatus
    records: tuple[TextLineCommentRecord, ...]


@dataclass(frozen=True, slots=True)
class TextProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    upstream_id: str | None = None
    subtext_id: str | None = None
    category_id: str | None = None
    page: int | None = None
    original_query: str | None = None
    submitted_query: str | None = None


@dataclass(frozen=True, slots=True)
class TextCatalogueResult:
    categories: tuple[TextCategoryRef, ...]
    texts: tuple[TextRef, ...]
    provenance: TextProvenance
    specialized_collections: tuple[TextSpecializedCollectionRef, ...] = ()

    @property
    def recursive(self) -> bool:
        return False

    @property
    def has_unexpanded_children(self) -> bool:
        return bool(self.categories or self.specialized_collections)

    def to_dict(self) -> dict[str, object]:
        return {
            "categories": [_category_to_dict(item) for item in self.categories],
            "texts": [_text_ref_to_dict(item) for item in self.texts],
            "specialized_collections": [
                _specialized_collection_to_dict(item) for item in self.specialized_collections
            ],
            "provenance": _provenance_to_dict(self.provenance),
            "recursive": self.recursive,
            "has_unexpanded_children": self.has_unexpanded_children,
        }


@dataclass(frozen=True, slots=True)
class TextSearchResult:
    matches: tuple[TextSearchMatch, ...]
    provenance: TextProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "matches": [_search_match_to_dict(item) for item in self.matches],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class TextPageResult:
    status: TextPageStatus
    page: TextPage | None
    provenance: TextProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "page": _text_page_to_dict(self.page) if self.page is not None else None,
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class TextInformationResult:
    status: TextInformationStatus
    file_id: str
    subtext_id: str | None
    metadata: tuple[str, ...]
    provenance: TextProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "file_id": self.file_id,
            "subtext_id": self.subtext_id,
            "metadata": list(self.metadata),
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class TextLineCommentsResult:
    status: TextLineCommentsStatus
    coordinate: str
    records: tuple[TextLineCommentRecord, ...]
    provenance: TextProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "coordinate": self.coordinate,
            "records": [_line_comment_record_to_dict(item) for item in self.records],
            "provenance": _provenance_to_dict(self.provenance),
        }


class _LineCommentRecordBuilder:
    def __init__(self) -> None:
        self.all_parts: list[str] = []
        self.reference_parts: list[str] = []
        self.reference_count = 0
        self.spans: list[tuple[str, list[str]]] = []
        self.br_count = 0
        self.before_entry_parts: list[str] = []
        self.links: list[tuple[str, list[str]]] = []
        self.pos_parts: list[str] = []
        self.gloss_parts: list[str] = []
        self.gloss_count = 0
        self.trailing_parts: list[str] = []
        self.events: list[str] = []


class _LineCommentsHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.titles: list[str] = []
        self.records: list[_LineCommentRecordBuilder] = []
        self.summary_count = 0
        self._summary_depth = 0
        self._title_parts: list[str] | None = None
        self._record: _LineCommentRecordBuilder | None = None
        self._span_parts: list[str] | None = None
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] | None = None
        self._in_reference = False
        self._in_gloss = False
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._ignored_depth:
            self._ignored_depth += 1
            return
        if tag in _LINE_COMMENTS_IGNORED_TAGS:
            self._ignored_depth = 1
            return

        attr_map = dict(attrs)
        if tag == "title":
            if self._title_parts is not None:
                raise TextParseError("CAL line-comments page has malformed nested title markup")
            self._title_parts = []
            return

        if tag == "div":
            classes = (attr_map.get("class") or "").split()
            if "summary-card" in classes:
                if self._summary_depth:
                    raise TextParseError("CAL line-comments page has nested summary cards")
                self.summary_count += 1
                self._summary_depth = 1
            elif self._summary_depth:
                self._summary_depth += 1
            return

        if not self._summary_depth:
            return
        if tag == "p":
            if self._record is not None:
                raise TextParseError("CAL line-comments summary contains nested records")
            self._record = _LineCommentRecordBuilder()
            return
        if self._record is None:
            return

        if tag == "span":
            if self._span_parts is not None or self._anchor_parts is not None:
                raise TextParseError("CAL line-comments record has malformed span nesting")
            span_class = attr_map.get("class") or ""
            parts: list[str] = []
            self._record.spans.append((span_class, parts))
            self._record.events.append(f"span:{span_class}")
            self._span_parts = parts
            return
        if tag == "br":
            self._record.br_count += 1
            self._record.events.append("br")
            return
        if tag == "a":
            if self._anchor_parts is not None:
                raise TextParseError("CAL line-comments record has nested lexical links")
            href = attr_map.get("href") or ""
            parts = []
            self._record.links.append((href, parts))
            self._record.events.append("anchor")
            self._anchor_href = href
            self._anchor_parts = parts
            return
        if tag == "b":
            if self._in_gloss:
                raise TextParseError("CAL line-comments record has nested gloss markup")
            self._record.gloss_count += 1
            self._record.events.append("gloss")
            self._in_gloss = True
            return
        if tag == "i" and self._anchor_parts is None:
            self._record.reference_count += 1
            self._record.events.append("reference")
            self._in_reference = True

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            self._ignored_depth -= 1
            return

        if tag == "title" and self._title_parts is not None:
            self.titles.append(_clean_text("".join(self._title_parts)))
            self._title_parts = None
            return

        if tag == "p" and self._record is not None:
            if (
                self._span_parts is not None
                or self._anchor_parts is not None
                or self._in_reference
                or self._in_gloss
            ):
                raise TextParseError(
                    "CAL line-comments record closes with unfinished semantic markup"
                )
            self.records.append(self._record)
            self._record = None
            self._in_reference = False
            return
        if tag == "span" and self._span_parts is not None:
            self._span_parts = None
            return
        if tag == "a" and self._anchor_parts is not None:
            self._anchor_href = None
            self._anchor_parts = None
            return
        if tag == "b" and self._in_gloss:
            self._in_gloss = False
            return
        if tag == "i" and self._in_reference:
            self._in_reference = False
            return
        if tag == "div" and self._summary_depth:
            self._summary_depth -= 1

    def close(self) -> None:
        super().close()
        if (
            self._record is not None
            or self._summary_depth
            or self._ignored_depth
            or self._span_parts is not None
            or self._anchor_parts is not None
            or self._in_reference
            or self._in_gloss
            or self._title_parts is not None
        ):
            raise TextParseError("CAL line-comments page ends with unfinished semantic markup")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._title_parts is not None:
            self._title_parts.append(data)
        record = self._record
        if record is None:
            return
        record.all_parts.append(data)
        if self._anchor_parts is not None:
            self._anchor_parts.append(data)
        elif self._span_parts is not None:
            self._span_parts.append(data)
        elif self._in_gloss:
            record.gloss_parts.append(data)
        elif self._in_reference:
            record.reference_parts.append(data)
        elif record.br_count and not record.links:
            record.before_entry_parts.append(data)
        elif record.links:
            if record.gloss_count:
                record.trailing_parts.append(data)
            else:
                record.pos_parts.append(data)


def parse_text_line_comments_page(
    response: CalResponse,
    *,
    requested_coordinate: str,
) -> TextLineCommentsPage:
    coordinate = _validate_line_comment_coordinate(requested_coordinate)
    _validate_line_comment_response_url(response.url, coordinate)

    parser = _LineCommentsHTMLParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    expected_title = f"CAL: citations and comments for {coordinate}"
    if parser.titles != [expected_title]:
        raise TextParseError("CAL line-comments title does not uniquely match the request")
    if parser.summary_count != 1:
        raise TextParseError("CAL line-comments page lacks one unique summary card")
    if not parser.records:
        raise TextParseError("CAL line-comments summary contains no semantic records")

    empty_markers = 0
    records: list[TextLineCommentRecord] = []
    for builder in parser.records:
        rendered = _clean_text("".join(builder.all_parts))
        if rendered == _LINE_COMMENTS_EMPTY_MARKER:
            empty_markers += 1
            continue
        records.append(_parse_line_comment_record(builder, response.url))

    if empty_markers:
        if empty_markers != 1 or records or len(parser.records) != 1:
            raise TextParseError("CAL line-comments empty marker conflicts with summary content")
        return TextLineCommentsPage(status=TextLineCommentsStatus.NO_CITATIONS, records=())
    if not records:
        raise TextParseError("CAL line-comments page contains no recognizable records")
    return TextLineCommentsPage(status=TextLineCommentsStatus.FOUND, records=tuple(records))


def _parse_line_comment_record(
    builder: _LineCommentRecordBuilder,
    source_url: str,
) -> TextLineCommentRecord:
    if builder.reference_count != 1:
        raise TextParseError("CAL line-comments record lacks one unique reference")
    if [span_class for span_class, _parts in builder.spans] != ["heb", "rom"]:
        raise TextParseError("CAL line-comments record citation spans changed unexpectedly")
    if builder.br_count != 1:
        raise TextParseError("CAL line-comments record lacks one citation/entry break")
    if len(builder.links) != 1:
        raise TextParseError("CAL line-comments record lacks one unique lexical-entry link")
    if builder.gloss_count > 1:
        raise TextParseError("CAL line-comments record repeats gloss markup")

    expected_events = ["reference", "span:heb", "span:rom", "br", "anchor"]
    if builder.gloss_count:
        expected_events.append("gloss")
    if builder.events != expected_events:
        raise TextParseError("CAL line-comments record semantic field order changed unexpectedly")
    if _clean_text("".join(builder.before_entry_parts)) != "See the entire entry for":
        raise TextParseError("CAL line-comments record lexical-entry phrase changed unexpectedly")
    if _clean_text("".join(builder.trailing_parts)):
        raise TextParseError("CAL line-comments record has unexpected trailing semantic content")

    reference = _clean_text("".join(builder.reference_parts))
    if not reference:
        raise TextParseError("CAL line-comments record has an empty reference")
    source_text = _optional_clean_text("".join(builder.spans[0][1]))
    translation = _optional_clean_text("".join(builder.spans[1][1]))

    href, headword_parts = builder.links[0]
    entry_url, lemma_key = _validate_line_comment_entry_url(source_url, href)
    headword = _clean_text("".join(headword_parts))
    if not headword:
        raise TextParseError("CAL line-comments lexical-entry link has no rendered headword")

    return TextLineCommentRecord(
        reference=reference,
        source_text=source_text,
        translation=translation,
        lemma_key=lemma_key,
        headword=headword,
        part_of_speech=_optional_clean_text("".join(builder.pos_parts)),
        gloss=_optional_clean_text("".join(builder.gloss_parts)),
        entry_url=entry_url,
    )


def _validate_line_comment_response_url(url: str, requested_coordinate: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "cal.huc.edu"
        or parsed.path != "/comment.php"
        or parsed.fragment
    ):
        raise TextParseError("CAL line-comments response has an unexpected route")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) != {"coord"} or query.get("coord") != [requested_coordinate]:
        raise TextParseError("CAL line-comments response coordinate contradicts the request")


def _validate_line_comment_entry_url(source_url: str, href: str) -> tuple[str, str]:
    resolved = urljoin(source_url, href)
    parsed = urlsplit(resolved)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "cal.huc.edu"
        or parsed.path != "/oneentry.php"
        or parsed.fragment
    ):
        raise TextParseError("CAL line-comments lexical-entry link has an unexpected route")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) != {"lemma", "cits"}:
        raise TextParseError("CAL line-comments lexical-entry link has unexpected selectors")
    lemma_values = query.get("lemma")
    cits_values = query.get("cits")
    if lemma_values is None or len(lemma_values) != 1 or not lemma_values[0]:
        raise TextParseError("CAL line-comments lexical-entry link lacks one lemma selector")
    if cits_values != ["all"]:
        raise TextParseError("CAL line-comments lexical-entry link must request cits=all")

    return resolved, lemma_values[0]


def parse_text_catalogue_page(response: CalResponse) -> TextCataloguePage:
    categories: list[TextCategoryRef] = []
    texts: list[TextRef] = []
    specialized_collections: list[TextSpecializedCollectionRef] = []
    seen_specialized_keys: set[str] = set()
    is_root_catalogue = _is_root_catalogue_response(response.url)
    requested_node = _requested_catalogue_node(response.url)

    for line in _parse_lines(response):
        for link in line.links:
            if requested_node is not None and _is_own_script_toggle(link, requested_node):
                continue
            if is_root_catalogue:
                specialized = _specialized_collection_from_link(link)
                if specialized is not None:
                    if specialized.collection_key in seen_specialized_keys:
                        raise TextParseError("CAL text catalogue repeats a specialized collection")
                    seen_specialized_keys.add(specialized.collection_key)
                    specialized_collections.append(specialized)
                    continue
            category = _category_from_link(link)
            if category is not None:
                categories.append(category)
                continue
            text = _text_ref_from_link(link)
            if text is not None:
                texts.append(text)

    if not categories and not texts and not specialized_collections:
        raise TextParseError(
            "CAL text catalogue contains no recognizable category, text, or specialized links"
        )
    return TextCataloguePage(
        categories=tuple(categories),
        texts=tuple(texts),
        specialized_collections=tuple(specialized_collections),
    )


class _RouteLinkCounter(HTMLParser):
    """Count Mandaic route anchors the way the page's HTML parser sees them.

    ``HTMLParser`` reports no tags inside ``<script>``/``<style>`` or comments, so links
    there are not counted, matching the shared line splitter.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.count = 0
        self.chapter_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        path = urlsplit(dict(attrs).get("href") or "").path
        if path.endswith(("showsubtexts.php", "get_a_chapter.php")):
            self.count += 1
        if path.endswith("get_a_chapter.php"):
            self.chapter_count += 1


def _mandaic_route_counts(response: CalResponse) -> tuple[int, int]:
    counter = _RouteLinkCounter()
    counter.feed(response.body.decode("utf-8", errors="replace"))
    counter.close()
    return counter.count, counter.chapter_count


def _count_mandaic_route_links(response: CalResponse) -> int:
    return _mandaic_route_counts(response)[0]


def _count_mandaic_chapter_route_links(response: CalResponse) -> int:
    return _mandaic_route_counts(response)[1]


def parse_mandaic_catalogue_page(response: CalResponse) -> TextCataloguePage:
    parsed_response = urlsplit(response.url)
    if parsed_response.path != f"/{_MANDAIC_CATALOGUE_PATH}":
        raise TextParseError("CAL Mandaic catalogue response endpoint changed unexpectedly")
    response_query = parse_qs(parsed_response.query, keep_blank_values=True)
    if set(response_query) != {"R1"} or response_query.get("R1") != [_MANDAIC_CATEGORY_ID]:
        raise TextParseError("CAL Mandaic catalogue response selector changed unexpectedly")

    categories: list[TextCategoryRef] = []
    texts: list[TextRef] = []
    seen_ids: set[str] = set()
    for line in _parse_lines(response):
        candidates: list[TextCategoryRef | TextRef] = []
        for link in line.links:
            candidate = _mandaic_catalogue_item_from_link(line, link, response.url)
            if candidate is not None:
                candidates.append(candidate)
        if len(candidates) > 1:
            raise TextParseError("CAL Mandaic catalogue row exposes multiple text routes")
        if not candidates:
            continue
        candidate = candidates[0]
        identifier = (
            candidate.category_id if isinstance(candidate, TextCategoryRef) else candidate.file_id
        )
        if identifier in seen_ids:
            raise TextParseError("CAL Mandaic catalogue repeats a file identifier")
        seen_ids.add(identifier)
        if isinstance(candidate, TextCategoryRef):
            categories.append(candidate)
        else:
            texts.append(candidate)

    if not categories and not texts:
        raise TextParseError("CAL Mandaic catalogue contains no recognizable text rows")
    # The shared line splitter drops a row with no text together with its links, so a
    # route link without a title would vanish silently; every route link must be represented.
    route_links = _count_mandaic_route_links(response)
    if route_links != len(categories) + len(texts):
        raise TextParseError("CAL Mandaic catalogue has a text link without a rendered title")
    return TextCataloguePage(categories=tuple(categories), texts=tuple(texts))


def parse_text_search_page(
    response: CalResponse, *, submitted_query: str | None = None
) -> TextSearchPage:
    lines = _parse_lines(response)
    page_text = " ".join(line.text for line in lines)
    lowered = page_text.lower()

    rejections = [
        match.group(1) for line in lines if (match := _TEXT_SEARCH_REJECTED_RE.search(line.text))
    ]
    if rejections:
        if len(rejections) != 1 or _TEXT_SEARCH_MARKER in lowered:
            raise TextParseError("CAL text search rejection contradicts the rest of the page")
        raise CalRejectedInputError(
            f'CAL rejected the text search: "{rejections[0]}" is not a valid search string '
            "(CAL removes the characters it does not search on, such as non-ASCII letters "
            "and punctuation)"
        )

    echoes = [
        match.group(1).strip()
        for line in lines
        if (match := _TEXT_SEARCH_ECHO_RE.search(line.text)) is not None
    ]
    if len(echoes) > 1:
        raise TextParseError("CAL text search page repeats its search-term heading")
    empty_echoes = [
        match.group(1).strip()
        for line in lines
        if (match := _TEXT_SEARCH_EMPTY_ECHO_RE.search(line.text)) is not None
    ]
    if echoes and empty_echoes and empty_echoes != echoes:
        raise TextParseError("CAL text search no-files marker contradicts its heading")
    if echoes and submitted_query is not None and echoes[0] != submitted_query:
        raise CalRejectedInputError(
            f'CAL searched for "{echoes[0]}", not "{submitted_query}": CAL text search drops '
            "characters it does not search on. Call cal_text_search again with "
            f'"{echoes[0]}" to use the term CAL actually searched.'
        )

    if _TEXT_SEARCH_EMPTY_MARKER in lowered:
        return TextSearchPage(matches=())
    if _TEXT_SEARCH_MARKER not in lowered:
        raise TextParseError("CAL text search page is missing its result marker")

    matches: list[TextSearchMatch] = []
    for line in lines:
        for link in line.links:
            if not (
                _is_path(link.href, "get_a_chapter.php") or _is_path(link.href, "showsubtexts.php")
            ):
                continue
            label, description = _search_label_and_description(line, link)
            text = _search_text_ref_from_link(link, label=label, description=description)
            if text is None:
                raise TextParseError("CAL text search result contains a malformed text link")
            matches.append(text)

    if not matches:
        raise TextParseError(
            "CAL text search page has neither results nor the explicit no-files marker"
        )
    return TextSearchPage(matches=tuple(matches))


def parse_text_information_page(response: CalResponse) -> TextInformationPage:
    lines = _parse_lines(response)
    heading_indexes = [
        index for index, line in enumerate(lines) if line.text == _TEXT_INFORMATION_HEADING
    ]
    if len(heading_indexes) != 1:
        raise TextParseError("CAL text-information page is missing its unique semantic heading")

    metadata = tuple(line.text for line in lines[heading_indexes[0] + 1 :])
    if _TEXT_INFORMATION_MISSING_MARKER in metadata:
        if metadata != (_TEXT_INFORMATION_MISSING_MARKER,):
            raise TextParseError("CAL text-information missing marker is mixed with metadata")
        return TextInformationPage(status=TextInformationStatus.NOT_FOUND, metadata=())
    if not metadata:
        raise TextParseError("CAL text-information page contains no metadata")
    return TextInformationPage(status=TextInformationStatus.FOUND, metadata=metadata)


def _has_explicit_no_lines_marker(
    lines: list[_Line],
    *,
    requested_file_id: str,
    requested_subtext_id: str | None,
) -> bool:
    matches: list[re.Match[str]] = []
    for line in lines:
        residue = line.text
        marker_like = _NO_LINES_ANYWHERE_RE.search(residue) is not None
        if not marker_like:
            continue

        for link in line.links:
            parsed = urlsplit(link.href)
            query = parse_qs(parsed.query, keep_blank_values=True)
            if (
                parsed.scheme
                or parsed.netloc
                or parsed.fragment
                or parsed.path not in {"get_a_chapter.php", "/get_a_chapter.php"}
                or set(query) != {"file", "sub", "cset", "variants"}
                or query.get("file") != [requested_file_id]
                or query.get("sub") != [""]
                or query.get("cset") != ["C"]
                or query.get("variants") != ["0"]
            ):
                raise TextParseError(
                    "CAL no-lines marker has an unexpected inline manuscript-variant link"
                )
            if not link.text or link.text not in residue:
                raise TextParseError("CAL no-lines marker link is detached from its rendered text")
            residue = residue.replace(link.text, " ", 1)

        residue = _clean_text(residue)
        match = _NO_LINES_RE.fullmatch(residue)
        if match is None:
            raise TextParseError("CAL text page has a malformed no-lines marker")
        matches.append(match)

    if len(matches) > 1:
        raise TextParseError("CAL text page has multiple no-lines markers")
    if not matches:
        return False

    match = matches[0]
    marker_file = match.group("file")
    if marker_file != requested_file_id:
        raise TextParseError("CAL no-lines marker file differs from the requested file")

    marker_selector = match.group("selector")
    if (
        marker_selector is not None
        and requested_subtext_id is not None
        and marker_selector != requested_subtext_id
    ):
        raise TextParseError("CAL no-lines marker subtext differs from the requested subtext")
    return True


def parse_text_page(
    response: CalResponse,
    *,
    requested_file_id: str,
    requested_subtext_id: str | None,
    requested_page: int | None = None,
) -> TextPage | None:
    return _parse_text_page(
        response,
        requested_file_id=requested_file_id,
        requested_subtext_id=requested_subtext_id,
        requested_page=requested_page,
        mandaic_page_route=False,
        submitted_sub=requested_subtext_id,
    )


def _parse_text_page(
    response: CalResponse,
    *,
    requested_file_id: str,
    requested_subtext_id: str | None,
    requested_page: int | None,
    mandaic_page_route: bool,
    submitted_sub: str | None = None,
) -> TextPage | None:
    lines = _parse_lines(response)
    if _has_explicit_no_lines_marker(
        lines,
        requested_file_id=requested_file_id,
        requested_subtext_id=requested_subtext_id,
    ):
        return None

    text_ref, cal_file_sub = _page_text_ref(
        lines,
        requested_file_id,
        requested_subtext_id,
        submitted_sub=submitted_sub,
    )
    page_number, page_count, total_lines = _page_metadata(lines)
    if mandaic_page_route and page_count is None and requested_page is not None:
        page_number = requested_page
    # A six-digit id that CAL splits into file plus sub navigates by that split (R-046).
    navigation_file_id, navigation_subtext_id = cal_file_sub or (
        requested_file_id,
        requested_subtext_id,
    )
    previous_page, next_page, previous_subtext, next_subtext = _page_navigation(
        lines,
        requested_file_id=navigation_file_id,
        requested_subtext_id=navigation_subtext_id,
        mandaic_page_route=mandaic_page_route,
    )
    if (previous_subtext is not None or next_subtext is not None) and (
        requested_page != 1 or page_count is not None
    ):
        raise TextParseError(
            "CAL Ginza cross-subtext navigation must be on a single unpaginated page"
        )
    if requested_page is not None and page_number != requested_page:
        # CAL clamps an out-of-range page to its last page: the last "Page N of N" of a
        # paginated text, or the only page (no marker, no navigation) of a short text.
        last_page = page_count
        if page_count is None and previous_page is None and next_page is None:
            last_page = 1
        if last_page is not None and page_number == last_page and requested_page > last_page:
            raise CalOutOfRangeError(
                f"page {requested_page} is beyond the last page ({last_page}) of this text"
            )
        raise TextParseError("CAL text page number differs from the requested page")
    _validate_page_navigation(
        page_number=page_number,
        page_count=page_count,
        previous_page=previous_page,
        next_page=next_page,
        allow_navigation_without_page_count=mandaic_page_route,
    )
    expected_coordinate_prefix: str | None
    if requested_file_id == "74421" and requested_subtext_id == "col":
        expected_coordinate_prefix = "74421col"
    else:
        expected_coordinate_prefix = (
            f"{requested_file_id}{requested_subtext_id}"
            if requested_subtext_id is not None and has_subtext_letter_suffix(requested_subtext_id)
            else None
        )
    if (
        requested_subtext_id is None
        and requested_file_id in _MANDAIC_ALPHANUMERIC_COORDINATE_FILE_IDS
    ):
        expected_coordinate_prefix = requested_file_id
    if cal_file_sub is not None:
        # A split six-digit id is accepted from indirect evidence, so every row must also
        # carry the requested id as its coordinate prefix (R-046).
        expected_coordinate_prefix = requested_file_id
    table = _parse_text_table(response)
    if table.found:
        lexical_rows = tuple(_row_has_lexical_link(row) for row in table.rows)
        if any(lexical_rows) and not all(lexical_rows):
            raise TextParseError("CAL text table mixes linked and plain text rows")
        if lexical_rows and all(lexical_rows):
            text_lines = tuple(
                _text_line_from_row(
                    row,
                    response.url,
                    expected_coordinate_prefix=expected_coordinate_prefix,
                )
                for row in table.rows
            )
        elif table.rows:
            plain_coordinate_prefix = f"{requested_file_id}{requested_subtext_id or ''}"
            text_lines = tuple(
                _plain_text_line_from_row(
                    row,
                    response.url,
                    expected_coordinate_prefix=plain_coordinate_prefix,
                )
                for row in table.rows
            )
        else:
            text_lines = ()
    else:
        text_lines = tuple(
            parsed
            for line in lines
            if (
                parsed := _parse_text_line(
                    line,
                    response.url,
                    expected_coordinate_prefix=expected_coordinate_prefix,
                )
            )
            is not None
        )
    if not text_lines:
        raise TextParseError("CAL text page contains no recognizable coordinate/token rows")

    return TextPage(
        text=text_ref,
        page=page_number,
        page_count=page_count,
        total_lines=total_lines,
        previous_page=previous_page,
        next_page=next_page,
        lines=text_lines,
        previous_subtext_id=previous_subtext,
        next_subtext_id=next_subtext,
    )


class TextService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def catalogue(self, *, category_id: str | None = None) -> TextCatalogueResult:
        normalized_category = None if category_id is None else _validate_category_id(category_id)
        parser = parse_text_catalogue_page
        if normalized_category is None:
            request = CalRequest(method="GET", path="newtextmenu.html")
        elif normalized_category == _ONKELOS_JONATHAN_CATEGORY_ID:
            request = CalRequest(method="GET", path=_ONKELOS_JONATHAN_PATH)
        elif normalized_category == _MANDAIC_CATEGORY_ID:
            request = CalRequest(
                method="GET",
                path=_MANDAIC_CATALOGUE_PATH,
                params=(("R1", _MANDAIC_CATEGORY_ID),),
            )
            parser = parse_mandaic_catalogue_page
        elif normalized_category in _MANDAIC_SUBDIVIDED_FILE_IDS:
            request = CalRequest(
                method="GET",
                path="showsubtexts.php",
                params=(("subtext", normalized_category),),
            )

            def parser(response: CalResponse) -> TextCataloguePage:
                return _parse_mandaic_subtext_catalogue_page(
                    response,
                    requested_file_id=normalized_category,
                )

        else:
            request = CalRequest(
                method="GET",
                path="showsubtexts.php",
                params=(("subtext", normalized_category),),
            )

        result = await self._client.fetch(
            request,
            parser=parser,
            cache_namespace="text-catalogue-v1",
        )
        return TextCatalogueResult(
            categories=result.value.categories,
            texts=result.value.texts,
            provenance=TextProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="catalogue",
                category_id=normalized_category,
            ),
            specialized_collections=result.value.specialized_collections,
        )

    async def search(self, query: str) -> TextSearchResult:
        submitted = _prepare_text_search_query(query)
        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path="newsearchtxts.php",
                data=(("search", submitted),),
            ),
            parser=lambda response: parse_text_search_page(response, submitted_query=submitted),
            cache_namespace="text-search-v1",
        )
        return TextSearchResult(
            matches=result.value.matches,
            provenance=TextProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="search",
                original_query=query,
                submitted_query=submitted,
            ),
        )

    async def information(
        self,
        file_id: str,
        *,
        subtext_id: str | None = None,
    ) -> TextInformationResult:
        normalized_file = _validate_id(file_id, "file_id")
        if subtext_id is None:
            normalized_subtext = None
        elif normalized_file in _MANDAIC_SUBDIVIDED_FILE_IDS:
            normalized_subtext = _validate_mandaic_subtext_id(subtext_id)
        else:
            normalized_subtext = _validate_subtext_id(subtext_id)
        coord = (
            normalized_file
            if normalized_subtext is None
            else f"{normalized_file}{normalized_subtext}"
        )
        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="get_file_info.php",
                params=(("coord", coord),),
            ),
            parser=parse_text_information_page,
            cache_namespace="text-information-v1",
        )
        return TextInformationResult(
            status=result.value.status,
            file_id=normalized_file,
            subtext_id=normalized_subtext,
            metadata=result.value.metadata,
            provenance=TextProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="text_information",
                upstream_id=normalized_file,
                subtext_id=normalized_subtext,
            ),
        )

    async def line_comments(self, coordinate: str) -> TextLineCommentsResult:
        normalized_coordinate = _validate_line_comment_coordinate(coordinate)

        def parse_requested(response: CalResponse) -> TextLineCommentsPage:
            return parse_text_line_comments_page(
                response,
                requested_coordinate=normalized_coordinate,
            )

        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="comment.php",
                params=(("coord", normalized_coordinate),),
            ),
            parser=parse_requested,
            cache_namespace="text-line-comments-v1",
        )
        return TextLineCommentsResult(
            status=result.value.status,
            coordinate=normalized_coordinate,
            records=result.value.records,
            provenance=TextProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="line_comments",
                upstream_id=normalized_coordinate,
            ),
        )

    async def page(
        self,
        file_id: str,
        *,
        subtext_id: str | None = None,
        page: int = 1,
    ) -> TextPageResult:
        normalized_file = _validate_id(file_id, "file_id")
        if subtext_id is None:
            normalized_subtext = None
        elif normalized_file in _MANDAIC_SUBDIVIDED_FILE_IDS:
            normalized_subtext = _validate_mandaic_subtext_id(subtext_id)
        else:
            normalized_subtext = _validate_subtext_id(subtext_id)
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise CalInputError("page must be a positive integer")
        if normalized_file in _CPA_DIRECT_FILE_IDS and normalized_subtext is not None:
            raise CalInputError("direct CPA texts do not accept subtext_id")
        if normalized_file in _CPA_SUBDIVIDED_FILE_IDS and normalized_subtext is None:
            raise CalInputError("subdivided CPA texts require subtext_id")
        if normalized_file in _MANDAIC_SUBDIVIDED_FILE_IDS and normalized_subtext is None:
            raise CalInputError("subdivided Mandaic texts require subtext_id")
        if normalized_file in _MANDAIC_PAGINATED_DIRECT_FILE_IDS and normalized_subtext is not None:
            raise CalInputError("direct Mandaic texts do not accept subtext_id")

        mandaic_page_route = False
        if normalized_file in _MANDAIC_SUBDIVIDED_FILE_IDS:
            mandaic_page_route = True
            params = [
                ("cset", "M"),
                ("file", normalized_file),
                ("sub", normalized_subtext or ""),
            ]
            if page > 1:
                params.append(("page", str(page - 1)))
        elif normalized_file in _MANDAIC_PAGINATED_DIRECT_FILE_IDS:
            mandaic_page_route = True
            params = [("cset", "M"), ("file", normalized_file)]
            if page > 1:
                params.append(("page", str(page - 1)))
        elif normalized_subtext is None and normalized_file.startswith(_MANDAIC_COLLECTION_PREFIX):
            if page != 1:
                raise CalInputError("direct Mandaic texts currently support only page 1")
            params = [("cset", "M"), ("file", normalized_file)]
        else:
            params = [("file", normalized_file)]
            if normalized_subtext is not None:
                params.append(("sub", normalized_subtext))
            if normalized_file in _CPA_TEXT_FILE_IDS:
                params.append(("cset", "C"))
            params.append(("page", str(page - 1)))
        submitted_sub = next((value for name, value in params if name == "sub"), None)

        def parse_requested(response: CalResponse) -> TextPage | None:
            return _parse_text_page(
                response,
                requested_file_id=normalized_file,
                requested_subtext_id=normalized_subtext,
                requested_page=page,
                mandaic_page_route=mandaic_page_route,
                submitted_sub=submitted_sub,
            )

        result = await self._client.fetch(
            CalRequest(method="GET", path="get_a_chapter.php", params=tuple(params)),
            parser=parse_requested,
            cache_namespace="text-page-v1",
        )
        status = TextPageStatus.FOUND if result.value is not None else TextPageStatus.NOT_FOUND
        return TextPageResult(
            status=status,
            page=result.value,
            provenance=TextProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="page",
                upstream_id=normalized_file,
                subtext_id=normalized_subtext,
                page=page,
            ),
        )


def _validate_id(value: str, name: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise CalInputError(f"{name} must be a CAL decimal identifier")
    return value


def _is_cpa_node(value: str) -> bool:
    """A CPA catalogue node: an observed subdivided CPA file followed by a subtext (R-083).

    CAL addresses some CPA nodes with a letter-suffixed identifier such as ``5500056125a``.
    The identifier is opaque CAL data and is never split into a file and subtext.
    """

    file_id, subtext = value[:5], value[5:]
    return file_id in _CPA_SUBDIVIDED_FILE_IDS and is_cal_subtext_id(subtext)


def _is_suffixed_cpa_node(value: str) -> bool:
    return _ID_RE.fullmatch(value) is None and _is_cpa_node(value)


def _validate_category_id(value: str) -> str:
    if isinstance(value, str) and (_ID_RE.fullmatch(value) is not None or _is_cpa_node(value)):
        return value
    raise CalInputError(
        "category_id must be a CAL decimal identifier or a returned CPA node identifier "
        "such as 5500056125a"
    )


def _validate_subtext_id(value: str) -> str:
    if not is_cal_subtext_id(value):
        raise CalInputError(
            "subtext_id must be CAL decimal digits with an optional lowercase letter suffix"
        )
    return value


def _validate_mandaic_subtext_id(value: str) -> str:
    if value == "col":
        return value
    return _validate_subtext_id(value)


def _parse_mandaic_subtext_id(value: str) -> str:
    if value == "col":
        return value
    return _parse_subtext_id(value)


def _validate_line_comment_coordinate(value: str) -> str:
    if not isinstance(value, str) or _LINE_COMMENT_COORD_RE.fullmatch(value) is None:
        raise CalInputError("coordinate must be a 1-64 character ASCII alphanumeric CAL coordinate")
    return value


def _parse_id(value: str, name: str) -> str:
    if _ID_RE.fullmatch(value) is None:
        raise TextParseError(f"CAL returned a non-decimal {name}")
    return value


def _parse_subtext_id(value: str) -> str:
    if not is_cal_subtext_id(value):
        raise TextParseError(
            "CAL returned a subtext_id outside the digits-plus-optional-lowercase-suffix contract"
        )
    return value


def _parse_positive_id(value: str, name: str) -> str:
    parsed = _parse_id(value, name)
    if int(parsed) < 1:
        raise TextParseError(f"CAL returned a non-positive {name}")
    return parsed


def _prepare_text_search_query(value: str) -> str:
    trimmed = value.strip(" ")
    if not trimmed:
        raise CalInputError("CAL text search query must not be empty")
    if any(char.isspace() and char != " " for char in trimmed):
        raise CalInputError("CAL text search words must be separated by ASCII spaces")
    parts = [part for part in trimmed.split(" ") if part]
    if not parts:
        raise CalInputError("CAL text search query must not be empty")
    return " ".join(parts)


def _is_root_catalogue_response(url: str) -> bool:
    parsed = urlsplit(url)
    cal_root = urlsplit(CAL_BASE_URL)
    return (
        (parsed.scheme, parsed.netloc) == (cal_root.scheme, cal_root.netloc)
        and parsed.path == f"/{_ROOT_CATALOGUE_PATH}"
        and not parsed.query
        and not parsed.fragment
    )


def _specialized_collection_from_link(
    link: _Link,
) -> TextSpecializedCollectionRef | None:
    label = link.text.strip()
    parsed = urlsplit(link.href)
    exact_path = (
        not parsed.scheme
        and not parsed.netloc
        and parsed.path in (_SYRIAC_ROOT_PATH, f"/{_SYRIAC_ROOT_PATH}")
    )
    if exact_path:
        if parsed.query or parsed.fragment:
            raise TextParseError("CAL Syriac root route changed unexpectedly")
        if not label:
            raise TextParseError("CAL Syriac root collection link has no label")
        return TextSpecializedCollectionRef(
            collection_key=_SYRIAC_COLLECTION_KEY,
            label=label,
            follow_up_tool=_SYRIAC_FOLLOW_UP_TOOL,
            selector_name=_SYRIAC_SELECTOR_NAME,
            supported_selectors=syriac_text_category_slugs(),
        )
    if label == _SYRIAC_ROOT_LABEL:
        raise TextParseError("CAL Syriac root route changed unexpectedly")
    return None


def _requested_catalogue_node(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.path != "/showsubtexts.php":
        return None
    values = parse_qs(parsed.query, keep_blank_values=True).get("subtext")
    return values[0] if values is not None and len(values) == 1 else None


def _is_own_script_toggle(link: _Link, requested_node: str) -> bool:
    """CAL's "View in" control re-renders the same node in another script (R-082).

    It is navigation, not a sub-category, so only an exact ``subtext=<this node>&script=<X>``
    link is skipped; a script link to any other node is still parsed as before.
    """

    if not _is_path(link.href, "showsubtexts.php"):
        return False
    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    own_nodes = [[requested_node]]
    if _is_suffixed_cpa_node(requested_node):
        # A suffixed CPA node's toggle names its suffix-less form (R-083).
        own_nodes.append([requested_node[:-1]])
    return (
        set(query) == {"subtext", "script"}
        and query["subtext"] in own_nodes
        and len(query["script"]) == 1
        and _SCRIPT_TOGGLE_RE.fullmatch(query["script"][0]) is not None
    )


def _category_from_link(link: _Link) -> TextCategoryRef | None:
    label = link.text.strip()
    parsed = urlsplit(link.href)

    exact_mandaic_path = (
        not parsed.scheme
        and not parsed.netloc
        and parsed.path in (_MANDAIC_CATALOGUE_PATH, f"/{_MANDAIC_CATALOGUE_PATH}")
    )
    if exact_mandaic_path:
        query = parse_qs(parsed.query, keep_blank_values=True)
        if set(query) != {"R1"} or query.get("R1") != [_MANDAIC_CATEGORY_ID]:
            raise TextParseError("CAL Mandaic catalogue route changed unexpectedly")
        if not label:
            raise TextParseError("CAL Mandaic catalogue link has no label")
        return TextCategoryRef(category_id=_MANDAIC_CATEGORY_ID, label=label)
    if label == _MANDAIC_ROOT_LABEL:
        raise TextParseError("CAL Mandaic catalogue route changed unexpectedly")

    exact_dedicated_route = (
        not parsed.scheme
        and not parsed.netloc
        and parsed.path in (_ONKELOS_JONATHAN_PATH, f"/{_ONKELOS_JONATHAN_PATH}")
    )
    if exact_dedicated_route:
        if parsed.query:
            raise TextParseError("CAL Onkelos/Jonathan catalogue route changed unexpectedly")
        if not label:
            raise TextParseError("CAL Onkelos/Jonathan catalogue link has no label")
        return TextCategoryRef(category_id=_ONKELOS_JONATHAN_CATEGORY_ID, label=label)
    if label == _ONKELOS_JONATHAN_LABEL:
        raise TextParseError("CAL Onkelos/Jonathan catalogue route changed unexpectedly")

    if not _is_path(link.href, "showsubtexts.php"):
        return None
    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    category_id = _single_query_value(query, "subtext", "category")
    _parse_id(category_id, "category_id")
    if not label:
        raise TextParseError("CAL text catalogue category link has no label")
    return TextCategoryRef(category_id=category_id, label=label)


def _text_ref_from_link(
    link: _Link,
    *,
    label: str | None = None,
    description: str | None = None,
) -> TextRef | None:
    if not _is_path(link.href, "get_a_chapter.php"):
        return None
    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    file_id = _single_query_value(query, "file", "text")
    _parse_id(file_id, "file_id")

    subtext_id: str | None = None
    sub_values = query.get("sub")
    if file_id in _CPA_DIRECT_FILE_IDS:
        if set(query) != {"file", "cset"} or query.get("cset") != ["C"]:
            raise TextParseError("CAL direct CPA text link lacks the exact current cset=C route")
    elif file_id in _CPA_SUBDIVIDED_FILE_IDS and (
        set(query) != {"file", "sub", "cset"} or query.get("cset") != ["C"]
    ):
        raise TextParseError("CAL subdivided CPA text link lacks the exact current cset=C route")

    if sub_values is not None:
        if len(sub_values) != 1:
            raise TextParseError("CAL text link has repeated sub identifiers")
        if sub_values[0]:
            subtext_id = _parse_subtext_id(sub_values[0])
    if file_id in _CPA_SUBDIVIDED_FILE_IDS and subtext_id is None:
        raise TextParseError("CAL subdivided CPA text link lacks a subtext identifier")

    rendered_label = (label if label is not None else link.text).strip()
    if not rendered_label:
        raise TextParseError("CAL text link has no rendered label")
    return TextRef(
        file_id=file_id,
        subtext_id=subtext_id,
        label=rendered_label,
        description=description,
    )


def _mandaic_catalogue_item_from_link(
    line: _Line,
    link: _Link,
    source_url: str,
) -> TextCategoryRef | TextRef | None:
    parsed = urlsplit(link.href)
    endpoint: str | None = None
    selector: str | None = None
    if parsed.path.endswith("showsubtexts.php"):
        endpoint = "showsubtexts.php"
        selector = "subtext"
    elif parsed.path.endswith("get_a_chapter.php"):
        endpoint = "get_a_chapter.php"
        selector = "file"
    else:
        return None

    if parsed.path not in (endpoint, f"/{endpoint}"):
        raise TextParseError("CAL Mandaic catalogue child route path changed unexpectedly")

    source = urlsplit(source_url)
    resolved = urlsplit(urljoin(source_url, link.href))
    if (resolved.scheme, resolved.netloc) != (source.scheme, source.netloc):
        raise TextParseError("CAL Mandaic catalogue child route changed origin")

    query = parse_qs(parsed.query, keep_blank_values=True)
    expected_keys = {"cset", selector}
    if set(query) != expected_keys:
        raise TextParseError("CAL Mandaic catalogue child query changed unexpectedly")
    # ``cset`` selects only the rendering script: current CAL links Roman (``R``), the
    # earlier layout Standard Transliteration (``M``). CAL-MCP never asks for ``J``.
    if query.get("cset") not in (["R"], ["M"]):
        raise TextParseError("CAL Mandaic catalogue child cset changed unexpectedly")
    file_id = _single_query_value(query, selector, "Mandaic catalogue")
    _parse_positive_id(file_id, "file_id")

    anchor = link.text.strip()
    if not anchor or anchor not in line.text:
        raise TextParseError("CAL Mandaic catalogue file link has no rendered title")
    if query.get("cset") == ["M"]:
        # Earlier layout: the link shows the file identifier and the title follows it.
        if anchor != file_id:
            raise TextParseError("CAL Mandaic catalogue file link is detached or mislabeled")
        rendered_label = line.text.replace(anchor, "", 1).strip()
    else:
        # Current layout: the link text is the title and the row shows nothing else.
        if anchor.isdigit() or line.text.strip() != anchor:
            raise TextParseError("CAL Mandaic catalogue title row has unexpected text")
        rendered_label = anchor
    if not rendered_label:
        raise TextParseError("CAL Mandaic catalogue file row has no rendered label")
    for other in line.links:
        if other is link or not _is_path(other.href, "get_file_info.php"):
            continue
        info_query = parse_qs(urlsplit(other.href).query, keep_blank_values=True)
        if _single_query_value(info_query, "coord", "Mandaic catalogue") != file_id:
            raise TextParseError("CAL Mandaic catalogue information link names another file")
    if endpoint == "showsubtexts.php":
        return TextCategoryRef(category_id=file_id, label=rendered_label)
    return TextRef(file_id=file_id, subtext_id=None, label=rendered_label)


def _parse_mandaic_subtext_catalogue_page(
    response: CalResponse,
    *,
    requested_file_id: str,
) -> TextCataloguePage:
    parsed_response = urlsplit(response.url)
    if parsed_response.path != "/showsubtexts.php":
        raise TextParseError("CAL Mandaic subtext catalogue endpoint changed unexpectedly")
    response_query = parse_qs(parsed_response.query, keep_blank_values=True)
    if set(response_query) != {"subtext"} or response_query.get("subtext") != [requested_file_id]:
        raise TextParseError("CAL Mandaic subtext catalogue selector changed unexpectedly")

    texts: list[TextRef] = []
    seen_subtexts: set[str] = set()
    for line in _parse_lines(response):
        chapter_links = [link for link in line.links if _is_path(link.href, "get_a_chapter.php")]
        if len(chapter_links) > 1:
            raise TextParseError("CAL Mandaic subtext row exposes multiple text routes")
        if not chapter_links:
            continue
        link = chapter_links[0]
        parsed = urlsplit(link.href)
        if (
            parsed.scheme
            or parsed.netloc
            or parsed.fragment
            or parsed.path
            not in {
                "get_a_chapter.php",
                "/get_a_chapter.php",
            }
        ):
            raise TextParseError("CAL Mandaic subtext route changed unexpectedly")
        query = parse_qs(parsed.query, keep_blank_values=True)
        if set(query) != {"file", "sub", "cset"}:
            raise TextParseError("CAL Mandaic subtext route has unexpected selectors")
        if query.get("file") != [requested_file_id]:
            raise TextParseError("CAL Mandaic subtext route names another file")
        if query.get("cset") != ["J"]:
            raise TextParseError("CAL Mandaic subtext route has an unexpected cset")
        subtext_id = _parse_mandaic_subtext_id(_single_query_value(query, "sub", "Mandaic subtext"))
        if subtext_id in seen_subtexts:
            raise TextParseError("CAL Mandaic subtext catalogue repeats a subtext")
        seen_subtexts.add(subtext_id)
        label = link.text.strip()
        if not label:
            raise TextParseError("CAL Mandaic subtext route has no rendered label")

        info_links = [link for link in line.links if _is_path(link.href, "get_file_info.php")]
        if len(info_links) > 1:
            raise TextParseError("CAL Mandaic subtext row exposes multiple information links")
        if info_links:
            info = urlsplit(info_links[0].href)
            if (
                info.scheme
                or info.netloc
                or info.fragment
                or info.path
                not in {
                    "get_file_info.php",
                    "/get_file_info.php",
                }
            ):
                raise TextParseError("CAL Mandaic subtext information route changed unexpectedly")
            info_query = parse_qs(info.query, keep_blank_values=True)
            if set(info_query) - {"coord", "return", "script"}:
                raise TextParseError(
                    "CAL Mandaic subtext information link has unexpected selectors"
                )
            # Rows normally name file + subtext; Ginza (74410) rows name the parent file (R-076).
            if _single_query_value(info_query, "coord", "Mandaic subtext information") not in {
                requested_file_id + subtext_id,
                requested_file_id,
            }:
                raise TextParseError(
                    "CAL Mandaic subtext information coordinate names another text"
                )

        texts.append(
            TextRef(
                file_id=requested_file_id,
                subtext_id=subtext_id,
                label=label,
            )
        )

    raw_route_links = _count_mandaic_chapter_route_links(response)
    if raw_route_links != len(texts):
        raise TextParseError("CAL Mandaic subtext catalogue has a route without a rendered title")
    if not texts:
        raise TextParseError("CAL Mandaic subtext catalogue contains no recognizable text rows")
    return TextCataloguePage(categories=(), texts=tuple(texts))


def _search_text_ref_from_link(
    link: _Link,
    *,
    label: str,
    description: str | None,
) -> TextSearchMatch | None:
    ordinary = _text_ref_from_link(link, label=label, description=description)
    if ordinary is not None:
        return _search_match(ordinary)
    if not _is_path(link.href, "showsubtexts.php"):
        return None

    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    subtext_values = query.get("subtext")
    if subtext_values is None or len(subtext_values) != 1:
        raise TextParseError("CAL text search subtext result has an invalid file identifier")
    # A showsubtexts.php result is a catalogue node. Mandaic uses its own script
    # selectors (M/R), CPA nodes use C (R-083), and the other collections use the shared
    # script set (R-056).
    identifier = subtext_values[0]
    cset_values = query.get("cset") or []
    cset = cset_values[0] if len(cset_values) == 1 else None
    if _ID_RE.fullmatch(identifier) is None and not (
        cset in _CPA_SEARCH_CSETS and _is_cpa_node(identifier)
    ):
        raise TextParseError("CAL text search subtext result has an invalid file identifier")
    mandaic = identifier.startswith(_MANDAIC_COLLECTION_PREFIX)
    cpa = _is_cpa_node(identifier)
    if (
        (mandaic and cset in _MANDAIC_SEARCH_CSETS)
        or (cpa and cset in _CPA_SEARCH_CSETS)
        or (not mandaic and cset in _SCRIPT_CSETS)
    ):
        file_id, category_id, tool = None, identifier, _FOLLOW_UP_CATALOGUE
    else:
        raise TextParseError("CAL text search subtext result has an invalid cset")

    rendered_label = label.strip()
    if not rendered_label:
        raise TextParseError("CAL text search subtext result has no rendered label")
    return TextSearchMatch(
        file_id=file_id,
        subtext_id=None,
        category_id=category_id,
        label=rendered_label,
        description=description,
        follow_up_tool=tool,
    )


def _search_match(text: TextRef) -> TextSearchMatch:
    return TextSearchMatch(
        file_id=text.file_id,
        subtext_id=text.subtext_id,
        category_id=None,
        label=text.label,
        description=text.description,
        follow_up_tool=_FOLLOW_UP_TEXT_PAGE,
    )


def _search_label_and_description(line: _Line, link: _Link) -> tuple[str, str | None]:
    if not link.text or link.text not in line.text:
        raise TextParseError("CAL text search link is detached from its result row")
    remainder = line.text.split(link.text, 1)[1].strip()
    if not remainder.startswith(":"):
        raise TextParseError("CAL text search result row is missing the file/label separator")
    remainder = remainder[1:].strip()
    if not remainder:
        raise TextParseError("CAL text search result row has no text label")
    # CAL separates label and description with ": "; a colon inside a label (a verse range
    # such as "John 13:15-16:9") has no following space (R-083).
    label, separator, description = _partition_label_separator(remainder)
    label = label.strip()
    if not label:
        raise TextParseError("CAL text search result row has an empty text label")
    rendered_description = description.strip() if separator and description.strip() else None
    return label, rendered_description


def _partition_label_separator(text: str) -> tuple[str, str, str]:
    # A ": " inside a parenthesized label (``JElet (Jacob of Edessa: Letter …)``) is part of
    # the label (R-085). When the row's parentheses do not balance there is no trustworthy
    # depth, so the first separator is used as before.
    separators = list(_SEARCH_LABEL_SEPARATOR_RE.finditer(text))
    depths = _parenthesis_depths(text)
    if depths is not None:
        separators = [match for match in separators if depths[match.start()] == 0]
    if not separators:
        return text, "", ""
    match = separators[0]
    return text[: match.start()], ":", text[match.end() :]


def _parenthesis_depths(text: str) -> list[int] | None:
    """Parenthesis depth before each character, or ``None`` if the text is unbalanced."""

    depths: list[int] = []
    depth = 0
    for character in text:
        depths.append(depth)
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                return None
    return depths if depth == 0 else None


def _page_text_ref(
    lines: list[_Line],
    requested_file_id: str,
    requested_subtext_id: str | None,
    *,
    submitted_sub: str | None,
) -> tuple[TextRef, tuple[str, str] | None]:
    # Current CAL (2026-09-25) renders the file-info coordinate of a subdivided page as the
    # file identifier followed by the submitted ``sub`` value. The bare file identifier is
    # still accepted only for the earlier (pre-2026-09-25) layout. Anything else names a
    # different file or subtext.
    accepted_coords = {requested_file_id}
    if submitted_sub is not None:
        accepted_coords.add(requested_file_id + submitted_sub)
    for line in lines:
        for link in line.links:
            if not _is_path(link.href, "get_file_info.php"):
                continue
            query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
            coord = _single_query_value(query, "coord", "file-info")
            if coord not in accepted_coords:
                raise TextParseError(
                    "CAL text page file identifier differs from the requested file"
                )
            file_id = requested_file_id
            prefix, separator, label = link.text.partition(":")
            if not separator or not label.strip():
                raise TextParseError("CAL text page file-info label is malformed")
            cal_file_sub: tuple[str, str] | None = None
            if prefix.strip() != file_id:
                if submitted_sub is not None or not _is_linked_file_sub_split(
                    lines, file_id, prefix.strip()
                ):
                    raise TextParseError("CAL text page file-info label is malformed")
                cal_file_sub = (prefix.strip(), file_id.removeprefix(prefix.strip()))
            text_ref = TextRef(
                file_id=file_id,
                subtext_id=requested_subtext_id,
                label=label.strip(),
            )
            return text_ref, cal_file_sub
    raise TextParseError("CAL text page is missing its file-information link")


def _is_linked_file_sub_split(lines: list[_Line], file_id: str, label_prefix: str) -> bool:
    # CAL lists some Syriac texts under a six-digit id that is its file plus subtext
    # (634081 = file 63408, sub 1). The file-info label then shows only the file. The split
    # is accepted only when the page's own text links name exactly that file and sub (R-046).
    sub = file_id.removeprefix(label_prefix)
    if (
        not label_prefix.isascii()
        or not label_prefix.isdecimal()
        or not file_id.startswith(label_prefix)
        or not sub
        or not sub.isdecimal()
    ):
        return False
    linked: set[tuple[str, str]] = set()
    for line in lines:
        for link in line.links:
            if not _is_path(link.href, "get_a_chapter.php"):
                continue
            query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
            files = query.get("file", [])
            subs = query.get("sub", [])
            if len(files) != 1 or len(subs) > 1:
                return False
            linked.add((files[0], subs[0] if subs else ""))
    named = {pair for pair in linked if pair[1]}
    return named == {(label_prefix, sub)}


def _page_metadata(lines: list[_Line]) -> tuple[int, int | None, int | None]:
    # Current CAL renders the marker in the same line as the previous/next/show-all
    # links and the variants toggle, and a second copy without the line total. The
    # marker is what remains of a non-token line once its link texts are removed.
    page_count: tuple[int, int] | None = None
    total: int | None = None
    for line in lines:
        if any(_is_lexical_link(link) for link in line.links):
            continue
        residue = line.text
        for link in line.links:
            residue = residue.replace(link.text, " ", 1)
        residue = " ".join(residue.split())
        match = _PAGE_MARKER_RE.fullmatch(residue)
        if match is None:
            if _PAGE_MARKER_ANYWHERE_RE.search(residue) is not None:
                raise TextParseError("CAL text page has a malformed pagination marker")
            continue
        candidate = (int(match.group("page")), int(match.group("count")))
        if candidate[0] < 1 or candidate[1] < candidate[0]:
            raise TextParseError("CAL text page has invalid pagination metadata")
        if page_count is not None and page_count != candidate:
            raise TextParseError("CAL text page exposes conflicting pagination metadata")
        page_count = candidate
        if match.group("total") is not None:
            candidate_total = int(match.group("total"))
            if total is not None and total != candidate_total:
                raise TextParseError("CAL text page exposes conflicting pagination metadata")
            total = candidate_total
    if page_count is None:
        return 1, None, None
    return page_count[0], page_count[1], total


def _page_navigation(
    lines: list[_Line],
    *,
    requested_file_id: str,
    requested_subtext_id: str | None,
    mandaic_page_route: bool = False,
) -> tuple[int | None, int | None, str | None, str | None]:
    previous: int | None = None
    next_page: int | None = None
    previous_subtext: str | None = None
    next_subtext: str | None = None
    for line in lines:
        for link in line.links:
            if not _is_path(link.href, "get_a_chapter.php"):
                continue
            label = link.text.lower()
            if "previous page" not in label and "next page" not in label:
                continue
            query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
            file_id = _single_query_value(query, "file", "page-navigation")
            _parse_id(file_id, "file_id")
            if file_id != requested_file_id:
                raise TextParseError("CAL text page navigation file differs from requested file")

            if mandaic_page_route:
                core_keys = frozenset({"file", "sub", "cset", "page"})
                with_clen_keys = core_keys | {"clen"}
                if frozenset(query) not in {core_keys, with_clen_keys}:
                    raise TextParseError("CAL Mandaic text navigation has unexpected selectors")
                if query.get("cset") != ["M"]:
                    raise TextParseError("CAL text page navigation cset differs from Mandaic route")
                expected_sub = requested_subtext_id or ""
                actual_sub = query.get("sub")
                if actual_sub != [expected_sub]:
                    # CAL's Ginza 74410 "next page" moves to the next
                    # Petermann-page *subtext*, not page 2 within subtext 001.
                    # Only this evidenced file may use that navigation.
                    if requested_file_id != "74410" or requested_subtext_id is None:
                        raise TextParseError(
                            "CAL text page navigation subtext differs from requested subtext"
                        )
                    source_link = urlsplit(link.href)
                    if (
                        source_link.scheme
                        or source_link.netloc
                        or source_link.path != "get_a_chapter.php"
                    ):
                        raise TextParseError("CAL Ginza subtext navigation changed origin or path")
                    if "clen" in query and query.get("clen") != ["5"]:
                        raise TextParseError(
                            "CAL Mandaic text navigation has an unexpected clen"
                        )
                    upstream_page = _single_query_value(query, "page", "page-navigation")
                    if upstream_page != "0":
                        raise TextParseError(
                            "CAL Ginza cross-subtext navigation must target private page zero"
                        )
                    if (
                        actual_sub is None
                        or len(actual_sub) != 1
                        or not actual_sub[0].isascii()
                        or not actual_sub[0].isdecimal()
                        or not requested_subtext_id.isascii()
                        or not requested_subtext_id.isdecimal()
                        or len(actual_sub[0]) != len(requested_subtext_id)
                    ):
                        raise TextParseError("CAL Ginza navigation target subtext is malformed")
                    label_text = " ".join(link.text.split()).casefold()
                    if label_text not in {"next page", "previous page"}:
                        raise TextParseError("CAL Ginza navigation direction changed")
                    current_number = int(requested_subtext_id)
                    adjacent = current_number + (1 if label_text == "next page" else -1)
                    if adjacent < 1 or int(actual_sub[0]) != adjacent:
                        raise TextParseError("CAL Ginza navigation target subtext is not adjacent")
                    if previous is not None or next_page is not None:
                        raise TextParseError("CAL Ginza page mixes pagination and subtext links")
                    if label_text == "next page":
                        if next_subtext is not None:
                            raise TextParseError("CAL Ginza has duplicate next-subtext links")
                        next_subtext = actual_sub[0]
                    else:
                        if previous_subtext is not None:
                            raise TextParseError("CAL Ginza has duplicate previous-subtext links")
                        previous_subtext = actual_sub[0]
                    continue
                if previous_subtext is not None or next_subtext is not None:
                    raise TextParseError("CAL Ginza page mixes pagination and subtext links")
                if "clen" in query and query.get("clen") != ["5"]:
                    raise TextParseError("CAL Mandaic text navigation has an unexpected clen")
                upstream_page = _single_query_value(query, "page", "page-navigation")
                if not upstream_page.isascii() or not upstream_page.isdecimal():
                    raise TextParseError("CAL text page navigation has a nonnumeric page")
                public_page = int(upstream_page) + 1
            else:
                if requested_file_id in _CPA_TEXT_FILE_IDS:
                    if requested_subtext_id is None:
                        core_route = set(query) == {"file", "page", "cset"}
                        paginated_direct_route = (
                            requested_file_id in _CPA_PAGINATED_DIRECT_FILE_IDS
                            and set(query) == {"file", "page", "cset", "sub", "clen"}
                            and query.get("sub") == [""]
                            and query.get("clen") == ["5"]
                        )
                        exact_cpa_route = core_route or paginated_direct_route
                    else:
                        exact_cpa_route = set(query) == {"file", "page", "cset", "sub"}
                    if not exact_cpa_route or query.get("cset") != ["C"]:
                        raise TextParseError(
                            "CAL CPA text navigation lacks the exact current cset=C route"
                        )

                subtext_id: str | None = None
                sub_values = query.get("sub")
                if sub_values is not None:
                    if len(sub_values) != 1:
                        raise TextParseError(
                            "CAL text page navigation has repeated sub identifiers"
                        )
                    if sub_values[0]:
                        subtext_id = _parse_subtext_id(sub_values[0])
                if subtext_id != requested_subtext_id:
                    raise TextParseError(
                        "CAL text page navigation subtext differs from requested subtext"
                    )
                upstream_page = _single_query_value(query, "page", "page-navigation")
                if not upstream_page.isdigit():
                    raise TextParseError("CAL text page navigation has a nonnumeric page")
                public_page = int(upstream_page) + 1

            if "previous page" in label:
                previous = _same_or_unset(previous, public_page, "previous")
            if "next page" in label:
                next_page = _same_or_unset(next_page, public_page, "next")
    return previous, next_page, previous_subtext, next_subtext


def _validate_page_navigation(
    *,
    page_number: int,
    page_count: int | None,
    previous_page: int | None,
    next_page: int | None,
    allow_navigation_without_page_count: bool = False,
) -> None:
    if page_count is None and not allow_navigation_without_page_count:
        if previous_page is not None or next_page is not None:
            raise TextParseError("CAL text page has navigation without pagination metadata")
        return

    if previous_page is not None and previous_page != page_number - 1:
        raise TextParseError("CAL text page has inconsistent previous-page navigation")
    if next_page is not None and next_page != page_number + 1:
        raise TextParseError("CAL text page has inconsistent next-page navigation")
    if previous_page is not None and previous_page < 1:
        raise TextParseError("CAL text page previous-page navigation is out of range")
    if page_count is not None and next_page is not None and next_page > page_count:
        raise TextParseError("CAL text page next-page navigation is out of range")


@dataclass(slots=True)
class _TableCell:
    loose_parts: list[str]
    links: list[_Link]


@dataclass(frozen=True, slots=True)
class _TextTable:
    found: bool
    rows: tuple[tuple[_TableCell, ...], ...]


class _TextTableParser(HTMLParser):
    """Read CAL's current ``text-display`` table: one text line per ``<tr>``.

    CAL does not close the table; the next ``<table>`` (page navigation) or ``</table>``
    ends it. Lexical links anywhere outside a text row are recorded so they fail closed.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found = False
        self.rows: list[tuple[_TableCell, ...]] = []
        self.lexical_links_outside_rows = 0
        self._in_table = False
        self._row: list[_TableCell] | None = None
        self._cell: _TableCell | None = None
        self._link_href: str | None = None
        self._link_parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        attributes = {key: value or "" for key, value in attrs}
        if self._cell is not None and tag not in _TEXT_CELL_TAGS:
            # A tag-shaped editorial bracket (``<wmr>``) would otherwise vanish silently.
            raise TextParseError("CAL text row has an unexpected element")
        if tag == "table":
            self._end_row()
            self._in_table = "text-display" in attributes.get("class", "").split()
            self.found = self.found or self._in_table
        elif tag == "tr" and self._in_table:
            self._end_row()
            self._row = []
        elif tag == "th" and self._row is not None:
            raise TextParseError("CAL text table has an unexpected header cell")
        elif tag == "td" and self._row is not None:
            self._end_cell()
            self._cell = _TableCell(loose_parts=[], links=[])
        elif tag == "a":
            href = attributes.get("href", "")
            if self._cell is None:
                if _is_lexical_href(href):
                    self.lexical_links_outside_rows += 1
                return
            if self._link_href is not None:
                raise TextParseError("CAL text row has a nested link")
            self._link_href = href
            self._link_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if self._ignored_depth:
            return
        if tag == "a" and self._link_href is not None and self._cell is not None:
            self._cell.links.append(
                _Link(href=self._link_href, text=_clean_text("".join(self._link_parts)))
            )
            self._link_href = None
        elif tag in {"td", "th"}:
            self._end_cell()
        elif tag == "tr":
            self._end_row()
        elif tag == "table":
            self._end_row()
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._cell is None:
            if self._row is not None and data.strip():
                raise TextParseError("CAL text row has text outside its cells")
            return
        if self._link_href is not None:
            self._link_parts.append(data)
        else:
            self._cell.loose_parts.append(data)

    def close(self) -> None:
        super().close()
        self._end_row()

    def _end_cell(self) -> None:
        if self._link_href is not None:
            raise TextParseError("CAL text row has an unclosed link")
        if self._cell is not None and self._row is not None:
            self._row.append(self._cell)
        self._cell = None

    def _end_row(self) -> None:
        self._end_cell()
        if self._row:
            self.rows.append(tuple(self._row))
        self._row = None


def _parse_text_table(response: CalResponse) -> _TextTable:
    parser = _TextTableParser()
    # CAL renders some editorial angle brackets in token text unescaped (``<w)th</a>``).
    # Such a ``<`` never starts a real tag, so it is text; without escaping, the HTML
    # parser would swallow the link end and merge the rest of the line into one token.
    body = _RAW_TEXT_LT_RE.sub("&lt;", response.body.decode("utf-8", errors="replace"))
    parser.feed(body)
    parser.close()
    if parser.found and parser.lexical_links_outside_rows:
        raise TextParseError("CAL text page has lexical links outside its text rows")
    return _TextTable(found=parser.found, rows=tuple(parser.rows))


def _row_has_lexical_link(row: tuple[_TableCell, ...]) -> bool:
    return any(_is_lexical_link(link) for cell in row for link in cell.links)


def _plain_text_line_from_row(
    row: tuple[_TableCell, ...],
    source_url: str,
    *,
    expected_coordinate_prefix: str,
) -> TextLine:
    if len(row) != 2:
        raise TextParseError("CAL plain text row does not have exactly two cells")
    coordinate_cell, text_cell = row

    if text_cell.links:
        raise TextParseError("CAL plain text row text cell unexpectedly contains a link")
    text = _clean_text("".join(text_cell.loose_parts))
    if not text:
        raise TextParseError("CAL plain text row has no rendered text")

    coordinate: str | None = None
    comment_url: str | None = None
    if not coordinate_cell.links:
        display_coordinate = _clean_text("".join(coordinate_cell.loose_parts))
        if not display_coordinate:
            raise TextParseError("CAL plain text row has no display coordinate")
    else:
        if len(coordinate_cell.links) != 1:
            raise TextParseError("CAL plain text row coordinate cell must contain exactly one link")
        if _clean_text("".join(coordinate_cell.loose_parts)):
            raise TextParseError(
                "CAL plain text row has loose display text outside its coordinate link"
            )
        link = coordinate_cell.links[0]
        parsed_href = urlsplit(link.href)
        if (
            parsed_href.scheme
            or parsed_href.netloc
            or parsed_href.fragment
            or parsed_href.path not in {"comment.php", "/comment.php"}
        ):
            raise TextParseError("CAL plain text row coordinate cell has an unexpected link")
        query = parse_qs(parsed_href.query, keep_blank_values=True)
        if set(query) != {"coord"}:
            raise TextParseError("CAL plain text row comment link has unexpected selectors")
        coordinate = _single_query_value(query, "coord", "plain-text-comment")
        if not is_cal_machine_coordinate(coordinate):
            raise TextParseError("CAL plain text row comment has an invalid coordinate")
        coordinate_tail = coordinate[len(expected_coordinate_prefix) :]
        if (
            not coordinate.startswith(expected_coordinate_prefix)
            or not coordinate_tail
            or not coordinate_tail.isdigit()
        ):
            raise TextParseError(
                "CAL plain text row comment coordinate differs from the requested text identity"
            )
        display_coordinate = _clean_text(link.text)
        if not display_coordinate:
            raise TextParseError("CAL plain text row has no display coordinate")
        comment_url = urljoin(source_url, link.href)

    return TextLine(
        coordinate=coordinate,
        display_coordinate=display_coordinate,
        text=text,
        tokens=(),
        comment_url=comment_url,
        empty_word_indexes=(),
    )


def _parse_text_machine_coordinate(
    value: str,
    *,
    expected_coordinate_prefix: str | None,
    require_positive_decimal: bool = False,
) -> str:
    if expected_coordinate_prefix is None:
        if require_positive_decimal:
            return _parse_positive_id(value, "coordinate")
        return _parse_id(value, "coordinate")
    if expected_coordinate_prefix in _MANDAIC_SPECIAL_COORDINATE_PREFIXES:
        if not is_cal_mandaic_machine_coordinate(value):
            raise TextParseError("CAL returned an invalid special-Mandaic machine coordinate")
        if not value.startswith(expected_coordinate_prefix):
            raise TextParseError("CAL text coordinate differs from the requested Mandaic text")
        return value
    if not is_cal_machine_coordinate(value):
        raise TextParseError("CAL returned an invalid machine coordinate")
    if not value.startswith(expected_coordinate_prefix):
        raise TextParseError("CAL text coordinate differs from the requested subtext")
    tail = value[len(expected_coordinate_prefix) :]
    if not tail or not tail.isdigit():
        raise TextParseError("CAL text coordinate lacks a decimal tail after its subtext")
    return value


def _empty_word_slot(
    link: _Link,
    *,
    expected_coordinate_prefix: str | None = None,
) -> tuple[str, int]:
    """Validate one current CAL empty lexical slot and return coordinate/index."""

    parsed_href = urlsplit(link.href)
    if (
        parsed_href.scheme
        or parsed_href.netloc
        or parsed_href.fragment
        or parsed_href.path != "getlex.php"
    ):
        raise TextParseError("CAL text row has an unexpected empty lexical-link route")
    query = parse_qs(parsed_href.query, keep_blank_values=True)
    if set(query) != {"coord", "word", "hasvariant"}:
        raise TextParseError("CAL text row empty lexical link has unexpected selectors")

    coordinate = _single_query_value(query, "coord", "empty-word-slot")
    _parse_text_machine_coordinate(
        coordinate,
        expected_coordinate_prefix=expected_coordinate_prefix,
        require_positive_decimal=True,
    )

    word = _single_query_value(query, "word", "empty-word-slot")
    if not word.isdigit():
        raise TextParseError("CAL text row empty lexical link has a nonnumeric word index")
    word_index = int(word)

    if query.get("hasvariant") != ["0"]:
        raise TextParseError("CAL text row empty lexical link must use hasvariant=0")
    return coordinate, word_index


def _text_line_from_row(
    row: tuple[_TableCell, ...],
    source_url: str,
    *,
    expected_coordinate_prefix: str | None = None,
) -> TextLine:
    if len(row) != 2:
        raise TextParseError("CAL text row does not have exactly two cells")
    coordinate_cell, token_cell = row

    if _clean_text("".join(token_cell.loose_parts)):
        raise TextParseError("CAL text row token cell has text outside its token links")
    if not token_cell.links:
        raise TextParseError("CAL text row has no token links")

    tokens: list[TextToken] = []
    empty_slots: list[tuple[str, int]] = []
    for link in token_cell.links:
        if link.text.strip():
            token = _token_from_link(
                link,
                source_url,
                expected_coordinate_prefix=expected_coordinate_prefix,
            )
            if token is None:
                raise TextParseError("CAL text row token cell has a non-lexical link")
            tokens.append(token)
        else:
            empty_slots.append(
                _empty_word_slot(
                    link,
                    expected_coordinate_prefix=expected_coordinate_prefix,
                )
            )

    coordinates = [token.coordinate for token in tokens]
    coordinates.extend(coordinate for coordinate, _index in empty_slots)
    coordinate = coordinates[0]
    if any(candidate != coordinate for candidate in coordinates[1:]):
        raise TextParseError("CAL text row mixes multiple machine coordinates")

    empty_word_indexes = [index for _coordinate, index in empty_slots]
    if len(set(empty_word_indexes)) != len(empty_word_indexes):
        raise TextParseError("CAL text row has a duplicate empty word index")
    rendered_word_indexes = {token.word_index for token in tokens}
    if rendered_word_indexes.intersection(empty_word_indexes):
        raise TextParseError("CAL text row empty word index collides with a rendered token")

    comment_link: _Link | None = None
    for link in coordinate_cell.links:
        if _is_path(link.href, "comment.php") or _is_path(link.href, "ask_ai_prompt.php"):
            query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
            link_coordinate = _single_query_value(query, "coord", "text-row")
            _parse_text_machine_coordinate(
                link_coordinate,
                expected_coordinate_prefix=expected_coordinate_prefix,
            )
            if link_coordinate != coordinate:
                raise TextParseError("CAL text row comment/Ask-AI link names another coordinate")
            if _is_path(link.href, "comment.php"):
                if comment_link is not None:
                    raise TextParseError("CAL text row has repeated comment links")
                comment_link = link
            continue
        raise TextParseError("CAL text row coordinate cell has an unexpected link")

    loose_coordinate = _clean_text("".join(coordinate_cell.loose_parts))
    if comment_link is not None:
        if loose_coordinate:
            raise TextParseError("CAL text row coordinate cell has text outside its comment link")
        display_coordinate = comment_link.text or None
        comment_url: str | None = urljoin(source_url, comment_link.href)
    else:
        display_coordinate = loose_coordinate or None
        comment_url = None

    rendered_text = " ".join(token.text for token in tokens)
    return TextLine(
        coordinate=coordinate,
        display_coordinate=display_coordinate,
        text=rendered_text,
        tokens=tuple(tokens),
        comment_url=comment_url,
        empty_word_indexes=tuple(empty_word_indexes),
    )


def _parse_text_line(
    line: _Line,
    source_url: str,
    *,
    expected_coordinate_prefix: str | None = None,
) -> TextLine | None:
    tokens = tuple(
        token
        for link in line.links
        if (
            token := _token_from_link(
                link,
                source_url,
                expected_coordinate_prefix=expected_coordinate_prefix,
            )
        )
        is not None
    )
    if not tokens:
        return None

    coordinate = tokens[0].coordinate
    if any(token.coordinate != coordinate for token in tokens):
        raise TextParseError("CAL text row mixes multiple machine coordinates")

    comment_link = _matching_comment_link(
        line.links,
        coordinate,
        expected_coordinate_prefix=expected_coordinate_prefix,
    )
    if comment_link is not None:
        display_coordinate = comment_link.text.strip() or None
        if display_coordinate is None or not line.text.startswith(display_coordinate):
            raise TextParseError("CAL text row comment coordinate is detached from its text")
        rendered_text = line.text[len(display_coordinate) :].strip()
        comment_url = urljoin(source_url, comment_link.href)
    else:
        first_token_text = tokens[0].text
        token_position = line.text.find(first_token_text)
        if token_position < 0:
            raise TextParseError("CAL text row token is detached from its rendered text")
        display_coordinate = line.text[:token_position].strip() or None
        rendered_text = line.text[token_position:].strip()
        comment_url = None

    if not rendered_text:
        raise TextParseError("CAL text row has no rendered text after its coordinate")
    return TextLine(
        coordinate=coordinate,
        display_coordinate=display_coordinate,
        text=rendered_text,
        tokens=tokens,
        comment_url=comment_url,
    )


def _is_lexical_href(href: str) -> bool:
    return _is_path(href, "bablex.php") or _is_path(href, "getlex.php")


def _is_lexical_link(link: _Link) -> bool:
    return _is_lexical_href(link.href)


def _token_from_link(
    link: _Link,
    source_url: str,
    *,
    expected_coordinate_prefix: str | None = None,
) -> TextToken | None:
    if not _is_lexical_href(link.href):
        return None
    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    coordinate = _single_query_value(query, "coord", "token")
    word = _single_query_value(query, "word", "token")
    _parse_text_machine_coordinate(
        coordinate,
        expected_coordinate_prefix=expected_coordinate_prefix,
    )
    if not word.isdigit():
        raise TextParseError("CAL lexical token link has a nonnumeric word index")
    text = link.text.strip()
    if not text:
        raise TextParseError("CAL lexical token link has no rendered token")
    return TextToken(
        coordinate=coordinate,
        word_index=int(word),
        text=text,
        lexical_url=urljoin(source_url, link.href),
    )


def _matching_comment_link(
    links: tuple[_Link, ...],
    coordinate: str,
    *,
    expected_coordinate_prefix: str | None = None,
) -> _Link | None:
    found: _Link | None = None
    for link in links:
        if not _is_path(link.href, "comment.php"):
            continue
        query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
        comment_coordinate = _single_query_value(query, "coord", "comment")
        _parse_text_machine_coordinate(
            comment_coordinate,
            expected_coordinate_prefix=expected_coordinate_prefix,
        )
        if comment_coordinate != coordinate:
            raise TextParseError("CAL text row comment coordinate differs from token coordinate")
        if found is not None and found != link:
            raise TextParseError("CAL text row exposes multiple different comment links")
        found = link
    return found


def _single_query_value(
    query: dict[str, list[str]],
    key: str,
    context: str,
) -> str:
    values = query.get(key)
    if values is None or len(values) != 1 or not values[0]:
        raise TextParseError(f"CAL {context} link is missing a single {key} value")
    return values[0]


def _same_or_unset(current: int | None, value: int, direction: str) -> int:
    if current is not None and current != value:
        raise TextParseError(f"CAL text page exposes conflicting {direction}-page links")
    return value


def _is_path(href: str, filename: str) -> bool:
    return urlsplit(href).path.endswith(filename)


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _optional_clean_text(value: str) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _search_match_to_dict(match: TextSearchMatch) -> dict[str, object]:
    return {
        "file_id": match.file_id,
        "subtext_id": match.subtext_id,
        "category_id": match.category_id,
        "label": match.label,
        "description": match.description,
        "follow_up_tool": match.follow_up_tool,
    }


def _text_ref_to_dict(text: TextRef) -> dict[str, object]:
    return {
        "file_id": text.file_id,
        "subtext_id": text.subtext_id,
        "label": text.label,
        "description": text.description,
    }


def _category_to_dict(category: TextCategoryRef) -> dict[str, object]:
    return {"category_id": category.category_id, "label": category.label}


def _specialized_collection_to_dict(
    collection: TextSpecializedCollectionRef,
) -> dict[str, object]:
    return {
        "collection_key": collection.collection_key,
        "label": collection.label,
        "follow_up_tool": collection.follow_up_tool,
        "selector_name": collection.selector_name,
        "supported_selectors": list(collection.supported_selectors),
    }


def _token_to_dict(token: TextToken) -> dict[str, object]:
    return {
        "coordinate": token.coordinate,
        "word_index": token.word_index,
        "text": token.text,
        "lexical_url": token.lexical_url,
    }


def _line_to_dict(line: TextLine) -> dict[str, object]:
    return {
        "coordinate": line.coordinate,
        "display_coordinate": line.display_coordinate,
        "text": line.text,
        "tokens": [_token_to_dict(item) for item in line.tokens],
        "empty_word_indexes": list(line.empty_word_indexes),
        "comment_url": line.comment_url,
    }


def _line_comment_record_to_dict(record: TextLineCommentRecord) -> dict[str, object]:
    return {
        "reference": record.reference,
        "source_text": record.source_text,
        "translation": record.translation,
        "lemma_key": record.lemma_key,
        "headword": record.headword,
        "part_of_speech": record.part_of_speech,
        "gloss": record.gloss,
        "entry_url": record.entry_url,
    }


def _text_page_to_dict(page: TextPage) -> dict[str, object]:
    return {
        "text": _text_ref_to_dict(page.text),
        "page": page.page,
        "page_count": page.page_count,
        "total_lines": page.total_lines,
        "previous_page": page.previous_page,
        "next_page": page.next_page,
        "previous_subtext_id": page.previous_subtext_id,
        "next_subtext_id": page.next_subtext_id,
        "lines": [_line_to_dict(item) for item in page.lines],
    }


def _provenance_to_dict(provenance: TextProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "operation": provenance.operation,
        "upstream_id": provenance.upstream_id,
        "subtext_id": provenance.subtext_id,
        "category_id": provenance.category_id,
        "page": provenance.page,
        "original_query": provenance.original_query,
        "submitted_query": provenance.submitted_query,
    }


__all__ = [
    "TextCataloguePage",
    "TextCatalogueResult",
    "TextCategoryRef",
    "TextInformationPage",
    "TextInformationResult",
    "TextInformationStatus",
    "TextLine",
    "TextLineCommentRecord",
    "TextLineCommentsPage",
    "TextLineCommentsResult",
    "TextLineCommentsStatus",
    "TextPage",
    "TextPageResult",
    "TextPageStatus",
    "TextParseError",
    "TextProvenance",
    "TextRef",
    "TextSearchMatch",
    "TextSearchPage",
    "TextSearchResult",
    "TextService",
    "TextSpecializedCollectionRef",
    "TextToken",
    "parse_mandaic_catalogue_page",
    "parse_text_catalogue_page",
    "parse_text_information_page",
    "parse_text_line_comments_page",
    "parse_text_page",
    "parse_text_search_page",
]
