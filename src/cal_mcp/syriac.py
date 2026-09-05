from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lemma_key import validate_lemma_key


class SyriacParseError(CalContentError):
    """Raised when CAL Syriac markup no longer exposes required semantics."""


class SyriacTextNavigationKind(StrEnum):
    TEXT = "text"
    GROUP = "group"


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
            self._append_script_data(" ")
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

_MISSING_WORD_PATHS = {
    "adjectives": "display_missing_adj.php",
    "adverbs": "display_missingSL.php",
    "miscellaneous": "display_missing_misc.php",
    "nomina-agentis": "display_missing_nomag.php",
    "abstracts": "display_missingU.php",
    "verbal-nouns": "display_missing_vn.php",
    "verbs": "display_missing_verbs.php",
    "masculine-nouns": "display_missing.mascnouns.php",
    "feminine-nouns": "display_missing.femnouns.php",
}

_BOOK_IDS = {
    "Gen": "01",
    "Exod": "02",
    "Levit": "03",
    "Numb": "04",
    "Deut": "05",
    "Joshua": "06",
    "Judges": "07",
    "1 Sam": "08",
    "2 Sam": "09",
    "1 Kings": "10",
    "2 Kings": "11",
    "Isaiah": "12",
    "Jeremiah": "13",
    "Ezekiel": "14",
    "Hosea": "15",
    "Joel": "16",
    "Amos": "17",
    "Obadiah": "18",
    "Jonah": "19",
    "Micah": "20",
    "Nahum": "21",
    "Hab.": "22",
    "Zeph.": "23",
    "Haggai": "24",
    "Zechariah": "25",
    "Malachi": "26",
    "Psalms": "27",
    "Job": "28",
    "Proverbs": "33",
    "Ruth": "30",
    "Song of Songs": "29",
    "Qoheleth": "31",
    "Lamentations": "32",
    "Esther": "36",
    "1 Chronicles": "34",
    "2 Chronicles": "35",
}

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

    items: list[SyriacTextItem] = []
    seen_ids: set[str] = set()
    for line in parser.lines:
        navigation: list[tuple[SyriacTextNavigationKind, str, str, _Link]] = []
        info_links: list[tuple[str, str, _Link]] = []
        for link in line.links:
            target = urlsplit(urljoin(response.url, link.href))
            endpoint = target.path.rsplit("/", 1)[-1]
            if endpoint == "get_a_chapter.php":
                resolved = _validated_same_origin_url(response.url, link.href, endpoint)
                upstream_id = _single_query_value(
                    parse_qs(urlsplit(resolved).query, keep_blank_values=True),
                    "file",
                    "Syriac direct-text navigation",
                )
                _require_decimal_identifier(upstream_id, "Syriac text file")
                navigation.append((SyriacTextNavigationKind.TEXT, upstream_id, resolved, link))
            elif endpoint == "showsubtexts.php":
                resolved = _validated_same_origin_url(response.url, link.href, endpoint)
                upstream_id = _single_query_value(
                    parse_qs(urlsplit(resolved).query, keep_blank_values=True),
                    "keyword",
                    "Syriac grouped-text navigation",
                )
                _require_decimal_identifier(upstream_id, "Syriac grouped-text keyword")
                navigation.append((SyriacTextNavigationKind.GROUP, upstream_id, resolved, link))
            elif endpoint == "get_file_info.php":
                resolved = _validated_same_origin_url(response.url, link.href, endpoint)
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
    return SyriacTextCategoryPage(label=matching_headings[0], items=tuple(items))


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
            _, _, canonical_key = validate_lemma_key(lemma_key)
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

    expected_heading = f"{_PESHITTA_HEADING_PREFIX}{book} {chapter}:{verse}"
    headings = [text for text in parser.centers if text.startswith(_PESHITTA_HEADING_PREFIX)]
    if headings != [expected_heading]:
        raise SyriacParseError("CAL Peshitta heading does not match the requested verse")

    page_text = _clean_text(" ".join(parser.all_parts))
    coordinate_error = _COORDINATE_ERROR_RE.search(page_text) is not None
    hebrew = _clean_text("".join(parser.hebrew_parts))
    syriac = _clean_text("".join(parser.syriac_parts))
    peshitta_links = [link for link in parser.links if _clean_text(link.text) == "Peshitta:"]

    has_any_result_data = bool(hebrew or syriac or peshitta_links)
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
                upstream_category=path,
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
        raise ValueError("category must be a current CAL-MCP Syriac text-category slug")
    config = _TEXT_CATEGORIES.get(category)
    if config is None:
        raise ValueError("category must be a current CAL-MCP Syriac text-category slug")
    return config


def _missing_word_path(category: str) -> str:
    if not isinstance(category, str):
        raise ValueError("category must be a current CAL-MCP Syriac missing-word category slug")
    path = _MISSING_WORD_PATHS.get(category)
    if path is None:
        raise ValueError("category must be a current CAL-MCP Syriac missing-word category slug")
    return path


def _validate_book(book: str) -> str:
    if not isinstance(book, str) or book not in _BOOK_IDS:
        raise ValueError("book must be one exact current CAL biblical book label")
    return _BOOK_IDS[book]


def _validate_positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 1 or value > 999:
        raise ValueError(f"{name} must be between 1 and 999")
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
