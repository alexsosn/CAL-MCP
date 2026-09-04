from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import (
    LemmaRef,
    LexiconParseError,
    _lemma_key_from_href,
    _parse_lemma_header,
    _parse_lines,
    parse_browse_page,
)

_GLOSS_EMPTY_MARKER = "there are no glosses with the word:"
_CITATION_EMPTY_MARKER = "there are no citations with the word:"
_CITATION_PARTS_RE = re.compile(r"\s+:\s*")


class SearchParseError(CalContentError):
    """Raised when a CAL English-search page no longer exposes required semantics."""


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
    lemma: LemmaRef
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

    lines = _parse_lines(response)
    hits: list[CitationSearchHit] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        lemma = _lemma_from_line(line)
        if lemma is None:
            index += 1
            continue

        lexical_context: str | None = None
        citation_text: str | None = None
        cursor = index + 1
        while cursor < len(lines) and _lemma_from_line(lines[cursor]) is None:
            candidate = lines[cursor].text
            if lexical_context is None:
                lexical_context = candidate
            elif citation_text is None:
                citation_text = candidate
                break
            cursor += 1

        if lexical_context is None or citation_text is None:
            raise SearchParseError("CAL citation search result is missing context or citation text")

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
        index = cursor + 1

    if not hits:
        raise SearchParseError("CAL citation search page has no recognizable results")
    return CitationSearchPage(hits=tuple(hits))


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
            raise ValueError("CAL gloss search requires at least three letters")

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

    async def search_citations(self, query: str) -> CitationTextSearchResult:
        submitted = _prepare_english_query(query)
        if len(submitted.split(" ")) > 3:
            raise ValueError("CAL citation-text search accepts at most three words")

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
        raise ValueError("CAL English search query must not be empty")
    if any(char.isspace() and char != " " for char in trimmed):
        raise ValueError("CAL English search words must be separated by ASCII spaces")
    parts = [part for part in trimmed.split(" ") if part]
    if not parts:
        raise ValueError("CAL English search query must not be empty")
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
        "lemma": _lemma_to_dict(hit.lemma),
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
    "GlossSearchPage",
    "GlossSearchResult",
    "SearchParseError",
    "SearchProvenance",
    "parse_citation_search_page",
    "parse_gloss_search_page",
]
