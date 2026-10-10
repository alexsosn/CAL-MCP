from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.biblical import (
    MT_LINE_BREAK,
    _clean_parallel_mt_text,
    cal_biblical_book_id,
    cal_biblical_heading_matches,
)
from cal_mcp.client import CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalInputError, CalParseError
from cal_mcp.lemma_key import validate_lemma_key


class SyriacParseError(CalParseError):
    """Raised when CAL Syriac markup no longer exposes required semantics."""


class SyriacTextNavigationKind(StrEnum):
    TEXT = "text"
    GROUP = "group"
    CATALOGUE = "catalogue"


class SyriacPeshittaStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class SyriacTextItem:
    upstream_id: str
    label: str
    navigation_kind: SyriacTextNavigationKind
    navigation_url: str
    info_url: str | None = None
    subtext_id: str | None = None


@dataclass(frozen=True, slots=True)
class SyriacTextCategoryPage:
    label: str
    items: tuple[SyriacTextItem, ...]


@dataclass(frozen=True, slots=True)
class SyriacMissingWord:
    lemma_key: str
    label: str
    note: str | None
    entry_url: str


@dataclass(frozen=True, slots=True)
class SyriacMissingWordsPage:
    dictionary_label: str
    heading: str
    items: tuple[SyriacMissingWord, ...]


@dataclass(frozen=True, slots=True)
class SyriacPeshittaPage:
    status: SyriacPeshittaStatus
    mt_text: str | None
    peshitta_label: str | None
    peshitta_text: str | None
    peshitta_url: str | None


@dataclass(frozen=True, slots=True)
class SyriacProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    category: str | None = None
    upstream_category: str | None = None
    group_id: str | None = None
    book: str | None = None
    book_id: str | None = None
    chapter: int | None = None
    verse: int | None = None


@dataclass(frozen=True, slots=True)
class SyriacTextCategoryResult:
    category: str
    label: str
    items: tuple[SyriacTextItem, ...]
    provenance: SyriacProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "label": self.label,
            "items": [_text_item_to_dict(item) for item in self.items],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class SyriacTextGroupResult:
    group_id: str
    items: tuple[SyriacTextItem, ...]
    provenance: SyriacProvenance

    def to_dict(self) -> dict[str, object]:
        provenance = _provenance_to_dict(self.provenance)
        provenance["group_id"] = self.group_id
        return {
            "group_id": self.group_id,
            "items": [_text_item_to_dict(item) for item in self.items],
            "provenance": provenance,
        }


@dataclass(frozen=True, slots=True)
class SyriacMissingWordsResult:
    category: str
    dictionary_label: str
    heading: str
    items: tuple[SyriacMissingWord, ...]
    provenance: SyriacProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "dictionary_label": self.dictionary_label,
            "heading": self.heading,
            "items": [_missing_word_to_dict(item) for item in self.items],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class SyriacPeshittaResult:
    status: SyriacPeshittaStatus
    book: str
    book_id: str
    chapter: int
    verse: int
    mt_text: str | None
    peshitta_label: str | None
    peshitta_text: str | None
    peshitta_url: str | None
    provenance: SyriacProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "book": self.book,
            "book_id": self.book_id,
            "chapter": self.chapter,
            "verse": self.verse,
            "mt_text": self.mt_text,
            "peshitta_label": self.peshitta_label,
            "peshitta_text": self.peshitta_text,
            "peshitta_url": self.peshitta_url,
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class _Link:
    href: str
    text: str


@dataclass(frozen=True, slots=True)
class _Line:
    text: str
    links: tuple[_Link, ...]


@dataclass(slots=True)
class _OpenLink:
    href: str
    parts: list[str] = field(default_factory=list)


_IGNORED_CONTENT_TAGS = frozenset({"script", "style"})
_BLOCK_TAGS = frozenset(
    {
        "article",
        "center",
        "div",
        "h1",
        "h2",
        "h3",
        "li",
        "p",
        "section",
        "td",
        "th",
        "tr",
    }
)


class _SemanticLinesParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[_Line] = []
        self._parts: list[str] = []
        self._links: list[_Link] = []
        self._open_link: _OpenLink | None = None
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _IGNORED_CONTENT_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag in _BLOCK_TAGS or tag == "br":
            self._flush()
        if tag == "a":
            if self._open_link is not None:
                raise SyriacParseError("CAL Syriac page contains nested result links")
            href = next((value for key, value in attrs if key == "href" and value), "")
            if not href.strip():
                raise SyriacParseError("CAL Syriac result link has no target")
            self._open_link = _OpenLink(href=href)

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            if tag in _IGNORED_CONTENT_TAGS:
                self._ignored_depth -= 1
            return
        if tag == "a" and self._open_link is not None:
            self._links.append(
                _Link(
                    href=self._open_link.href,
                    text=_clean_text("".join(self._open_link.parts)),
                )
            )
            self._open_link = None
        if tag in _BLOCK_TAGS or tag == "br":
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self._parts.append(data)
        if self._open_link is not None:
            self._open_link.parts.append(data)

    def close(self) -> None:
        super().close()
        if self._ignored_depth:
            raise SyriacParseError("CAL Syriac page has an unclosed ignored content subtree")
        if self._open_link is not None:
            raise SyriacParseError("CAL Syriac page has an incomplete result link")
        self._flush()

    def _flush(self) -> None:
        text = _clean_text("".join(self._parts))
        if text:
            self.lines.append(_Line(text=text, links=tuple(self._links)))
        self._parts.clear()
        self._links.clear()


@dataclass(slots=True)
class _OpenPeshittaLink:
    href: str
    parts: list[str] = field(default_factory=list)


class _PeshittaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.centers: list[str] = []
        self.all_parts: list[str] = []
        self.hebrew_parts: list[str] = []
        self.syriac_parts: list[str] = []
        self.links: list[_Link] = []
        self._center_parts: list[str] | None = None
        self._script_kind: str | None = None
        self._script_depth = 0
        self._open_link: _OpenPeshittaLink | None = None
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _IGNORED_CONTENT_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        attributes = dict(attrs)
        if tag == "center":
            if self._center_parts is not None:
                raise SyriacParseError("CAL Peshitta page contains nested semantic headings")
            self._center_parts = []
            return
        if tag == "span":
            classes = set((attributes.get("class") or "").split())
            matched = classes.intersection({"heb", "syr"})
            if self._script_kind is None and matched:
                if len(matched) != 1:
                    raise SyriacParseError("CAL Peshitta span has ambiguous script semantics")
                self._script_kind = next(iter(matched))
                self._script_depth = 1
            elif self._script_kind is not None:
                self._script_depth += 1
            return
        if tag == "br" and self._script_kind is not None:
            self._append_script_data(MT_LINE_BREAK)
            return
        if tag == "a":
            if self._open_link is not None:
                raise SyriacParseError("CAL Peshitta page contains nested links")
            href = attributes.get("href")
            if href is None or not href.strip():
                raise SyriacParseError("CAL Peshitta link has no target")
            self._open_link = _OpenPeshittaLink(href=href)

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            if tag in _IGNORED_CONTENT_TAGS:
                self._ignored_depth -= 1
            return
        if tag == "center" and self._center_parts is not None:
            text = _clean_text("".join(self._center_parts))
            if text:
                self.centers.append(text)
            self._center_parts = None
            return
        if tag == "span" and self._script_kind is not None:
            self._script_depth -= 1
            if self._script_depth == 0:
                self._script_kind = None
            return
        if tag == "a" and self._open_link is not None:
            self.links.append(
                _Link(
                    href=self._open_link.href,
                    text=_clean_text("".join(self._open_link.parts)),
                )
            )
            self._open_link = None

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self.all_parts.append(data)
        if self._center_parts is not None:
            self._center_parts.append(data)
        if self._script_kind is not None:
            self._append_script_data(data)
        if self._open_link is not None:
            self._open_link.parts.append(data)

    def close(self) -> None:
        super().close()
        if self._ignored_depth:
            raise SyriacParseError("CAL Peshitta page has an unclosed ignored content subtree")
        if self._center_parts is not None or self._script_kind is not None:
            raise SyriacParseError("CAL Peshitta page contains incomplete semantic markup")
        if self._open_link is not None:
            raise SyriacParseError("CAL Peshitta page contains an incomplete result link")

    def _append_script_data(self, data: str) -> None:
        if self._script_kind == "heb":
            self.hebrew_parts.append(data)
        elif self._script_kind == "syr":
            self.syriac_parts.append(data)


@dataclass(frozen=True, slots=True)
class _TextCategoryConfig:
    label: str
    path: str
    upstream_category: str | None = None


_TEXT_CATEGORIES = {
    "ot-peshitta": _TextCategoryConfig("OT Peshiṭta", "ot_peshitta.html"),
    "old-syriac-gospels": _TextCategoryConfig(
        "Old Syriac Gospels",
        "old_syriac_gospels.html",
    ),
    "nt-peshitta": _TextCategoryConfig("NT Peshiṭta", "nt_peshitta.html"),
    "apocryphal-pseudepigraphal": _TextCategoryConfig(
        "Apocryphal/Pseudepigraphal Texts",
        "apocryphal_pseudepigraphal.html",
    ),
    "commentaries": _TextCategoryConfig("Commentaries", "show_Syriac_categories.php", "5"),
    "metrical-homilies-hymns": _TextCategoryConfig(
        "Metrical Homilies and Hymns",
        "show_Syriac_categories.php",
        "6",
    ),
    "dispute-poems": _TextCategoryConfig("Dispute Poems", "show_Syriac_categories.php", "7"),
    "religion": _TextCategoryConfig("Religion", "show_Syriac_categories.php", "8"),
    "archival": _TextCategoryConfig("Archival", "show_Syriac_categories.php", "9"),
    "canonical": _TextCategoryConfig("Canonical", "show_Syriac_categories.php", "10"),
    "documents": _TextCategoryConfig("Documents", "show_Syriac_categories.php", "11"),
    "syro-roman-law-book": _TextCategoryConfig(
        "Syro-Roman Law Book",
        "show_Syriac_categories.php",
        "12",
    ),
    "canon-law": _TextCategoryConfig("Canon Law", "show_Syriac_categories.php", "13"),
    "magic": _TextCategoryConfig("Magic", "show_Syriac_categories.php", "14"),
    "science-philosophy": _TextCategoryConfig(
        "Science/Philosophy",
        "show_Syriac_categories.php",
        "15",
    ),
    "history": _TextCategoryConfig("History", "show_Syriac_categories.php", "16"),
    "novels-histories": _TextCategoryConfig(
        "Novels/Histories",
        "show_Syriac_categories.php",
        "17",
    ),
    "martyrologies": _TextCategoryConfig(
        "Martyrologies",
        "show_Syriac_categories.php",
        "18",
    ),
    "various": _TextCategoryConfig("Various", "show_Syriac_categories.php", "19"),
    "inscriptions": _TextCategoryConfig(
        "Inscriptions",
        "show_Syriac_categories.php",
        "20",
    ),
}


def syriac_text_category_slugs() -> tuple[str, ...]:
    """Return supported public Syriac text-category selectors in service order."""
    return tuple(_TEXT_CATEGORIES)


class SyriacMissingWordCategory(StrEnum):
    ADJECTIVES = "adjectives"
    ADVERBS = "adverbs"
    MISCELLANEOUS = "miscellaneous"
    NOMINA_AGENTIS = "nomina-agentis"
    ABSTRACTS = "abstracts"
    VERBAL_NOUNS = "verbal-nouns"
    VERBS = "verbs"
    MASCULINE_NOUNS = "masculine-nouns"
    FEMININE_NOUNS = "feminine-nouns"


_MISSING_WORD_PATHS = {
    SyriacMissingWordCategory.ADJECTIVES: "display_missing_adj.php",
    SyriacMissingWordCategory.ADVERBS: "display_missingSL.php",
    SyriacMissingWordCategory.MISCELLANEOUS: "display_missing_misc.php",
    SyriacMissingWordCategory.NOMINA_AGENTIS: "display_missing_nomag.php",
    SyriacMissingWordCategory.ABSTRACTS: "display_missingU.php",
    SyriacMissingWordCategory.VERBAL_NOUNS: "display_missing_vn.php",
    SyriacMissingWordCategory.VERBS: "display_missing_verbs.php",
    SyriacMissingWordCategory.MASCULINE_NOUNS: "display_missing.mascnouns.php",
    SyriacMissingWordCategory.FEMININE_NOUNS: "display_missing.femnouns.php",
}


def syriac_missing_word_category_slugs() -> tuple[str, ...]:
    """Public selectors in the exact route-map declaration order."""
    return tuple(category.value for category in _MISSING_WORD_PATHS)

_PESHITTA_HEADING_PREFIX = "MT and Peshitta for "
_COORDINATE_ERROR_RE = re.compile(r"\berror\s+in\s+coord(?:inate)?\b", re.I)
_MISSING_DICTIONARY_LABEL = "A Syriac Lexicon"
_MISSING_MARKER = "not found in A Syriac Lexicon"


def parse_syriac_text_category_page(
    response: CalResponse,
    *,
    category: str,
) -> SyriacTextCategoryPage:
    config = _text_category_config(category)
    _validate_category_response_url(response.url, config)
    parser = _SemanticLinesParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    expected = _clean_text(config.label).casefold()
    matching_headings = [line.text for line in parser.lines if line.text.casefold() == expected]
    if len(matching_headings) != 1:
        raise SyriacParseError("CAL Syriac text category lacks the expected category heading")

    items = _parse_syriac_navigation_items(parser.lines, response.url)
    return SyriacTextCategoryPage(label=matching_headings[0], items=items)


def _parse_syriac_navigation_items(
    lines: list[_Line],
    source_url: str,
) -> tuple[SyriacTextItem, ...]:
    items: list[SyriacTextItem] = []
    seen_ids: set[str] = set()
    for line in lines:
        navigation: list[tuple[SyriacTextNavigationKind, str, str, _Link]] = []
        info_links: list[tuple[str, str, _Link]] = []
        for link in line.links:
            target = urlsplit(urljoin(source_url, link.href))
            endpoint = target.path.rsplit("/", 1)[-1]
            if endpoint == "get_a_chapter.php":
                resolved = _validated_same_origin_url(source_url, link.href, endpoint)
                upstream_id = _single_query_value(
                    parse_qs(urlsplit(resolved).query, keep_blank_values=True),
                    "file",
                    "Syriac direct-text navigation",
                )
                _require_decimal_identifier(upstream_id, "Syriac text file")
                navigation.append((SyriacTextNavigationKind.TEXT, upstream_id, resolved, link))
            elif endpoint == "showsubtexts.php":
                resolved = _validated_same_origin_url(source_url, link.href, endpoint)
                query = parse_qs(urlsplit(resolved).query, keep_blank_values=True)
                allowed_keys = {"keyword", "subtext", "cset", "script"}
                if set(query) - allowed_keys:
                    raise SyriacParseError(
                        "CAL Syriac subtext navigation has unexpected query fields"
                    )
                for presentation_key in ("cset", "script"):
                    if presentation_key in query:
                        _single_query_value(
                            query,
                            presentation_key,
                            "Syriac subtext presentation metadata",
                        )

                selectors: list[tuple[SyriacTextNavigationKind, str]] = []
                if "keyword" in query:
                    keyword = _single_query_value(
                        query,
                        "keyword",
                        "Syriac grouped-text navigation",
                    )
                    _require_decimal_identifier(keyword, "Syriac grouped-text keyword")
                    selectors.append((SyriacTextNavigationKind.GROUP, keyword))
                if "subtext" in query:
                    subtext = _single_query_value(
                        query,
                        "subtext",
                        "Syriac catalogue navigation",
                    )
                    _require_decimal_identifier(subtext, "Syriac catalogue identifier")
                    selectors.append((SyriacTextNavigationKind.CATALOGUE, subtext))
                if len(selectors) != 1:
                    raise SyriacParseError(
                        "CAL Syriac subtext navigation must expose exactly one semantic selector"
                    )
                kind, upstream_id = selectors[0]
                navigation.append((kind, upstream_id, resolved, link))
            elif endpoint == "get_file_info.php":
                resolved = _validated_same_origin_url(source_url, link.href, endpoint)
                info_id = _single_query_value(
                    parse_qs(urlsplit(resolved).query, keep_blank_values=True),
                    "coord",
                    "Syriac file information",
                )
                _require_decimal_identifier(info_id, "Syriac file information coordinate")
                info_links.append((info_id, resolved, link))

        if not navigation:
            if info_links:
                raise SyriacParseError("CAL Syriac category has detached file-information links")
            continue
        if len(navigation) != 1:
            raise SyriacParseError("CAL Syriac category row has ambiguous navigation semantics")
        kind, upstream_id, navigation_url, navigation_link = navigation[0]
        if upstream_id in seen_ids:
            raise SyriacParseError("CAL Syriac category repeats an upstream text identifier")
        seen_ids.add(upstream_id)
        if len(info_links) > 1:
            raise SyriacParseError("CAL Syriac category row has ambiguous file-information links")
        info_url = None
        ignored_labels = [navigation_link.text]
        if info_links:
            info_id, info_url, info_link = info_links[0]
            if info_id != upstream_id:
                raise SyriacParseError(
                    "CAL Syriac category file-information link contradicts its row"
                )
            ignored_labels.append(info_link.text)
        label = _row_label(line.text, navigation_link.text, upstream_id, ignored_labels)
        if not label:
            raise SyriacParseError("CAL Syriac category row has no rendered label")
        items.append(
            SyriacTextItem(
                upstream_id=upstream_id,
                label=label,
                navigation_kind=kind,
                navigation_url=navigation_url,
                info_url=info_url,
            )
        )

    if not items:
        raise SyriacParseError("CAL Syriac text category has no recognized result rows")
    return tuple(items)


def parse_syriac_text_group_page(
    response: CalResponse,
    *,
    group_id: str,
) -> tuple[SyriacTextItem, ...]:
    submitted_group = _validate_group_id(group_id)
    _require_response_path(response.url, "showsubtexts.php", "Syriac grouped-text")
    query = parse_qs(urlsplit(response.url).query, keep_blank_values=True)
    if set(query) != {"keyword"}:
        raise SyriacParseError("CAL Syriac grouped-text response has unexpected query semantics")
    returned_group = _single_query_value(
        query,
        "keyword",
        "Syriac grouped-text response",
    )
    if returned_group != submitted_group:
        raise SyriacParseError("CAL Syriac grouped-text response contradicts the selected group")

    body = response.body.decode("utf-8", errors="replace")
    if _GROUP_CARD_MARKER_RE.search(body) is not None:
        return _parse_syriac_group_cards(body, response.url, submitted_group)
    parser = _SemanticLinesParser()
    parser.feed(body)
    parser.close()
    return _parse_syriac_navigation_items(parser.lines, response.url)


_GROUP_CARD_MARKER_RE = re.compile(
    r"<details\b[^>]*\bclass=\"[^\"]*(?<![\w-])dialect-group(?![\w-])", re.IGNORECASE
)
_GROUP_TOGGLE_SCRIPTS = frozenset({"S", "R"})
_GROUP_CHROME_HREFS = frozenset({"javascript:history.back()", "/newtextmenu.html", "/"})
_GROUP_PAGE_TEXT = frozenset({"Select a Text"})
_GROUP_TOGGLE_TEXT = frozenset({"View in:"})
# The document head (title, styles, scripts) is not page content.
_GROUP_IGNORED_TAGS = _IGNORED_CONTENT_TAGS | {"head"}


@dataclass(slots=True)
class _CardLink:
    classes: tuple[str, ...]
    href: str
    parts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return _clean_text("".join(self.parts))


@dataclass(slots=True)
class _Card:
    links: list[_CardLink] = field(default_factory=list)
    loose_text: list[str] = field(default_factory=list)


class _GroupCardsParser(HTMLParser):
    """Place every link and every piece of text of CAL's card-layout group page (R-055).

    Nothing is dropped: text or links outside the recognised places are recorded so that
    the caller can fail closed on them.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chrome_links: list[_CardLink] = []
        self.toggle_links: list[_CardLink] = []
        self.summary_links: list[_CardLink] = []
        self.cards: list[_Card] = []
        self.stray_links: list[_CardLink] = []
        self.summary_text: list[str] = []
        self.summary_other_text: list[str] = []
        self.summary_span_count = 0
        self.toggle_text: list[str] = []
        self.group_text: list[str] = []
        self.page_text: list[str] = []
        self.group_count = 0
        self._banner_depth = 0
        self._toggle_depth = 0
        self._details_depth = 0
        self._in_summary = False
        self._summary_span_depth = 0
        self._card: _Card | None = None
        self._link: _CardLink | None = None
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _GROUP_IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        values = dict(attrs)
        classes = tuple((values.get("class") or "").split())
        if tag == "div":
            if self._banner_depth:
                self._banner_depth += 1
            elif "cal-banner" in classes:
                self._banner_depth = 1
            if self._toggle_depth:
                self._toggle_depth += 1
            elif "script-toggle" in classes:
                self._toggle_depth = 1
        elif tag == "details":
            if self._details_depth:
                self._details_depth += 1
            elif "dialect-group" in classes:
                self._details_depth = 1
                self.group_count += 1
        elif tag == "summary" and self._details_depth:
            self._in_summary = True
        elif tag == "span" and self._in_summary and self._link is None:
            if not self._summary_span_depth:
                self.summary_span_count += 1
            self._summary_span_depth += 1
        elif tag == "li" and self._details_depth:
            if self._card is not None:
                raise SyriacParseError("CAL Syriac group card is nested in another card")
            self._card = _Card()
            self.cards.append(self._card)
        elif tag == "a":
            if self._link is not None:
                raise SyriacParseError("CAL Syriac group page contains nested links")
            self._link = _CardLink(classes=classes, href=values.get("href") or "")

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            if tag in _GROUP_IGNORED_TAGS:
                self._ignored_depth -= 1
            return
        if tag == "div":
            if self._banner_depth:
                self._banner_depth -= 1
            if self._toggle_depth:
                self._toggle_depth -= 1
        elif tag == "details" and self._details_depth:
            self._details_depth -= 1
        elif tag == "summary":
            self._in_summary = False
        elif tag == "span" and self._summary_span_depth:
            self._summary_span_depth -= 1
        elif tag == "li":
            self._card = None
        elif tag == "a" and self._link is not None:
            link, self._link = self._link, None
            if self._banner_depth:
                self.chrome_links.append(link)
            elif self._toggle_depth:
                self.toggle_links.append(link)
            elif self._in_summary:
                self.summary_links.append(link)
            elif self._card is not None:
                self._card.links.append(link)
            else:
                self.stray_links.append(link)

    def handle_data(self, data: str) -> None:
        if self._ignored_depth or not data.strip():
            return
        if self._link is not None:
            self._link.parts.append(data)
        elif self._banner_depth:
            self.page_text.append(data)
        elif self._toggle_depth:
            self.toggle_text.append(data)
        elif self._in_summary:
            # The summary is CAL's label span plus the information link; nothing else.
            target = self.summary_text if self._summary_span_depth else self.summary_other_text
            target.append(data)
        elif self._card is not None:
            self._card.loose_text.append(data)
        elif self._details_depth:
            self.group_text.append(data)
        else:
            self.page_text.append(data)

    def close(self) -> None:
        super().close()
        if self._link is not None or self._ignored_depth:
            raise SyriacParseError("CAL Syriac group page has incomplete markup")


def _parse_syriac_group_cards(
    body: str, source_url: str, group_id: str
) -> tuple[SyriacTextItem, ...]:
    parser = _GroupCardsParser()
    parser.feed(body)
    parser.close()

    if parser.group_count != 1:
        raise SyriacParseError("CAL Syriac group page does not hold exactly one group")
    # Only CAL's banner navigation, the page title and the toggle label surround the group;
    # any other link or text is content CAL-MCP would otherwise drop (R-055).
    if parser.stray_links or parser.group_text:
        raise SyriacParseError("CAL Syriac group page has content outside its cards")
    if any(link.href not in _GROUP_CHROME_HREFS for link in parser.chrome_links):
        raise SyriacParseError("CAL Syriac group page banner has an unexpected link")
    if not {_clean_text(text) for text in parser.page_text} <= _GROUP_PAGE_TEXT:
        raise SyriacParseError("CAL Syriac group page has unexpected text outside its group")
    if not {_clean_text(text) for text in parser.toggle_text} <= _GROUP_TOGGLE_TEXT:
        raise SyriacParseError("CAL Syriac group script toggle has unexpected text")

    for link in parser.toggle_links:
        if "script-toggle-opt" not in link.classes:
            raise SyriacParseError("CAL Syriac group script toggle has an unexpected link")
        resolved = _validated_same_origin_url(source_url, link.href, "showsubtexts.php")
        query = parse_qs(urlsplit(resolved).query, keep_blank_values=True)
        if (
            set(query) != {"subtext", "script"}
            or query["subtext"] != [group_id]
            or len(query["script"]) != 1
            or query["script"][0] not in _GROUP_TOGGLE_SCRIPTS
        ):
            raise SyriacParseError("CAL Syriac group script toggle names another group")

    if (
        parser.summary_span_count != 1
        or parser.summary_other_text
        or not _clean_text(" ".join(parser.summary_text))
    ):
        raise SyriacParseError("CAL Syriac group summary is not one label")
    if len(parser.summary_links) != 1 or "info-link" not in parser.summary_links[0].classes:
        raise SyriacParseError("CAL Syriac group summary lacks one information link")
    if _card_info_coordinate(parser.summary_links[0], source_url) != group_id:
        raise SyriacParseError("CAL Syriac group summary information link names another group")

    items: list[SyriacTextItem] = []
    seen: set[str] = set()
    for card in parser.cards:
        if card.loose_text:
            raise SyriacParseError("CAL Syriac group card has text outside its links")
        books = [link for link in card.links if link.classes == ("book-link",)]
        infos = [link for link in card.links if link.classes == ("info-link",)]
        if len(books) != 1 or len(infos) > 1 or len(books) + len(infos) != len(card.links):
            raise SyriacParseError("CAL Syriac group card has unexpected links")
        book = books[0]
        navigation_url = _validated_same_origin_url(source_url, book.href, "get_a_chapter.php")
        query = parse_qs(urlsplit(navigation_url).query, keep_blank_values=True)
        if set(query) != {"file", "sub", "cset"} or any(len(v) != 1 for v in query.values()):
            raise SyriacParseError("CAL Syriac group card link has unexpected selectors")
        file_id, subtext_id, cset = query["file"][0], query["sub"][0], query["cset"][0]
        # Every observed group's cards are subtexts of the group's own file.
        if file_id != group_id:
            raise SyriacParseError("CAL Syriac group card names another file")
        if cset not in _GROUP_TOGGLE_SCRIPTS:
            raise SyriacParseError("CAL Syriac group card has an unexpected script selector")
        if not subtext_id.isascii() or not subtext_id.isdecimal():
            raise SyriacParseError("CAL Syriac group card subtext is not decimal")
        if subtext_id in seen:
            raise SyriacParseError("CAL Syriac group repeats a card")
        seen.add(subtext_id)
        if not book.text:
            raise SyriacParseError("CAL Syriac group card has no rendered label")
        info_url = None
        if infos:
            info_url = _validated_same_origin_url(source_url, infos[0].href, "get_file_info.php")
            if _card_info_coordinate(infos[0], source_url) not in {file_id, file_id + subtext_id}:
                raise SyriacParseError("CAL Syriac group card information link names another text")
        items.append(
            SyriacTextItem(
                upstream_id=file_id,
                label=book.text,
                navigation_kind=SyriacTextNavigationKind.TEXT,
                navigation_url=navigation_url,
                info_url=info_url,
                subtext_id=subtext_id,
            )
        )
    if not items:
        raise SyriacParseError("CAL Syriac group page has no cards")
    return tuple(items)


def _card_info_coordinate(link: _CardLink, source_url: str) -> str:
    resolved = _validated_same_origin_url(source_url, link.href, "get_file_info.php")
    query = parse_qs(urlsplit(resolved).query, keep_blank_values=True)
    # CAL's return target is not URL-encoded, so its own script parameter leaks through.
    if not set(query) <= {"coord", "return", "script"}:
        raise SyriacParseError("CAL Syriac group information link has unexpected selectors")
    coord = _single_query_value(query, "coord", "Syriac group information")
    _require_decimal_identifier(coord, "Syriac group information coordinate")
    return coord


def parse_syriac_missing_words_page(
    response: CalResponse,
    *,
    category: str,
) -> SyriacMissingWordsPage:
    expected_path = _missing_word_path(category)
    _require_response_path(response.url, expected_path, "Syriac missing-word list")
    parser = _SemanticLinesParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    headings = [
        line.text for line in parser.lines if _MISSING_MARKER.casefold() in line.text.casefold()
    ]
    if len(headings) != 1:
        raise SyriacParseError(
            "CAL Syriac missing-word page lacks its dictionary comparison heading"
        )

    items: list[SyriacMissingWord] = []
    seen_lemmas: set[str] = set()
    for line in parser.lines:
        entry_links: list[tuple[str, str, _Link]] = []
        for link in line.links:
            target = urlsplit(urljoin(response.url, link.href))
            endpoint = target.path.rsplit("/", 1)[-1]
            if endpoint != "oneentry.php":
                continue
            resolved = _validated_same_origin_url(response.url, link.href, endpoint)
            query = parse_qs(urlsplit(resolved).query, keep_blank_values=True)
            lemma_key = _single_query_value(query, "lemma", "Syriac missing-word entry")
            try:
                _, _, canonical_key = validate_lemma_key(lemma_key)
            except ValueError as exc:
                raise SyriacParseError(
                    "CAL Syriac missing-word link contains an invalid lemma key"
                ) from exc
            if canonical_key != lemma_key:
                raise SyriacParseError(
                    "CAL Syriac missing-word link contains a noncanonical lemma key"
                )
            entry_links.append((canonical_key, resolved, link))
        if not entry_links:
            continue
        if len(entry_links) != 1:
            raise SyriacParseError("CAL Syriac missing-word row has ambiguous entry links")
        lemma_key, entry_url, link = entry_links[0]
        if lemma_key in seen_lemmas:
            raise SyriacParseError("CAL Syriac missing-word list repeats a lemma identifier")
        seen_lemmas.add(lemma_key)
        label = _clean_text(link.text)
        if not label:
            raise SyriacParseError("CAL Syriac missing-word entry has no rendered label")
        note = _remove_rendered_labels(line.text, [link.text])
        items.append(
            SyriacMissingWord(
                lemma_key=lemma_key,
                label=label,
                note=note or None,
                entry_url=entry_url,
            )
        )

    if not items:
        raise SyriacParseError("CAL Syriac missing-word page has no recognized list rows")
    return SyriacMissingWordsPage(
        dictionary_label=_MISSING_DICTIONARY_LABEL,
        heading=headings[0],
        items=tuple(items),
    )


def parse_syriac_peshitta_page(
    response: CalResponse,
    *,
    book: str,
    chapter: int,
    verse: int,
) -> SyriacPeshittaPage:
    _require_response_path(response.url, "showpesh.php", "Peshitta comparison")
    parser = _PeshittaParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    headings = [text for text in parser.centers if text.startswith(_PESHITTA_HEADING_PREFIX)]
    if len(headings) != 1 or not cal_biblical_heading_matches(
        headings[0][len(_PESHITTA_HEADING_PREFIX) :], book=book, chapter=chapter, verse=verse
    ):
        raise SyriacParseError("CAL Peshitta heading does not match the requested verse")
    display_coordinate = headings[0][len(_PESHITTA_HEADING_PREFIX) :]

    page_text = _clean_text(" ".join(parser.all_parts))
    coordinate_error = _COORDINATE_ERROR_RE.search(page_text) is not None
    raw_hebrew = "".join(parser.hebrew_parts)
    syriac = _clean_text("".join(parser.syriac_parts))
    peshitta_links = [link for link in parser.links if _clean_text(link.text) == "Peshitta:"]

    has_any_result_data = bool(_clean_text(raw_hebrew) or syriac or peshitta_links)
    if coordinate_error:
        if has_any_result_data:
            raise SyriacParseError("CAL Peshitta page contradicts its coordinate error")
        return SyriacPeshittaPage(
            status=SyriacPeshittaStatus.NOT_FOUND,
            mt_text=None,
            peshitta_label=None,
            peshitta_text=None,
            peshitta_url=None,
        )

    try:
        hebrew = _clean_parallel_mt_text(
            raw_hebrew,
            display_coordinate=display_coordinate,
        )
    except ValueError:
        raise SyriacParseError(
            "CAL Peshitta MT block has contradictory verse-label semantics"
        ) from None

    if not hebrew or not syriac or len(peshitta_links) != 1:
        raise SyriacParseError("CAL Peshitta page lacks a complete MT/Peshitta comparison")
    peshitta_link = peshitta_links[0]
    peshitta_url = _validated_same_origin_url(
        response.url,
        peshitta_link.href,
        "get_a_chapter.php",
    )
    query = parse_qs(urlsplit(peshitta_url).query, keep_blank_values=True)
    file_id = _single_query_value(query, "file", "Peshitta chapter link")
    _require_decimal_identifier(file_id, "Peshitta text file")
    sub_values = query.get("sub")
    if sub_values is not None:
        if len(sub_values) != 1:
            raise SyriacParseError("CAL Peshitta chapter link has invalid subtext semantics")
        _require_decimal_identifier(sub_values[0], "Peshitta subtext")

    return SyriacPeshittaPage(
        status=SyriacPeshittaStatus.FOUND,
        mt_text=hebrew,
        peshitta_label=_clean_text(peshitta_link.text),
        peshitta_text=syriac,
        peshitta_url=peshitta_url,
    )


class SyriacService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def texts(self, category: str) -> SyriacTextCategoryResult:
        config = _text_category_config(category)
        params = (
            (("category", config.upstream_category),)
            if config.upstream_category is not None
            else ()
        )
        result = await self._client.fetch(
            CalRequest(method="GET", path=config.path, params=params),
            parser=lambda response: parse_syriac_text_category_page(
                response,
                category=category,
            ),
            cache_namespace=f"syriac-texts-{category}-v1",
        )
        return SyriacTextCategoryResult(
            category=category,
            label=result.value.label,
            items=result.value.items,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="syriac_texts",
                category=category,
                upstream_category=config.upstream_category,
            ),
        )

    async def group(self, group_id: str) -> SyriacTextGroupResult:
        submitted_group = _validate_group_id(group_id)
        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="showsubtexts.php",
                params=(("keyword", submitted_group),),
            ),
            parser=lambda response: parse_syriac_text_group_page(
                response,
                group_id=submitted_group,
            ),
            cache_namespace="syriac-group-v1",
        )
        return SyriacTextGroupResult(
            group_id=submitted_group,
            items=result.value,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="syriac_group",
                group_id=submitted_group,
            ),
        )

    async def missing_words(self, category: str) -> SyriacMissingWordsResult:
        path = _missing_word_path(category)
        result = await self._client.fetch(
            CalRequest(method="GET", path=path),
            parser=lambda response: parse_syriac_missing_words_page(
                response,
                category=category,
            ),
            cache_namespace=f"syriac-missing-words-{category}-v1",
        )
        return SyriacMissingWordsResult(
            category=category,
            dictionary_label=result.value.dictionary_label,
            heading=result.value.heading,
            items=result.value.items,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="syriac_missing_words",
                category=category,
            ),
        )

    async def peshitta_parallel(
        self,
        book: str,
        chapter: int,
        verse: int,
    ) -> SyriacPeshittaResult:
        book_id = _validate_book(book)
        submitted_chapter = _validate_positive_int(chapter, "chapter")
        submitted_verse = _validate_positive_int(verse, "verse")
        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path="showpesh.php",
                data=(
                    ("bookname", book_id),
                    ("chapter", _format_coordinate_number(submitted_chapter)),
                    ("verse", _format_coordinate_number(submitted_verse)),
                ),
            ),
            parser=lambda response: parse_syriac_peshitta_page(
                response,
                book=book,
                chapter=submitted_chapter,
                verse=submitted_verse,
            ),
            cache_namespace="syriac-peshitta-parallel-v1",
        )
        return SyriacPeshittaResult(
            status=result.value.status,
            book=book,
            book_id=book_id,
            chapter=submitted_chapter,
            verse=submitted_verse,
            mt_text=result.value.mt_text,
            peshitta_label=result.value.peshitta_label,
            peshitta_text=result.value.peshitta_text,
            peshitta_url=result.value.peshitta_url,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="syriac_peshitta_parallel",
                book=book,
                book_id=book_id,
                chapter=submitted_chapter,
                verse=submitted_verse,
            ),
        )


def _text_category_config(category: str) -> _TextCategoryConfig:
    if not isinstance(category, str):
        raise CalInputError("category must be a current CAL-MCP Syriac text-category slug")
    config = _TEXT_CATEGORIES.get(category)
    if config is None:
        raise CalInputError("category must be a current CAL-MCP Syriac text-category slug")
    return config


def _validate_group_id(value: object) -> str:
    if type(value) is not str or not value.isdecimal() or int(value) < 1:
        raise CalInputError("group_id must be a positive decimal Syriac GROUP selector")
    return value


def _missing_word_path(category: str) -> str:
    try:
        selected = SyriacMissingWordCategory(category)
    except (ValueError, TypeError):
        choices = ", ".join(syriac_missing_word_category_slugs())
        raise CalInputError(f"category must be one of: {choices}") from None
    return _MISSING_WORD_PATHS[selected]


def _validate_book(book: str) -> str:
    return cal_biblical_book_id(book)


def _validate_positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CalInputError(f"{name} must be an integer")
    if value < 1 or value > 999:
        raise CalInputError(f"{name} must be between 1 and 999")
    return value


def _format_coordinate_number(value: int) -> str:
    return f"{value:02d}" if value < 100 else str(value)


def _validate_category_response_url(source_url: str, config: _TextCategoryConfig) -> None:
    _require_response_path(source_url, config.path, "Syriac text category")
    if config.upstream_category is None:
        return
    query = parse_qs(urlsplit(source_url).query, keep_blank_values=True)
    category = _single_query_value(query, "category", "Syriac text category response")
    if category != config.upstream_category:
        raise SyriacParseError("CAL Syriac category response contradicts the selected category")


def _require_response_path(source_url: str, expected_path: str, context: str) -> None:
    path = urlsplit(source_url).path.rsplit("/", 1)[-1]
    if path != expected_path:
        raise SyriacParseError(f"CAL {context} response came from an unexpected endpoint family")


def _validated_same_origin_url(source_url: str, href: str, expected_path: str) -> str:
    resolved = urljoin(source_url, href)
    source = urlsplit(source_url)
    target = urlsplit(resolved)
    if (target.scheme, target.netloc) != (source.scheme, source.netloc):
        raise SyriacParseError("CAL Syriac result link points outside the CAL origin")
    if target.path.rsplit("/", 1)[-1] != expected_path:
        raise SyriacParseError("CAL Syriac result link targets an unexpected endpoint family")
    return resolved


def _single_query_value(query: dict[str, list[str]], key: str, context: str) -> str:
    values = query.get(key)
    if values is None or len(values) != 1 or not values[0]:
        raise SyriacParseError(f"CAL {context} has invalid {key} query semantics")
    return values[0]


def _require_decimal_identifier(value: str, context: str) -> None:
    if not value.isdecimal() or int(value) < 1:
        raise SyriacParseError(f"CAL {context} is not a positive decimal identifier")


def _row_label(
    line_text: str,
    navigation_text: str,
    upstream_id: str,
    ignored_labels: list[str],
) -> str:
    remainder = _remove_rendered_labels(line_text, ignored_labels)
    if remainder:
        return remainder
    navigation_label = _clean_text(navigation_text)
    if navigation_label.startswith(upstream_id):
        navigation_label = _clean_text(navigation_label[len(upstream_id) :])
    return navigation_label


def _remove_rendered_labels(text: str, labels: list[str]) -> str:
    result = text
    for label in labels:
        cleaned = _clean_text(label)
        if cleaned:
            result = result.replace(cleaned, "", 1)
    return _clean_text(result)


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _make_provenance(
    source_url: str,
    retrieved_at: datetime,
    *,
    operation: str,
    category: str | None = None,
    upstream_category: str | None = None,
    group_id: str | None = None,
    book: str | None = None,
    book_id: str | None = None,
    chapter: int | None = None,
    verse: int | None = None,
) -> SyriacProvenance:
    return SyriacProvenance(
        source="CAL",
        source_url=source_url,
        retrieved_at=retrieved_at,
        operation=operation,
        category=category,
        upstream_category=upstream_category,
        group_id=group_id,
        book=book,
        book_id=book_id,
        chapter=chapter,
        verse=verse,
    )


def _text_item_to_dict(item: SyriacTextItem) -> dict[str, object]:
    return {
        "upstream_id": item.upstream_id,
        "label": item.label,
        "navigation_kind": item.navigation_kind.value,
        "navigation_url": item.navigation_url,
        "info_url": item.info_url,
        "subtext_id": item.subtext_id,
    }


def _missing_word_to_dict(item: SyriacMissingWord) -> dict[str, object]:
    return {
        "lemma_key": item.lemma_key,
        "label": item.label,
        "note": item.note,
        "entry_url": item.entry_url,
    }


def _provenance_to_dict(provenance: SyriacProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "operation": provenance.operation,
        "category": provenance.category,
        "upstream_category": provenance.upstream_category,
        "book": provenance.book,
        "book_id": provenance.book_id,
        "chapter": provenance.chapter,
        "verse": provenance.verse,
    }
