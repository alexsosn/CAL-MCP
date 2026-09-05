from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse


class DictionaryCollationParseError(CalContentError):
    """Raised when CAL dictionary-collation markup no longer exposes required semantics."""


class DictionarySource(StrEnum):
    JASTROW = "jastrow"
    LEXICON_SYRIACUM = "lexicon_syriacum"
    SYRIAC_LEXICON = "syriac_lexicon"
    COMPENDIOUS_SYRIAC_DICTIONARY = "compendious_syriac_dictionary"
    DJBA = "djba"
    DJPA = "djpa"
    LEVY_TARGUMIM = "levy_targumim"
    MANDAIC_DICTIONARY = "mandaic_dictionary"
    DNSI = "dnsi"
    THESAURUS_SYRIACUS = "thesaurus_syriacus"
    SAMARITAN_ARAMAIC = "samaritan_aramaic"
    SCHULTHESS = "schulthess"
    DCPA = "dcpa"
    JUDEAN_ARAMAIC = "judean_aramaic"
    QUMRAN_ARAMAIC = "qumran_aramaic"


@dataclass(frozen=True, slots=True)
class _SourceSpec:
    code: str
    label: str


_SOURCE_SPECS: dict[DictionarySource, _SourceSpec] = {
    DictionarySource.JASTROW: _SourceSpec("J", "Jastrow"),
    DictionarySource.LEXICON_SYRIACUM: _SourceSpec("L", "Lexicon Syriacum"),
    DictionarySource.SYRIAC_LEXICON: _SourceSpec("K", "A Syriac Lexicon"),
    DictionarySource.COMPENDIOUS_SYRIAC_DICTIONARY: _SourceSpec(
        "j", "A Compendious Syriac Dictionary"
    ),
    DictionarySource.DJBA: _SourceSpec("B", "A Dictionary of Jewish Babylonian Aramaic"),
    DictionarySource.DJPA: _SourceSpec("P", "A Dictionary of Jewish Palestinian Aramaic"),
    DictionarySource.LEVY_TARGUMIM: _SourceSpec(
        "V", "Levy, Chaldäisches Wörterbuch ü.die Targumim"
    ),
    DictionarySource.MANDAIC_DICTIONARY: _SourceSpec("M", "A Mandaic Dictionary"),
    DictionarySource.DNSI: _SourceSpec("W", "Dictionary of the Northwest Semitic Inscriptions"),
    DictionarySource.THESAURUS_SYRIACUS: _SourceSpec("T", "Thesaurus Syriacus"),
    DictionarySource.SAMARITAN_ARAMAIC: _SourceSpec("R", "Dictionary of Samaritan Aramaic"),
    DictionarySource.SCHULTHESS: _SourceSpec("S", "Schulthess Lexicon Syropalaestinum"),
    DictionarySource.DCPA: _SourceSpec(
        "C", "A Dictionary of Christian Palestinian Aramaic"
    ),
    DictionarySource.JUDEAN_ARAMAIC: _SourceSpec("D", "A Dictionary of Judean Aramaic"),
    DictionarySource.QUMRAN_ARAMAIC: _SourceSpec("Q", "Dictionary of Qumran Aramaic Page"),
}


@dataclass(frozen=True, slots=True)
class DictionaryCollationEntry:
    display_lemma: str
    target_lemma_key: str
    gloss: str
    entry_url: str


@dataclass(frozen=True, slots=True)
class DictionaryCollationPage:
    page: str
    source_label: str
    entries: tuple[DictionaryCollationEntry, ...]
    explicit_empty: bool


@dataclass(frozen=True, slots=True)
class DictionaryCollationProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    dictionary_source: DictionarySource
    original_page: str
    submitted_page: str


@dataclass(frozen=True, slots=True)
class DictionaryCollationResult:
    source: DictionarySource
    source_label: str
    page: str
    entries: tuple[DictionaryCollationEntry, ...]
    provenance: DictionaryCollationProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source.value,
            "source_label": self.source_label,
            "page": self.page,
            "entries": [_entry_to_dict(item) for item in self.entries],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class _Link:
    href: str
    label: str


@dataclass(slots=True)
class _OpenLink:
    href: str
    parts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _Paragraph:
    classes: frozenset[str]
    before_parts: list[str] = field(default_factory=list)
    after_parts: list[str] = field(default_factory=list)
    links: list[_Link] = field(default_factory=list)
    open_link: _OpenLink | None = None

    @property
    def text(self) -> str:
        pieces = [*self.before_parts]
        pieces.extend(link.label for link in self.links)
        pieces.extend(self.after_parts)
        return _clean_text(" ".join(pieces))


class _DictionaryCollationHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.titles: list[str] = []
        self.summary_cards = 0
        self.paragraphs: list[_Paragraph] = []
        self._title_parts: list[str] | None = None
        self._card_depth = 0
        self._paragraph: _Paragraph | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "title":
            if self._title_parts is not None:
                raise DictionaryCollationParseError("CAL dictionary collation has nested titles")
            self._title_parts = []
            return

        if tag == "div":
            classes = set((attributes.get("class") or "").split())
            if self._card_depth:
                self._card_depth += 1
            elif "summary-card" in classes:
                self.summary_cards += 1
                self._card_depth = 1
            return

        if not self._card_depth:
            return

        if tag == "p":
            if self._paragraph is not None:
                raise DictionaryCollationParseError(
                    "CAL dictionary collation contains nested result paragraphs"
                )
            self._paragraph = _Paragraph(
                classes=frozenset((attributes.get("class") or "").split())
            )
            return

        if tag == "a" and self._paragraph is not None:
            if self._paragraph.open_link is not None or self._paragraph.links:
                raise DictionaryCollationParseError(
                    "CAL dictionary collation result row contains multiple links"
                )
            href = attributes.get("href")
            if href is None or not href.strip():
                raise DictionaryCollationParseError(
                    "CAL dictionary collation result link has no target"
                )
            self._paragraph.open_link = _OpenLink(href=href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._title_parts is not None:
            title = _clean_text("".join(self._title_parts))
            if title:
                self.titles.append(title)
            self._title_parts = None
            return

        if not self._card_depth:
            return

        if tag == "a" and self._paragraph is not None and self._paragraph.open_link is not None:
            label = _clean_text("".join(self._paragraph.open_link.parts))
            if not label:
                raise DictionaryCollationParseError(
                    "CAL dictionary collation result link has no rendered label"
                )
            self._paragraph.links.append(
                _Link(href=self._paragraph.open_link.href, label=label)
            )
            self._paragraph.open_link = None
            return

        if tag == "p" and self._paragraph is not None:
            if self._paragraph.open_link is not None:
                raise DictionaryCollationParseError(
                    "CAL dictionary collation result link is incomplete"
                )
            self.paragraphs.append(self._paragraph)
            self._paragraph = None
            return

        if tag == "div":
            self._card_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._title_parts is not None:
            self._title_parts.append(data)
        if self._paragraph is None:
            return
        if self._paragraph.open_link is not None:
            self._paragraph.open_link.parts.append(data)
        elif self._paragraph.links:
            self._paragraph.after_parts.append(data)
        else:
            self._paragraph.before_parts.append(data)

    def close(self) -> None:
        super().close()
        if self._title_parts is not None:
            raise DictionaryCollationParseError("CAL dictionary collation title is incomplete")
        if self._paragraph is not None:
            raise DictionaryCollationParseError(
                "CAL dictionary collation result paragraph is incomplete"
            )
        if self._card_depth:
            raise DictionaryCollationParseError(
                "CAL dictionary collation summary card is incomplete"
            )


_TITLE_RE = re.compile(r"^CAL:\s*entries for page (.+?) of (.+)$")
_PAGE_REF_RE = re.compile(r"^[0-9]+(?::[0-9]+)?$")
_EMPTY_MARKER = "No data available for that page."
_MAX_PAGE_LENGTH = 96
_MAX_PAGE_REFS = 16


def parse_dictionary_collation_page(response: CalResponse) -> DictionaryCollationPage:
    parser = _DictionaryCollationHTMLParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    identities: list[tuple[str, str]] = []
    for title in parser.titles:
        match = _TITLE_RE.fullmatch(title)
        if match is None:
            continue
        try:
            page = _normalize_page_reference(match.group(1))
        except ValueError as exc:
            raise DictionaryCollationParseError(
                "CAL dictionary collation returned an invalid page identity"
            ) from exc
        source_label = _returned_single_line(match.group(2), "dictionary label")
        identities.append((page, source_label))

    if len(identities) != 1:
        raise DictionaryCollationParseError(
            "CAL dictionary collation lacks one recognizable page identity"
        )
    if parser.summary_cards != 1:
        raise DictionaryCollationParseError(
            "CAL dictionary collation lacks one recognizable summary card"
        )

    entries: list[DictionaryCollationEntry] = []
    empty_markers = 0
    for paragraph in parser.paragraphs:
        text = paragraph.text
        if "red" in paragraph.classes:
            if text != _EMPTY_MARKER or paragraph.links:
                raise DictionaryCollationParseError(
                    "CAL dictionary collation returned an unrecognized error marker"
                )
            empty_markers += 1
            continue
        if not paragraph.links:
            continue
        entries.append(_parse_entry_paragraph(response.url, paragraph))

    if empty_markers > 1:
        raise DictionaryCollationParseError(
            "CAL dictionary collation repeats its no-data marker"
        )
    if empty_markers and entries:
        raise DictionaryCollationParseError(
            "CAL dictionary collation contradicts its no-data marker"
        )
    if not empty_markers and not entries:
        raise DictionaryCollationParseError(
            "CAL dictionary collation contains neither entries nor explicit no-data"
        )

    page, source_label = identities[0]
    return DictionaryCollationPage(
        page=page,
        source_label=source_label,
        entries=tuple(entries),
        explicit_empty=bool(empty_markers),
    )


def _parse_entry_paragraph(source_url: str, paragraph: _Paragraph) -> DictionaryCollationEntry:
    if len(paragraph.links) != 1:
        raise DictionaryCollationParseError(
            "CAL dictionary collation result row must contain exactly one entry link"
        )
    if _clean_text("".join(paragraph.before_parts)):
        raise DictionaryCollationParseError(
            "CAL dictionary collation result row has text before its lemma link"
        )

    link = paragraph.links[0]
    resolved = urljoin(source_url, link.href)
    source = urlsplit(source_url)
    target = urlsplit(resolved)
    if (target.scheme, target.netloc) != (source.scheme, source.netloc):
        raise DictionaryCollationParseError(
            "CAL dictionary collation entry link points outside the CAL origin"
        )
    if target.fragment or target.path.rsplit("/", 1)[-1] != "oneentry.php":
        raise DictionaryCollationParseError(
            "CAL dictionary collation entry link has an unexpected target"
        )

    query = parse_qs(target.query, keep_blank_values=True)
    if not set(query) <= {"lemma", "cits"}:
        raise DictionaryCollationParseError(
            "CAL dictionary collation entry link has unexpected query controls"
        )
    lemma_values = query.get("lemma")
    if lemma_values is None or len(lemma_values) != 1:
        raise DictionaryCollationParseError(
            "CAL dictionary collation entry link has invalid lemma semantics"
        )
    target_lemma_key = _returned_single_line(lemma_values[0], "entry lemma key")
    cits_values = query.get("cits")
    if cits_values is not None and cits_values != ["no"]:
        raise DictionaryCollationParseError(
            "CAL dictionary collation entry link has invalid citation controls"
        )

    rendered_after = _clean_text("".join(paragraph.after_parts))
    if not rendered_after.startswith(":"):
        raise DictionaryCollationParseError(
            "CAL dictionary collation result row lacks its gloss separator"
        )
    gloss = rendered_after[1:].strip()
    if not gloss:
        raise DictionaryCollationParseError(
            "CAL dictionary collation result row has no gloss"
        )

    return DictionaryCollationEntry(
        display_lemma=link.label,
        target_lemma_key=target_lemma_key,
        gloss=gloss,
        entry_url=resolved,
    )


def _normalize_page_reference(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("page must be a string")
    candidate = value.strip(" ")
    if not candidate:
        raise ValueError("page must not be empty")
    if len(candidate) > _MAX_PAGE_LENGTH:
        raise ValueError(f"page must not exceed {_MAX_PAGE_LENGTH} characters")
    if any((char.isspace() and char != " ") or ord(char) < 32 or ord(char) == 127 for char in candidate):
        raise ValueError("page must be a single-line value")

    parts = candidate.split(",")
    if len(parts) > _MAX_PAGE_REFS:
        raise ValueError(f"page must contain at most {_MAX_PAGE_REFS} references")

    normalized: list[str] = []
    for part in parts:
        page_ref = part.strip(" ")
        if _PAGE_REF_RE.fullmatch(page_ref) is None:
            raise ValueError("page must contain only decimal page or volume:page references")
        normalized.append(page_ref)
    return ", ".join(normalized)


def _returned_single_line(value: str, name: str) -> str:
    candidate = value.strip(" ")
    if not candidate:
        raise DictionaryCollationParseError(f"CAL returned an empty {name}")
    if any((char.isspace() and char != " ") or ord(char) < 32 or ord(char) == 127 for char in candidate):
        raise DictionaryCollationParseError(f"CAL returned an invalid {name}")
    return candidate


class DictionaryCollationService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def collate(
        self,
        source: DictionarySource | str,
        page: str,
    ) -> DictionaryCollationResult:
        try:
            dictionary_source = DictionarySource(source)
        except (TypeError, ValueError) as exc:
            raise ValueError("source must be a supported dictionary source") from exc
        submitted_page = _normalize_page_reference(page)
        spec = _SOURCE_SPECS[dictionary_source]

        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path="searchdicts.php",
                data=(("dict", spec.code), ("page", submitted_page)),
            ),
            parser=parse_dictionary_collation_page,
            cache_namespace="dictionary-collation-v1",
        )
        parsed = result.value
        if parsed.page != submitted_page:
            raise DictionaryCollationParseError(
                "CAL dictionary collation result page does not match the submitted page"
            )
        if parsed.source_label != spec.label:
            raise DictionaryCollationParseError(
                "CAL dictionary collation result source does not match the submitted source"
            )

        return DictionaryCollationResult(
            source=dictionary_source,
            source_label=parsed.source_label,
            page=parsed.page,
            entries=parsed.entries,
            provenance=DictionaryCollationProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="dictionary_collation",
                dictionary_source=dictionary_source,
                original_page=page,
                submitted_page=submitted_page,
            ),
        )


def _entry_to_dict(entry: DictionaryCollationEntry) -> dict[str, object]:
    return {
        "display_lemma": entry.display_lemma,
        "target_lemma_key": entry.target_lemma_key,
        "gloss": entry.gloss,
        "entry_url": entry.entry_url,
    }


def _provenance_to_dict(provenance: DictionaryCollationProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "operation": provenance.operation,
        "dictionary_source": provenance.dictionary_source.value,
        "original_page": provenance.original_page,
        "submitted_page": provenance.submitted_page,
    }
