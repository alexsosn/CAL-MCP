from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from types import MappingProxyType

from cal_mcp.client import CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalInputError, CalParseError
from cal_mcp.lexicon import (
    LemmaRef,
    LexiconParseError,
    _lemma_key_from_href,
    _parse_lemma_header,
    _parse_lines,
    _split_trailing_parenthetical,
    parse_browse_page,
)

_GLOSS_EMPTY_MARKER = "there are no glosses with the word:"
_CITATION_EMPTY_MARKER = "there are no citations with the word:"
_CITATION_PARTS_RE = re.compile(r"\s+:\s*")
_CITATION_ROW_MARKER_RE = re.compile(r"<div\s+class=\"citation-row\b", re.IGNORECASE)


class SearchParseError(CalParseError):
    """Raised when a CAL English-search page no longer exposes required semantics."""


class GlossField(StrEnum):
    ALCHEMY = "alchemy"
    ANATOMY = "anatomy"
    ARCHITECTURE = "architecture"
    ASTRONOMY = "astronomy"
    BOTANY = "botany"
    CANTILLATION = "cantillation"
    CHEMISTRY = "chemistry"
    GEOGRAPHY = "geography"
    GEOLOGY = "geology"
    GEOMETRY = "geometry"
    GRAMMAR = "grammar"
    LITURGY = "liturgy"
    LOGIC = "logic"
    MAGIC = "magic"
    MATHEMATICS = "mathematics"
    MEDICINE = "medicine"
    MUSIC = "music"
    PHILOSOPHY = "philosophy"
    TOPOGRAPHY = "topography"
    ZOOLOGY = "zoology"


@dataclass(frozen=True, slots=True)
class _GlossFieldConfig:
    label: str
    token: str


_GLOSS_FIELD_CONFIG = MappingProxyType(
    {
        GlossField.ALCHEMY: _GlossFieldConfig("alchemy", "(alchem"),
        GlossField.ANATOMY: _GlossFieldConfig("anatomy", "(anat"),
        GlossField.ARCHITECTURE: _GlossFieldConfig("architecture", "(arch"),
        GlossField.ASTRONOMY: _GlossFieldConfig("astronomy", "(astron"),
        GlossField.BOTANY: _GlossFieldConfig("botany, flora", "(bot"),
        GlossField.CANTILLATION: _GlossFieldConfig("cantillation", "(cantill"),
        GlossField.CHEMISTRY: _GlossFieldConfig("chemistry", "(chem"),
        GlossField.GEOGRAPHY: _GlossFieldConfig("geography", "(geog"),
        GlossField.GEOLOGY: _GlossFieldConfig("geology, gemology", "(geol"),
        GlossField.GEOMETRY: _GlossFieldConfig("geometry", "(geom"),
        GlossField.GRAMMAR: _GlossFieldConfig("grammar", "(gram"),
        GlossField.LITURGY: _GlossFieldConfig("liturgy", "(liturg"),
        GlossField.LOGIC: _GlossFieldConfig("logic", "(logic"),
        GlossField.MAGIC: _GlossFieldConfig("magic", "(magic"),
        GlossField.MATHEMATICS: _GlossFieldConfig("mathematics", "(math"),
        GlossField.MEDICINE: _GlossFieldConfig("medicine", "(med"),
        GlossField.MUSIC: _GlossFieldConfig("music", "(music"),
        GlossField.PHILOSOPHY: _GlossFieldConfig("philosophy", "(philos"),
        GlossField.TOPOGRAPHY: _GlossFieldConfig("topography", "(topog"),
        GlossField.ZOOLOGY: _GlossFieldConfig("zoology, fauna", "(zool"),
    }
)


@dataclass(frozen=True, slots=True)
class SearchProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    original_query: str
    submitted_query: str
    search_kind: str


@dataclass(frozen=True, slots=True)
class GlossSearchPage:
    matches: tuple[LemmaRef, ...]


@dataclass(frozen=True, slots=True)
class CitationSearchHit:
    lemma: LemmaRef | None
    lexical_context: str
    reference: str
    source_text: str
    translation: str | None


@dataclass(frozen=True, slots=True)
class CitationSearchPage:
    hits: tuple[CitationSearchHit, ...]


@dataclass(frozen=True, slots=True)
class GlossSearchResult:
    matches: tuple[LemmaRef, ...]
    all_glosses: bool
    provenance: SearchProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "matches": [_lemma_to_dict(item) for item in self.matches],
            "all_glosses": self.all_glosses,
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class GlossFieldSearchResult:
    field: GlossField
    label: str
    matches: tuple[LemmaRef, ...]
    provenance: SearchProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "field": self.field.value,
            "label": self.label,
            "matches": [_lemma_to_dict(item) for item in self.matches],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class CitationTextSearchResult:
    hits: tuple[CitationSearchHit, ...]
    provenance: SearchProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "hits": [_citation_hit_to_dict(item) for item in self.hits],
            "provenance": _provenance_to_dict(self.provenance),
        }


def parse_gloss_search_page(response: CalResponse) -> GlossSearchPage:
    text = response.body.decode("utf-8", errors="replace")
    if _GLOSS_EMPTY_MARKER in text.lower():
        return GlossSearchPage(matches=())
    try:
        browse = parse_browse_page(response)
    except LexiconParseError as exc:
        raise SearchParseError("CAL gloss search page has no recognizable results") from exc
    if not browse.entries:
        raise SearchParseError("CAL gloss search page is unexpectedly empty")
    return GlossSearchPage(matches=browse.entries)


def parse_citation_search_page(response: CalResponse) -> CitationSearchPage:
    text = response.body.decode("utf-8", errors="replace")
    if _CITATION_EMPTY_MARKER in text.lower():
        return CitationSearchPage(hits=())

    if _CITATION_ROW_MARKER_RE.search(text) is not None:
        return CitationSearchPage(hits=_parse_citation_rows(text))

    lines = _parse_lines(response)
    hits: list[CitationSearchHit] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        lemma = _lemma_from_line(line)
        if lemma is None:
            index += 1
            continue

        next_lemma_index = index + 1
        while next_lemma_index < len(lines) and _lemma_from_line(lines[next_lemma_index]) is None:
            next_lemma_index += 1

        payload = lines[index + 1 : next_lemma_index]
        if len(payload) != 2:
            raise SearchParseError(
                "CAL citation search result must contain exactly context and citation text"
            )

        lexical_context = payload[0].text
        citation_text = payload[1].text
        reference, source_text, translation = _parse_citation_text(citation_text)
        hits.append(
            CitationSearchHit(
                lemma=lemma,
                lexical_context=lexical_context,
                reference=reference,
                source_text=source_text,
                translation=translation,
            )
        )
        index = next_lemma_index

    if not hits:
        raise SearchParseError("CAL citation search page has no recognizable results")
    return CitationSearchPage(hits=tuple(hits))


class _CitationSegment:
    """One ``<br>``-delimited piece of a current citation row."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.label_parts: list[str] = []
        self.pos_parts: list[str] = []
        self.after_pos_parts: list[str] = []
        self.pos_count = 0
        self.hrefs: list[str] = []
        self.starts_with_citation = False
        self._seen_content = False

    @property
    def text(self) -> str:
        return _clean("".join(self.parts))

    def start_tag(self, tag: str) -> None:
        if not self._seen_content:
            self.starts_with_citation = tag == "i"
            self._seen_content = True

    def data(self, value: str) -> None:
        self.parts.append(value)
        if value.strip() and not self._seen_content:
            self._seen_content = True


class _CitationRowsParser(HTMLParser):
    """Split current ``citation-row`` containers into ``<br>``-delimited segments (R-048)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[_CitationSegment]] = []
        self._depth = 0
        self._segment: _CitationSegment | None = None
        self._in_link = False
        self._in_pos = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div":
            if self._depth:
                self._depth += 1
            elif "citation-row" in (dict(attrs).get("class") or "").split():
                self._depth = 1
                self._segment = _CitationSegment()
                self.rows.append([self._segment])
            return
        if not self._depth or self._segment is None:
            return
        if tag == "br":
            self._segment = _CitationSegment()
            self.rows[-1].append(self._segment)
            return
        self._segment.start_tag(tag)
        if tag == "pos":
            self._segment.pos_count += 1
            self._in_pos = True
        elif tag == "a":
            self._segment.hrefs.append(dict(attrs).get("href") or "")
            self._in_link = True

    def handle_endtag(self, tag: str) -> None:
        if not self._depth:
            return
        if tag == "div":
            self._depth -= 1
            if not self._depth:
                self._segment = None
                self._in_link = self._in_pos = False
        elif tag == "pos":
            self._in_pos = False
        elif tag == "a":
            self._in_link = False

    def handle_data(self, data: str) -> None:
        if not self._depth or self._segment is None:
            return
        self._segment.data(data)
        if self._in_pos:
            self._segment.pos_parts.append(data)
        elif self._in_link and self._segment.pos_count:
            self._segment.after_pos_parts.append(data)
        elif self._in_link:
            self._segment.label_parts.append(data)


def _parse_citation_rows(text: str) -> tuple[CitationSearchHit, ...]:
    parser = _CitationRowsParser()
    parser.feed(text)
    parser.close()
    hits: list[CitationSearchHit] = []
    for row in parser.rows:
        segments = [segment for segment in row if segment.text]
        if not segments:
            raise SearchParseError("CAL citation search row is empty")
        header, rest = segments[0], segments[1:]
        lemma = _citation_row_lemma(header)
        if any(segment.hrefs or segment.pos_count for segment in rest):
            raise SearchParseError("CAL citation search row has more than one lemma header")
        if not rest or len(rest) % 2:
            raise SearchParseError(
                "CAL citation search row must pair each context with one citation"
            )
        for pair_index in range(0, len(rest), 2):
            context, citation = rest[pair_index], rest[pair_index + 1]
            if context.starts_with_citation or not citation.starts_with_citation:
                raise SearchParseError(
                    "CAL citation search row must pair each context with one citation"
                )
            reference, source_text, translation = _parse_citation_text(citation.text)
            hits.append(
                CitationSearchHit(
                    # CAL renders one header per sense. A further pair in the same row has
                    # no header of its own and is never attributed to this one (R-048).
                    lemma=lemma if pair_index == 0 else None,
                    lexical_context=context.text,
                    reference=reference,
                    source_text=source_text,
                    translation=translation,
                )
            )
    if not hits:
        raise SearchParseError("CAL citation search page has no recognizable results")
    return tuple(hits)


def _citation_row_lemma(header: _CitationSegment) -> LemmaRef:
    keys = [_lemma_key_from_href(href) for href in header.hrefs]
    if len(keys) != 1 or keys[0] is None:
        raise SearchParseError("CAL citation search row lacks exactly one lemma header")
    label = _clean("".join(header.label_parts))
    part_of_speech = _clean("".join(header.pos_parts))
    if header.pos_count != 1 or not part_of_speech or not label:
        raise SearchParseError("CAL citation search header lacks one part of speech")
    # After the POS, CAL renders only the homograph number that the key already carries.
    after_pos = _clean("".join(header.after_pos_parts))
    if after_pos and not keys[0].split(" ", 1)[0].endswith(after_pos):
        raise SearchParseError("CAL citation search header has unexpected text after its POS")
    if after_pos and not (after_pos.startswith("#") and after_pos[1:].isdecimal()):
        raise SearchParseError("CAL citation search header has unexpected text after its POS")
    pronunciation: str | None = None
    parts = _split_trailing_parenthetical(label)
    headword_text = label
    if parts is not None:
        headword_text, pronunciation = parts
    headwords = tuple(part.strip() for part in headword_text.split(",") if part.strip())
    if not headwords:
        raise SearchParseError("CAL citation search header has no headword")
    return LemmaRef(
        lemma_key=keys[0],
        headwords=headwords,
        pronunciation=pronunciation,
        part_of_speech=part_of_speech,
        gloss="",
    )


def _clean(value: str) -> str:
    return " ".join(value.split())


class EnglishSearchService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def search_gloss(
        self,
        query: str,
        *,
        all_glosses: bool = False,
    ) -> GlossSearchResult:
        submitted = _prepare_english_query(query)
        if sum(char.isalpha() for char in submitted) < 3:
            raise CalInputError("CAL gloss search requires at least three letters")

        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path="newsearchmngs.php",
                data=(
                    ("English", submitted),
                    ("secondary", "true" if all_glosses else ""),
                ),
            ),
            parser=parse_gloss_search_page,
            cache_namespace="english-gloss-search-v1",
        )
        return GlossSearchResult(
            matches=result.value.matches,
            all_glosses=all_glosses,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                query,
                submitted,
                "gloss",
            ),
        )

    async def search_gloss_field(self, field: GlossField) -> GlossFieldSearchResult:
        try:
            normalized_field = GlossField(field)
        except (TypeError, ValueError) as exc:
            raise CalInputError("unsupported CAL specialized gloss field") from exc
        config = _GLOSS_FIELD_CONFIG[normalized_field]

        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="newsearchmngs.php",
                params=(("English", config.token), ("secondary", "true")),
            ),
            parser=parse_gloss_search_page,
            cache_namespace="english-gloss-field-v1",
        )
        return GlossFieldSearchResult(
            field=normalized_field,
            label=config.label,
            matches=result.value.matches,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                normalized_field.value,
                config.token,
                "gloss_field",
            ),
        )

    async def search_citations(self, query: str) -> CitationTextSearchResult:
        submitted = _prepare_english_query(query)
        if len(submitted.split(" ")) > 3:
            raise CalInputError("CAL citation-text search accepts at most three words")

        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path="searchcits.php",
                data=(("English", submitted),),
            ),
            parser=parse_citation_search_page,
            cache_namespace="english-citation-search-v1",
        )
        return CitationTextSearchResult(
            hits=result.value.hits,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                query,
                submitted,
                "citation_text",
            ),
        )


def _lemma_from_line(line: object) -> LemmaRef | None:
    links = getattr(line, "links", ())
    for link in links:
        href = getattr(link, "href", "")
        link_text = getattr(link, "text", "")
        lemma_key = _lemma_key_from_href(href)
        if lemma_key is None:
            continue
        parsed = _parse_lemma_header(link_text, lemma_key=lemma_key, require_gloss=False)
        if parsed is not None:
            return parsed
    return None


def _parse_citation_text(text: str) -> tuple[str, str, str | None]:
    parts = _CITATION_PARTS_RE.split(text, maxsplit=2)
    if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
        raise SearchParseError("CAL citation search row is missing reference or source text")
    reference = parts[0].strip()
    source_text = parts[1].strip()
    translation = parts[2].strip() if len(parts) == 3 and parts[2].strip() else None
    return reference, source_text, translation


def _prepare_english_query(value: str) -> str:
    trimmed = value.strip(" ")
    if not trimmed:
        raise CalInputError("CAL English search query must not be empty")
    if any(char.isspace() and char != " " for char in trimmed):
        raise CalInputError("CAL English search words must be separated by ASCII spaces")
    parts = [part for part in trimmed.split(" ") if part]
    if not parts:
        raise CalInputError("CAL English search query must not be empty")
    return " ".join(parts)


def _make_provenance(
    source_url: str,
    retrieved_at: datetime,
    original_query: str,
    submitted_query: str,
    search_kind: str,
) -> SearchProvenance:
    return SearchProvenance(
        source="CAL",
        source_url=source_url,
        retrieved_at=retrieved_at,
        original_query=original_query,
        submitted_query=submitted_query,
        search_kind=search_kind,
    )


def _lemma_to_dict(lemma: LemmaRef) -> dict[str, object]:
    return {
        "lemma_key": lemma.lemma_key,
        "headwords": list(lemma.headwords),
        "pronunciation": lemma.pronunciation,
        "part_of_speech": lemma.part_of_speech,
        "gloss": lemma.gloss,
        "aliases": list(lemma.aliases),
    }


def _citation_hit_to_dict(hit: CitationSearchHit) -> dict[str, object]:
    return {
        "lemma": None if hit.lemma is None else _lemma_to_dict(hit.lemma),
        "lexical_context": hit.lexical_context,
        "reference": hit.reference,
        "source_text": hit.source_text,
        "translation": hit.translation,
    }


def _provenance_to_dict(provenance: SearchProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "original_query": provenance.original_query,
        "submitted_query": provenance.submitted_query,
        "search_kind": provenance.search_kind,
    }


__all__ = [
    "CitationSearchHit",
    "CitationSearchPage",
    "CitationTextSearchResult",
    "EnglishSearchService",
    "GlossField",
    "GlossFieldSearchResult",
    "GlossSearchPage",
    "GlossSearchResult",
    "SearchParseError",
    "SearchProvenance",
    "parse_citation_search_page",
    "parse_gloss_search_page",
]
