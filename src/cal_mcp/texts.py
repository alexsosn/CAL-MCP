from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import (
    CAL_BASE_URL,
    CalContentError,
    CalHttpClient,
    CalRequest,
    CalResponse,
)
from cal_mcp.lexicon import _Line, _Link, _parse_lines
from cal_mcp.syriac import syriac_text_category_slugs

_ID_RE = re.compile(r"^\d+$")
_LINE_COMMENT_COORD_RE = re.compile(r"^[A-Za-z0-9]{1,64}$")
_PAGE_MARKER_RE = re.compile(
    r"^Page\s+(?P<page>\d+)\s+of\s+(?P<count>\d+)\s+"
    r"\((?P<total>\d+)\s+lines total\)$",
    re.IGNORECASE,
)
_NO_LINES_RE = re.compile(r"\bNO LINES FOR\b.*\bARE CURRENTLY STORED\b", re.IGNORECASE)
_TEXT_SEARCH_MARKER = "cal search for texts like:"
_TEXT_SEARCH_EMPTY_MARKER = "there are no files associated with the search term"
_TEXT_INFORMATION_HEADING = "Text Information"
_TEXT_INFORMATION_MISSING_MARKER = "No information on record for this text."
_LINE_COMMENTS_EMPTY_MARKER = "NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED"
_MANDAIC_COLLECTION_PREFIX = "74"
_MANDAIC_CATEGORY_ID = "74"
_MANDAIC_CATALOGUE_PATH = "show_Mandaic.php"
_MANDAIC_ROOT_LABEL = "Mandaic"
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
_ONKELOS_JONATHAN_CATEGORY_ID = "51"
_ONKELOS_JONATHAN_PATH = "targum_onkelos_jonathan.html"
_ONKELOS_JONATHAN_LABEL = "Targums Onkelos and Jonathan to the Prophets"
_SYRIAC_COLLECTION_KEY = "syriac"
_SYRIAC_ROOT_PATH = "AvailSyr.html"
_SYRIAC_ROOT_LABEL = "Syriac"
_SYRIAC_FOLLOW_UP_TOOL = "cal_syriac_texts"
_SYRIAC_SELECTOR_NAME = "category"
_ROOT_CATALOGUE_PATH = "newtextmenu.html"


class TextParseError(CalContentError):
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
    coordinate: str
    display_coordinate: str | None
    text: str
    tokens: tuple[TextToken, ...]
    comment_url: str | None


@dataclass(frozen=True, slots=True)
class TextPage:
    text: TextRef
    page: int
    page_count: int | None
    total_lines: int | None
    previous_page: int | None
    next_page: int | None
    lines: tuple[TextLine, ...]


@dataclass(frozen=True, slots=True)
class TextCataloguePage:
    categories: tuple[TextCategoryRef, ...]
    texts: tuple[TextRef, ...]
    specialized_collections: tuple[TextSpecializedCollectionRef, ...] = ()


@dataclass(frozen=True, slots=True)
class TextSearchPage:
    matches: tuple[TextRef, ...]


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

    def to_dict(self) -> dict[str, object]:
        return {
            "categories": [_category_to_dict(item) for item in self.categories],
            "texts": [_text_ref_to_dict(item) for item in self.texts],
            "specialized_collections": [
                _specialized_collection_to_dict(item) for item in self.specialized_collections
            ],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class TextSearchResult:
    matches: tuple[TextRef, ...]
    provenance: TextProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "matches": [_text_ref_to_dict(item) for item in self.matches],
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "title":
            if self._title_parts is not None:
                raise TextParseError("CAL line-comments page has malformed nested title markup")
            self._title_parts = []
            return

        if tag == "div":
            classes = (attr_map.get("class") or "").split()
            if self._summary_depth:
                self._summary_depth += 1
            elif "summary-card" in classes:
                self.summary_count += 1
                self._summary_depth = 1
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

    def handle_data(self, data: str) -> None:
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

    for line in _parse_lines(response):
        for link in line.links:
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


def parse_mandaic_catalogue_page(response: CalResponse) -> TextCataloguePage:
    parsed_response = urlsplit(response.url)
    if parsed_response.path != f"/{_MANDAIC_CATALOGUE_PATH}":
        raise TextParseError("CAL Mandaic catalogue response endpoint changed unexpectedly")
    response_query = parse_qs(parsed_response.query, keep_blank_values=True)
    if set(response_query) != {"R1"} or response_query.get("R1") != [_MANDAIC_CATEGORY_ID]:
        raise TextParseError("CAL Mandaic catalogue response selector changed unexpectedly")

    texts: list[TextRef] = []
    seen_ids: set[str] = set()
    for line in _parse_lines(response):
        candidates: list[TextRef] = []
        for link in line.links:
            candidate = _mandaic_catalogue_text_from_link(line, link, response.url)
            if candidate is not None:
                candidates.append(candidate)
        if len(candidates) > 1:
            raise TextParseError("CAL Mandaic catalogue row exposes multiple text routes")
        if not candidates:
            continue
        candidate = candidates[0]
        if candidate.file_id in seen_ids:
            raise TextParseError("CAL Mandaic catalogue repeats a file identifier")
        seen_ids.add(candidate.file_id)
        texts.append(candidate)

    if not texts:
        raise TextParseError("CAL Mandaic catalogue contains no recognizable text rows")
    return TextCataloguePage(categories=(), texts=tuple(texts))


def parse_text_search_page(response: CalResponse) -> TextSearchPage:
    lines = _parse_lines(response)
    page_text = " ".join(line.text for line in lines)
    lowered = page_text.lower()

    if _TEXT_SEARCH_EMPTY_MARKER in lowered:
        return TextSearchPage(matches=())
    if _TEXT_SEARCH_MARKER not in lowered:
        raise TextParseError("CAL text search page is missing its result marker")

    matches: list[TextRef] = []
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
    )


def _parse_text_page(
    response: CalResponse,
    *,
    requested_file_id: str,
    requested_subtext_id: str | None,
    requested_page: int | None,
    mandaic_page_route: bool,
) -> TextPage | None:
    lines = _parse_lines(response)
    page_text = " ".join(line.text for line in lines)
    if _NO_LINES_RE.search(page_text) is not None:
        return None

    text_ref = _page_text_ref(lines, requested_file_id, requested_subtext_id)
    page_number, page_count, total_lines = _page_metadata(lines)
    if mandaic_page_route and page_count is None and requested_page is not None:
        page_number = requested_page
    if requested_page is not None and page_number != requested_page:
        raise TextParseError("CAL text page number differs from the requested page")
    previous_page, next_page = _page_navigation(
        lines,
        requested_file_id=requested_file_id,
        requested_subtext_id=requested_subtext_id,
        mandaic_page_route=mandaic_page_route,
    )
    _validate_page_navigation(
        page_number=page_number,
        page_count=page_count,
        previous_page=previous_page,
        next_page=next_page,
        allow_navigation_without_page_count=mandaic_page_route,
    )
    text_lines = tuple(
        parsed for line in lines if (parsed := _parse_text_line(line, response.url)) is not None
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
    )


class TextService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def catalogue(self, *, category_id: str | None = None) -> TextCatalogueResult:
        normalized_category = (
            None if category_id is None else _validate_id(category_id, "category_id")
        )
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
            parser=parse_text_search_page,
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
        normalized_subtext = None if subtext_id is None else _validate_id(subtext_id, "subtext_id")
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
        normalized_subtext = None if subtext_id is None else _validate_id(subtext_id, "subtext_id")
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError("page must be a positive integer")

        mandaic_collection_route = normalized_subtext is None and normalized_file.startswith(
            _MANDAIC_COLLECTION_PREFIX
        )
        mandaic_page_route = (
            mandaic_collection_route and normalized_file in _MANDAIC_SUBDIVIDED_FILE_IDS
        )
        mandaic_direct_route = mandaic_collection_route and not mandaic_page_route
        if mandaic_page_route:
            params = [
                ("cset", "M"),
                ("file", normalized_file),
                ("sub", f"{page:03d}"),
            ]
        elif mandaic_direct_route:
            if page != 1:
                raise ValueError("direct Mandaic texts currently support only page 1")
            params = [("cset", "M"), ("file", normalized_file)]
        else:
            params = [("file", normalized_file)]
            if normalized_subtext is not None:
                params.append(("sub", normalized_subtext))
            params.append(("page", str(page - 1)))

        def parse_requested(response: CalResponse) -> TextPage | None:
            return _parse_text_page(
                response,
                requested_file_id=normalized_file,
                requested_subtext_id=normalized_subtext,
                requested_page=page,
                mandaic_page_route=mandaic_page_route,
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
        raise ValueError(f"{name} must be a CAL decimal identifier")
    return value


def _validate_line_comment_coordinate(value: str) -> str:
    if not isinstance(value, str) or _LINE_COMMENT_COORD_RE.fullmatch(value) is None:
        raise ValueError("coordinate must be a 1-64 character ASCII alphanumeric CAL coordinate")
    return value


def _parse_id(value: str, name: str) -> str:
    if _ID_RE.fullmatch(value) is None:
        raise TextParseError(f"CAL returned a non-decimal {name}")
    return value


def _parse_positive_id(value: str, name: str) -> str:
    parsed = _parse_id(value, name)
    if int(parsed) < 1:
        raise TextParseError(f"CAL returned a non-positive {name}")
    return parsed


def _prepare_text_search_query(value: str) -> str:
    trimmed = value.strip(" ")
    if not trimmed:
        raise ValueError("CAL text search query must not be empty")
    if any(char.isspace() and char != " " for char in trimmed):
        raise ValueError("CAL text search words must be separated by ASCII spaces")
    parts = [part for part in trimmed.split(" ") if part]
    if not parts:
        raise ValueError("CAL text search query must not be empty")
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
    if sub_values is not None:
        if len(sub_values) != 1:
            raise TextParseError("CAL text link has repeated sub identifiers")
        if sub_values[0]:
            subtext_id = _parse_id(sub_values[0], "subtext_id")

    rendered_label = (label if label is not None else link.text).strip()
    if not rendered_label:
        raise TextParseError("CAL text link has no rendered label")
    return TextRef(
        file_id=file_id,
        subtext_id=subtext_id,
        label=rendered_label,
        description=description,
    )


def _mandaic_catalogue_text_from_link(
    line: _Line,
    link: _Link,
    source_url: str,
) -> TextRef | None:
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
    if query.get("cset") != ["M"]:
        raise TextParseError("CAL Mandaic catalogue child cset changed unexpectedly")
    file_id = _single_query_value(query, selector, "Mandaic catalogue")
    _parse_positive_id(file_id, "file_id")

    anchor = link.text.strip()
    if not anchor or anchor != file_id or anchor not in line.text:
        raise TextParseError("CAL Mandaic catalogue file link is detached or mislabeled")
    rendered_label = line.text.replace(anchor, "", 1).strip()
    if not rendered_label:
        raise TextParseError("CAL Mandaic catalogue file row has no rendered label")
    return TextRef(file_id=file_id, subtext_id=None, label=rendered_label)


def _search_text_ref_from_link(
    link: _Link,
    *,
    label: str,
    description: str | None,
) -> TextRef | None:
    ordinary = _text_ref_from_link(link, label=label, description=description)
    if ordinary is not None:
        return ordinary
    if not _is_path(link.href, "showsubtexts.php"):
        return None

    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    subtext_values = query.get("subtext")
    if (
        subtext_values is None
        or len(subtext_values) != 1
        or _ID_RE.fullmatch(subtext_values[0]) is None
    ):
        raise TextParseError("CAL Mandaic text search result has an invalid file identifier")
    cset_values = query.get("cset")
    if cset_values != ["M"]:
        raise TextParseError("CAL Mandaic text search result has an invalid cset")

    rendered_label = label.strip()
    if not rendered_label:
        raise TextParseError("CAL Mandaic text search result has no rendered label")
    return TextRef(
        file_id=subtext_values[0],
        subtext_id=None,
        label=rendered_label,
        description=description,
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
    label, separator, description = remainder.partition(":")
    label = label.strip()
    if not label:
        raise TextParseError("CAL text search result row has an empty text label")
    rendered_description = description.strip() if separator and description.strip() else None
    return label, rendered_description


def _page_text_ref(
    lines: list[_Line],
    requested_file_id: str,
    requested_subtext_id: str | None,
) -> TextRef:
    for line in lines:
        for link in line.links:
            if not _is_path(link.href, "get_file_info.php"):
                continue
            query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
            file_id = _single_query_value(query, "coord", "file-info")
            _parse_id(file_id, "file_id")
            if file_id != requested_file_id:
                raise TextParseError(
                    "CAL text page file identifier differs from the requested file"
                )
            prefix, separator, label = link.text.partition(":")
            if not separator or prefix.strip() != file_id or not label.strip():
                raise TextParseError("CAL text page file-info label is malformed")
            return TextRef(
                file_id=file_id,
                subtext_id=requested_subtext_id,
                label=label.strip(),
            )
    raise TextParseError("CAL text page is missing its file-information link")


def _page_metadata(lines: list[_Line]) -> tuple[int, int | None, int | None]:
    found: tuple[int, int, int] | None = None
    for line in lines:
        match = _PAGE_MARKER_RE.fullmatch(line.text)
        if match is None:
            continue
        candidate = (
            int(match.group("page")),
            int(match.group("count")),
            int(match.group("total")),
        )
        if candidate[0] < 1 or candidate[1] < candidate[0]:
            raise TextParseError("CAL text page has invalid pagination metadata")
        if found is not None and found != candidate:
            raise TextParseError("CAL text page exposes conflicting pagination metadata")
        found = candidate
    if found is None:
        return 1, None, None
    return found


def _page_navigation(
    lines: list[_Line],
    *,
    requested_file_id: str,
    requested_subtext_id: str | None,
    mandaic_page_route: bool = False,
) -> tuple[int | None, int | None]:
    previous: int | None = None
    next_page: int | None = None
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
                cset = _single_query_value(query, "cset", "page-navigation")
                if cset != "M":
                    raise TextParseError("CAL text page navigation cset differs from Mandaic route")
                upstream_sub = _single_query_value(query, "sub", "page-navigation")
                _parse_id(upstream_sub, "subtext_id")
                public_page = int(upstream_sub)
            else:
                subtext_id: str | None = None
                sub_values = query.get("sub")
                if sub_values is not None:
                    if len(sub_values) != 1:
                        raise TextParseError(
                            "CAL text page navigation has repeated sub identifiers"
                        )
                    if sub_values[0]:
                        subtext_id = _parse_id(sub_values[0], "subtext_id")
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
    return previous, next_page


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


def _parse_text_line(line: _Line, source_url: str) -> TextLine | None:
    tokens = tuple(
        token for link in line.links if (token := _token_from_link(link, source_url)) is not None
    )
    if not tokens:
        return None

    coordinate = tokens[0].coordinate
    if any(token.coordinate != coordinate for token in tokens):
        raise TextParseError("CAL text row mixes multiple machine coordinates")

    comment_link = _matching_comment_link(line.links, coordinate)
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


def _token_from_link(link: _Link, source_url: str) -> TextToken | None:
    if not _is_path(link.href, "bablex.php") and not _is_path(link.href, "getlex.php"):
        return None
    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    coordinate = _single_query_value(query, "coord", "token")
    word = _single_query_value(query, "word", "token")
    _parse_id(coordinate, "coordinate")
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


def _matching_comment_link(links: tuple[_Link, ...], coordinate: str) -> _Link | None:
    found: _Link | None = None
    for link in links:
        if not _is_path(link.href, "comment.php"):
            continue
        query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
        comment_coordinate = _single_query_value(query, "coord", "comment")
        _parse_id(comment_coordinate, "coordinate")
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
