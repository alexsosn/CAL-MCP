from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.normalization import NormalizedQuery, normalize_query


class LexiconParseError(CalContentError):
    """Raised when CAL lexicon markup no longer contains required semantics."""


class LexiconLookupStatus(StrEnum):
    FOUND = "found"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class Citation:
    reference: str | None
    url: str | None
    text: str


@dataclass(frozen=True, slots=True)
class Sense:
    label_path: tuple[int, ...]
    definition: str
    dialects: tuple[str, ...] = ()
    citations: tuple[Citation, ...] = ()
    heading: str | None = None


@dataclass(frozen=True, slots=True)
class Derivative:
    headword: str
    lemma_key: str | None
    part_of_speech: str | None
    gloss: str | None
    depth: int = 0


@dataclass(frozen=True, slots=True)
class LemmaRef:
    lemma_key: str
    headwords: tuple[str, ...]
    pronunciation: str | None
    part_of_speech: str
    gloss: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LexiconEntry:
    lemma: LemmaRef
    senses: tuple[Sense, ...]
    root: str | None = None
    grammar: tuple[str, ...] = ()
    form_usage: tuple[str, ...] = ()
    derivatives: tuple[Derivative, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Provenance:
    source: str
    source_url: str
    retrieved_at: datetime
    upstream_id: str | None
    original_query: str
    normalized_query: str
    representation: str
    normalization_strategy: str


@dataclass(frozen=True, slots=True)
class BrowsePage:
    entries: tuple[LemmaRef, ...]


@dataclass(frozen=True, slots=True)
class LexiconLookupResult:
    status: LexiconLookupStatus
    matches: tuple[LemmaRef, ...] = ()
    entry: LexiconEntry | None = None
    provenance: Provenance | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "matches": [_lemma_to_dict(item) for item in self.matches],
            "entry": _entry_to_dict(self.entry) if self.entry is not None else None,
            "provenance": (
                _provenance_to_dict(self.provenance) if self.provenance is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class _Link:
    href: str
    text: str


@dataclass(frozen=True, slots=True)
class _Line:
    text: str
    links: tuple[_Link, ...]
    list_depth: int


@dataclass(slots=True)
class _OpenLink:
    tag: str
    href: str
    depth: int = 1
    parts: list[str] = field(default_factory=list)


_IGNORED_CONTENT_TAGS = frozenset({"script", "style"})
_HTML_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_CITATION_BOUNDARY = "\ue000"
_DISPLAY_NONE_RE = re.compile(r"(?:^|;)\s*display\s*:\s*none\s*(?:;|$)", re.IGNORECASE)


_BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "p",
        "section",
        "td",
        "th",
        "tr",
    }
)


class _SemanticHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[_Line] = []
        self._parts: list[str] = []
        self._links: list[_Link] = []
        self._open_link: _OpenLink | None = None
        self._list_depth = -1
        self._line_depth = 0
        self._ignored_depth = 0
        self._semantic_skip_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _IGNORED_CONTENT_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if self._semantic_skip_tags:
            if tag not in _HTML_VOID_TAGS:
                self._semantic_skip_tags.append(tag)
            return

        attributes = {key: value or "" for key, value in attrs}
        classes = frozenset(attributes.get("class", "").split())
        if tag == "span" and "cit-sep" in classes:
            self._parts.append(f" {_CITATION_BOUNDARY} ")
            self._semantic_skip_tags.append(tag)
            return
        if (
            tag == "span"
            and "cit-script" in classes
            and _DISPLAY_NONE_RE.search(attributes.get("style", "")) is not None
        ):
            self._semantic_skip_tags.append(tag)
            return

        if self._open_link is not None and tag == self._open_link.tag:
            self._open_link.depth += 1
        if tag in {"ul", "ol"}:
            self._flush()
            self._list_depth += 1
            return
        if tag in _BLOCK_TAGS:
            self._flush()
            self._line_depth = max(self._list_depth, 0)
        if tag == "br":
            self._flush()
        if tag == "a" and self._open_link is None:
            href = attributes.get("href", "")
            self._open_link = _OpenLink(tag="a", href=href)
        elif tag == "span" and "cit-ref-plain" in classes and self._open_link is None:
            self._open_link = _OpenLink(tag="span", href="")

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            if tag in _IGNORED_CONTENT_TAGS:
                self._ignored_depth -= 1
            return
        if self._semantic_skip_tags:
            if tag != self._semantic_skip_tags[-1]:
                raise LexiconParseError("CAL lexicon has malformed excluded citation content")
            self._semantic_skip_tags.pop()
            return
        if self._open_link is not None and tag == self._open_link.tag:
            self._open_link.depth -= 1
            if self._open_link.depth == 0:
                text = _clean_text("".join(self._open_link.parts))
                self._links.append(_Link(href=self._open_link.href, text=text))
                self._open_link = None
        if tag in _BLOCK_TAGS or tag == "br":
            self._flush()
        if tag in {"ul", "ol"}:
            self._flush()
            self._list_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self._parts.append(data)
        if self._open_link is not None:
            self._open_link.parts.append(data)

    def close(self) -> None:
        super().close()
        if self._ignored_depth:
            raise LexiconParseError("CAL lexicon has an unclosed ignored content subtree")
        if self._semantic_skip_tags:
            raise LexiconParseError("CAL lexicon has an unclosed excluded citation subtree")
        self._flush()

    def _flush(self) -> None:
        text = _clean_text("".join(self._parts))
        if text:
            self.lines.append(
                _Line(text=text, links=tuple(self._links), list_depth=self._line_depth)
            )
        self._parts.clear()
        self._links.clear()
        self._line_depth = max(self._list_depth, 0)


_TOKEN_RE = re.compile(r"\S+")
_NUMBER_RE = re.compile(r"^(\d+)$")
_SUBNUMBER_RE = re.compile(r"^\((\d+)\)$")
_STEM_HEADING_RE = re.compile(r"^(?P<heading>.+?)\s+\d+\s+senses?▶$")
_CITATION_MARKER_RE = re.compile(r"^▶\s*(?P<count>\d+)\s+citations?$", re.IGNORECASE)
_CITATION_SEPARATOR_RE = re.compile(r"(?:\s+;\s*|\s*;\s+)")
_SECTION_FORM = "§Form & Usage▶"
_SECTION_DERIVATIVES = "☛Derivatives▶"
_SECTION_NOTES = "✎Notes & Bibliography▶"
_SECTION_CONCORDANCE = "🔍Concordance▶"
_FULL_BIBLIOGRAPHY = "📖 Full Bibliography"
_NOT_FOUND_PHRASES = (
    "no matching lexical entries were found",
    "no matching entries were found",
    "no matches were found",
)
_DIALECT_EXACT = frozenset(
    {
        "BA",
        "BA-Da",
        "BA-Ez",
        "CPA",
        "Com",
        "Com.",
        "Common Aramaic",
        "Gal",
        "Hat",
        "Hatran",
        "JBA",
        "JBAg",
        "JLAtg",
        "JPA",
        "Jud",
        "LJLA",
        "Man",
        "Mandaic",
        "Nab",
        "Nabatean",
        "OA",
        "OfA",
        "OfAGen",
        "PTA",
        "Palm",
        "Palmyrene",
        "Qum",
        "Qumran",
        "Sam",
        "Samaritan",
        "Syr",
        "Syriac",
        "Targum",
    }
)
_DIALECT_PREFIXES = ("BA-", "JBA", "JPA", "OA-", "OfA-", "Qum", "Syr")
_NOUN_POS_QUALIFIERS = frozenset({"c.", "coll.", "du.", "f.", "m.", "pl.", "sg.", "t."})
_STEM_TOKENS = frozenset({"G", "D", "C", "N", "Gt", "Dt", "Ct", "Et", "It", "Š", "Št"})


@dataclass(slots=True)
class _SenseBuilder:
    label_path: tuple[int, ...]
    heading: str | None = None
    definition: str = ""
    dialects: tuple[str, ...] = ()
    citations: list[Citation] = field(default_factory=list)
    expected_citations: int | None = None
    citation_mode: bool = False

    def freeze(self) -> Sense:
        if not self.definition:
            raise LexiconParseError("CAL lexicon sense is missing its definition")
        if self.expected_citations is not None and len(self.citations) != self.expected_citations:
            raise LexiconParseError(
                "CAL lexicon citation count does not match the rendered citation marker"
            )
        return Sense(
            label_path=self.label_path,
            definition=self.definition,
            dialects=self.dialects,
            citations=tuple(self.citations),
            heading=self.heading,
        )


def parse_browse_page(response: CalResponse) -> BrowsePage:
    lines = _parse_lines(response)
    entries: list[LemmaRef] = []

    for index, line in enumerate(lines):
        for link in line.links:
            lemma_key = _lemma_key_from_href(link.href)
            if lemma_key is None:
                continue
            parsed = _parse_lemma_header(link.text, lemma_key=lemma_key, require_gloss=False)
            if parsed is None:
                continue

            aliases: tuple[str, ...] = ()
            before_link = line.text.split(link.text, 1)[0]
            if "→" in before_link:
                alias_text = before_link.split("→", 1)[0].strip()
                aliases = tuple(part.strip() for part in alias_text.split(",") if part.strip())

            gloss = parsed.gloss
            for next_line in lines[index + 1 :]:
                if any(_lemma_key_from_href(item.href) is not None for item in next_line.links):
                    break
                if next_line.text:
                    gloss = next_line.text
                    break

            entries.append(
                LemmaRef(
                    lemma_key=parsed.lemma_key,
                    headwords=parsed.headwords,
                    pronunciation=parsed.pronunciation,
                    part_of_speech=parsed.part_of_speech,
                    gloss=gloss,
                    aliases=aliases,
                )
            )

    if entries:
        return BrowsePage(entries=tuple(entries))

    page_text = " ".join(line.text.lower() for line in lines)
    if any(phrase in page_text for phrase in _NOT_FOUND_PHRASES):
        return BrowsePage(entries=())
    raise LexiconParseError(
        "CAL lexicon browse page contains neither entries nor explicit no-match"
    )


def parse_lexicon_entry(response: CalResponse, *, lemma_key: str) -> LexiconEntry:
    lines = _parse_lines(response)
    header_index = -1
    lemma: LemmaRef | None = None
    for index, line in enumerate(lines):
        parsed = _parse_lemma_header(line.text, lemma_key=lemma_key, require_gloss=True)
        if parsed is not None:
            lemma = parsed
            header_index = index
            break
    if lemma is None:
        raise LexiconParseError("CAL lexicon entry is missing a recognizable lemma header")

    senses: list[Sense] = []
    current: _SenseBuilder | None = None
    previous_path: tuple[int, ...] | None = None
    root: str | None = None
    grammar: list[str] = []
    form_usage: list[str] = []
    derivatives: list[Derivative] = []
    notes: list[str] = []
    mode = "senses"

    def finish_current() -> None:
        nonlocal current, previous_path
        if current is not None:
            frozen = current.freeze()
            senses.append(frozen)
            previous_path = frozen.label_path
            current = None

    for line in lines[header_index + 1 :]:
        text = line.text

        if text == _SECTION_FORM:
            finish_current()
            mode = "form"
            continue
        if text == _SECTION_DERIVATIVES:
            finish_current()
            mode = "derivatives"
            continue
        if text == _SECTION_NOTES:
            finish_current()
            mode = "notes"
            continue
        if text == _SECTION_CONCORDANCE:
            finish_current()
            mode = "ignore"
            continue
        if text.startswith(_FULL_BIBLIOGRAPHY):
            finish_current()
            mode = "ignore"
            continue

        if mode == "form":
            form_usage.append(text)
            continue
        if mode == "derivatives":
            derivative = _parse_derivative(line)
            if derivative is not None:
                derivatives.append(derivative)
            continue
        if mode == "notes":
            notes.append(text)
            continue
        if mode == "ignore":
            continue

        if text.startswith("√"):
            root = text[1:].strip()
            continue
        if current is None and not senses and _looks_like_grammar(text):
            grammar.append(text)
            continue

        stem_match = _STEM_HEADING_RE.match(text)
        if stem_match:
            finish_current()
            current = _SenseBuilder(label_path=(), heading=stem_match.group("heading"))
            continue

        number_match = _NUMBER_RE.match(text)
        subnumber_match = _SUBNUMBER_RE.match(text)
        label_match = number_match or subnumber_match
        if label_match is not None:
            finish_current()
            value = int(label_match.group(1))
            path = (value,) if number_match else _subsense_path(previous_path, value)
            current = _SenseBuilder(label_path=path)
            continue

        if current is None:
            current = _SenseBuilder(label_path=())

        citation_marker = _CITATION_MARKER_RE.match(text)
        if citation_marker is not None:
            current.expected_citations = int(citation_marker.group("count"))
            current.citation_mode = True
            continue
        if current.citation_mode:
            current.citations.extend(_parse_citations(line, response.url))
            continue
        if not current.definition:
            current.definition = text
            continue
        if _looks_like_dialect(text):
            current.dialects = tuple(part.strip() for part in text.split(",") if part.strip())
            continue
        current.definition = f"{current.definition} {text}"

    finish_current()
    if not senses:
        raise LexiconParseError("CAL lexicon entry contains no complete sense definitions")

    return LexiconEntry(
        lemma=lemma,
        senses=tuple(senses),
        root=root,
        grammar=tuple(grammar),
        form_usage=tuple(form_usage),
        derivatives=tuple(derivatives),
        notes=tuple(notes),
    )


class LexiconLookupService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def lookup(self, query: str, *, lemma_key: str | None = None) -> LexiconLookupResult:
        normalized = normalize_query(query)
        prefix = _browse_prefix(normalized.normalized)
        browse_request = CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("first3", f'"{prefix}"'),),
        )
        browse_result = await self._client.fetch(
            browse_request,
            parser=parse_browse_page,
            cache_namespace="lexicon-browse-v1",
        )
        browse_provenance = _make_provenance(
            normalized,
            source_url=browse_result.source_url,
            retrieved_at=browse_result.retrieved_at,
            upstream_id=None,
        )

        matches = tuple(
            item
            for item in browse_result.value.entries
            if _query_matches(normalized.normalized, item)
        )
        if not matches:
            return LexiconLookupResult(
                status=LexiconLookupStatus.NOT_FOUND,
                provenance=browse_provenance,
            )

        if lemma_key is not None:
            selected = next((item for item in matches if item.lemma_key == lemma_key), None)
            if selected is None:
                raise ValueError("lemma_key must identify one of the matching CAL candidates")
        elif len(matches) > 1:
            return LexiconLookupResult(
                status=LexiconLookupStatus.AMBIGUOUS,
                matches=matches,
                provenance=browse_provenance,
            )
        else:
            selected = matches[0]

        selected_key = selected.lemma_key

        def parse_selected(response: CalResponse) -> LexiconEntry:
            return parse_lexicon_entry(response, lemma_key=selected_key)

        entry_result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="cal_entry_web.php",
                params=(("lemma", selected_key),),
            ),
            parser=parse_selected,
            cache_namespace="lexicon-entry-v1",
        )
        return LexiconLookupResult(
            status=LexiconLookupStatus.FOUND,
            matches=(selected,),
            entry=entry_result.value,
            provenance=_make_provenance(
                normalized,
                source_url=entry_result.source_url,
                retrieved_at=entry_result.retrieved_at,
                upstream_id=selected_key,
            ),
        )


def _parse_lines(response: CalResponse) -> list[_Line]:
    parser = _SemanticHTMLParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    return parser.lines


def _parse_lemma_header(
    text: str,
    *,
    lemma_key: str,
    require_gloss: bool,
) -> LemmaRef | None:
    tokens = list(_TOKEN_RE.finditer(text))
    pos_index = next(
        (index for index, token in enumerate(tokens) if _looks_like_pos_token(token.group(0))),
        None,
    )
    if pos_index is None:
        return None

    pos_start = tokens[pos_index].start()
    pos_end = tokens[pos_index].end()
    first_pos_token = tokens[pos_index].group(0)
    if first_pos_token == "n.":
        qualifier_index = pos_index + 1
        while (
            qualifier_index < len(tokens)
            and tokens[qualifier_index].group(0) in _NOUN_POS_QUALIFIERS
        ):
            pos_end = tokens[qualifier_index].end()
            qualifier_index += 1

    label = text[:pos_start].strip()
    part_of_speech = text[pos_start:pos_end].strip()
    gloss = text[pos_end:].strip()
    if gloss.startswith("#") and gloss[1:].isdigit():
        gloss = ""
    if require_gloss and not gloss:
        return None
    if not label or not part_of_speech:
        return None

    pronunciation: str | None = None
    if label.endswith(")") and " (" in label:
        headword_text, pronunciation_text = label.rsplit(" (", 1)
        pronunciation = pronunciation_text[:-1].strip()
    else:
        headword_text = label
    headwords = tuple(part.strip() for part in headword_text.split(",") if part.strip())
    if not headwords:
        return None
    return LemmaRef(
        lemma_key=lemma_key,
        headwords=headwords,
        pronunciation=pronunciation,
        part_of_speech=part_of_speech,
        gloss=gloss,
    )


def _looks_like_pos_token(value: str) -> bool:
    if not value or not value[0].isascii() or not value[0].isalpha() or "." not in value:
        return False
    return all(char.isascii() and (char.isalnum() or char in "./-") for char in value)


def _lemma_key_from_href(href: str) -> str | None:
    if not href:
        return None
    parsed = urlsplit(href)
    if not (parsed.path.endswith("oneentry.php") or parsed.path.endswith("cal_entry_web.php")):
        return None
    values = parse_qs(parsed.query, keep_blank_values=True).get("lemma")
    if not values or not values[0].strip():
        return None
    return values[0]


def _subsense_path(previous: tuple[int, ...] | None, value: int) -> tuple[int, ...]:
    if value < 1:
        raise LexiconParseError("CAL lexicon subsense labels must be positive integers")
    if not previous:
        return (value,)
    if value == 1:
        return (*previous, 1)

    for index in range(len(previous) - 1, -1, -1):
        if previous[index] == value - 1:
            return (*previous[:index], value)
    raise LexiconParseError("CAL lexicon subsense numbering cannot be placed safely")


def _looks_like_grammar(text: str) -> bool:
    tokens = text.split()
    return bool(tokens) and all(token in _STEM_TOKENS for token in tokens)


def _looks_like_dialect(text: str) -> bool:
    parts = tuple(part.strip() for part in text.split(",") if part.strip())
    if not parts:
        return False
    return all(_is_dialect_label(part) for part in parts)


def _is_dialect_label(value: str) -> bool:
    return value in _DIALECT_EXACT or value.startswith(_DIALECT_PREFIXES)


def _parse_citations(line: _Line, base_url: str) -> list[Citation]:
    locations: list[tuple[_Link, int]] = []
    cursor = 0
    for link in line.links:
        start = line.text.find(link.text, cursor)
        if start < 0:
            raise LexiconParseError("CAL citation link text is missing from its rendered line")
        locations.append((link, start))
        cursor = start + len(link.text)

    if not locations:
        return [_raw_citation(part) for part in _split_citation_segments(line.text)]

    citations: list[Citation] = []
    prefix = line.text[: locations[0][1]]
    citations.extend(_raw_citation(part) for part in _split_citation_segments(prefix))

    for index, (link, start) in enumerate(locations):
        text_start = start + len(link.text)
        text_end = locations[index + 1][1] if index + 1 < len(locations) else len(line.text)
        segments = _split_citation_segments(line.text[text_start:text_end])
        linked_text = segments[0] if segments else ""
        reference = link.text.removesuffix("↗").strip()
        citations.append(
            Citation(
                reference=reference,
                url=urljoin(base_url, link.href) if link.href else None,
                text=linked_text,
            )
        )
        citations.extend(_raw_citation(part) for part in segments[1:])
    return citations


def _split_citation_segments(value: str) -> list[str]:
    if _CITATION_BOUNDARY in value:
        return [part.strip() for part in value.split(_CITATION_BOUNDARY) if part.strip()]
    return [part.strip() for part in _CITATION_SEPARATOR_RE.split(value.strip()) if part.strip()]


def _raw_citation(text: str) -> Citation:
    return Citation(reference=None, url=None, text=text)


def _parse_derivative(line: _Line) -> Derivative | None:
    link = next((item for item in line.links if _lemma_key_from_href(item.href) is not None), None)
    if link is None:
        return None
    remainder = line.text.split(link.text, 1)[1].strip() if link.text in line.text else ""
    part_of_speech: str | None = None
    gloss: str | None = None
    if "—" in remainder:
        left, right = remainder.split("—", 1)
        part_of_speech = left.strip() or None
        gloss = right.strip() or None
    elif remainder:
        gloss = remainder
    return Derivative(
        headword=link.text,
        lemma_key=_lemma_key_from_href(link.href),
        part_of_speech=part_of_speech,
        gloss=gloss,
        depth=line.list_depth,
    )


def _browse_prefix(value: str) -> str:
    result: list[str] = []
    base_characters = 0
    for char in value:
        if unicodedata.category(char).startswith("M"):
            if result:
                result.append(char)
            continue
        if base_characters >= 3:
            break
        result.append(char)
        base_characters += 1
    if not result:
        raise ValueError("normalized CAL query has no browse prefix")
    return "".join(result)


def _query_matches(query: str, lemma: LemmaRef) -> bool:
    needle = _comparison_surface(query)
    candidates = (*lemma.headwords, *lemma.aliases)
    return any(_comparison_surface(candidate) == needle for candidate in candidates)


_HEBREW_TO_ROMAN = {
    "א": "ˀ",
    "ב": "b",
    "ג": "g",
    "ד": "d",
    "ה": "h",
    "ו": "w",
    "ז": "z",
    "ח": "ḥ",
    "ט": "ṭ",
    "י": "y",
    "כ": "k",
    "ך": "k",
    "ל": "l",
    "מ": "m",
    "ם": "m",
    "נ": "n",
    "ן": "n",
    "ס": "s",
    "ע": "ˁ",
    "פ": "p",
    "ף": "p",
    "צ": "ṣ",
    "ץ": "ṣ",
    "ק": "q",
    "ר": "r",
    "ש": "š",
    "ת": "t",
}
_SYRIAC_TO_ROMAN = {
    "ܐ": "ˀ",
    "ܒ": "b",
    "ܓ": "g",
    "ܕ": "d",
    "ܗ": "h",
    "ܘ": "w",
    "ܙ": "z",
    "ܚ": "ḥ",
    "ܛ": "ṭ",
    "ܝ": "y",
    "ܟ": "k",
    "ܠ": "l",
    "ܡ": "m",
    "ܢ": "n",
    "ܣ": "s",
    "ܥ": "ˁ",
    "ܦ": "p",
    "ܧ": "ṗ",
    "ܨ": "ṣ",
    "ܩ": "q",
    "ܪ": "r",
    "ܫ": "š",
    "ܬ": "t",
}
_HEBREW_SIN_DOT = "\u05c2"


def _comparison_surface(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.strip(" "))
    output: list[str] = []
    index = 0
    while index < len(normalized):
        char = normalized[index]
        if unicodedata.category(char).startswith("M"):
            index += 1
            continue

        next_index = index + 1
        marks: list[str] = []
        while next_index < len(normalized) and unicodedata.category(
            normalized[next_index]
        ).startswith("M"):
            marks.append(normalized[next_index])
            next_index += 1

        if char == "ש" and _HEBREW_SIN_DOT in marks:
            output.append("ś")
        else:
            output.append(_HEBREW_TO_ROMAN.get(char, _SYRIAC_TO_ROMAN.get(char, char)))
        index = next_index
    return unicodedata.normalize("NFC", "".join(output))


def _make_provenance(
    normalized: NormalizedQuery,
    *,
    source_url: str,
    retrieved_at: datetime,
    upstream_id: str | None,
) -> Provenance:
    return Provenance(
        source="CAL",
        source_url=source_url,
        retrieved_at=retrieved_at,
        upstream_id=upstream_id,
        original_query=normalized.original,
        normalized_query=normalized.normalized,
        representation=normalized.representation.value,
        normalization_strategy=normalized.strategy.value,
    )


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _lemma_to_dict(lemma: LemmaRef) -> dict[str, object]:
    return {
        "lemma_key": lemma.lemma_key,
        "headwords": list(lemma.headwords),
        "pronunciation": lemma.pronunciation,
        "part_of_speech": lemma.part_of_speech,
        "gloss": lemma.gloss,
        "aliases": list(lemma.aliases),
    }


def _citation_to_dict(citation: Citation) -> dict[str, object]:
    return {"reference": citation.reference, "url": citation.url, "text": citation.text}


def _sense_to_dict(sense: Sense) -> dict[str, object]:
    return {
        "label_path": list(sense.label_path),
        "heading": sense.heading,
        "definition": sense.definition,
        "dialects": list(sense.dialects),
        "citations": [_citation_to_dict(item) for item in sense.citations],
    }


def _derivative_to_dict(derivative: Derivative) -> dict[str, object]:
    return {
        "headword": derivative.headword,
        "lemma_key": derivative.lemma_key,
        "part_of_speech": derivative.part_of_speech,
        "gloss": derivative.gloss,
        "depth": derivative.depth,
    }


def _entry_to_dict(entry: LexiconEntry) -> dict[str, object]:
    return {
        "lemma": _lemma_to_dict(entry.lemma),
        "senses": [_sense_to_dict(item) for item in entry.senses],
        "root": entry.root,
        "grammar": list(entry.grammar),
        "form_usage": list(entry.form_usage),
        "derivatives": [_derivative_to_dict(item) for item in entry.derivatives],
        "notes": list(entry.notes),
    }


def _provenance_to_dict(provenance: Provenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "upstream_id": provenance.upstream_id,
        "original_query": provenance.original_query,
        "normalized_query": provenance.normalized_query,
        "representation": provenance.representation,
        "normalization_strategy": provenance.normalization_strategy,
    }


__all__ = [
    "BrowsePage",
    "Citation",
    "Derivative",
    "LemmaRef",
    "LexiconEntry",
    "LexiconLookupResult",
    "LexiconLookupService",
    "LexiconLookupStatus",
    "LexiconParseError",
    "Provenance",
    "Sense",
    "parse_browse_page",
    "parse_lexicon_entry",
]
