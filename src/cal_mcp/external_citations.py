from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import SplitResult, parse_qs, urljoin, urlsplit

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lemma_key import validate_lemma_key

_CAL_ORIGIN = ("https", "cal.huc.edu")
_DIALECT_PATH = "/display.notext.abbrevs.php"
_CITATIONS_PATH = "/displaycits.abbrev.php"
_ENTRY_PATH = "/oneentry.php"
_DIALECT_RE = re.compile(r"^[0-9]{1,6}$")
_MAX_SOURCE_ABBREV_CHARS = 128
_RESULT_COUNT_RE = re.compile(r"^([0-9]+)\s+citations?$", re.IGNORECASE)
_EMPTY_CITATIONS_RE = re.compile(
    r'\bNo\s+citations\s+for\s+"(.+?)"\s+are\s+currently\s+stored\.',
    re.IGNORECASE,
)
_DIALECT_MARKER = "Choose a Dialect"
_SOURCE_HEADING = "Texts With Citations, No Full Text Yet"
_SOURCE_EMPTY_MARKER = "No extra citations for that dialect are currently found."
_CITATION_HEADING_PREFIX = "Citations for "
_BIDI_FORMATTING = frozenset(
    {
        "\u200e",
        "\u200f",
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",
        "\u2066",
        "\u2067",
        "\u2068",
        "\u2069",
    }
)


class ExternalCitationParseError(CalContentError):
    """Raised when CAL's external-citation markup loses required semantics."""


@dataclass(frozen=True, slots=True)
class ExternalCitationDialect:
    dialect_id: str
    label: str


@dataclass(frozen=True, slots=True)
class ExternalCitationSource:
    abbreviation: str
    description: str | None
    citations_url: str


@dataclass(frozen=True, slots=True)
class ExternalCitationHit:
    lemma_key: str
    lemma_label: str
    part_of_speech: str | None
    entry_url: str
    reference: str
    gloss: str | None
    source_text: str | None
    translation: str | None


@dataclass(frozen=True, slots=True)
class ExternalCitationDialectPage:
    dialects: tuple[ExternalCitationDialect, ...]


@dataclass(frozen=True, slots=True)
class ExternalCitationSourcePage:
    sources: tuple[ExternalCitationSource, ...]


@dataclass(frozen=True, slots=True)
class ExternalCitationPage:
    source_abbrev: str
    total: int
    citations: tuple[ExternalCitationHit, ...]


@dataclass(frozen=True, slots=True)
class ExternalCitationProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    dialect_id: str | None = None
    source_abbrev: str | None = None


@dataclass(frozen=True, slots=True)
class ExternalCitationDialectResult:
    dialects: tuple[ExternalCitationDialect, ...]
    provenance: ExternalCitationProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "dialects": [_dialect_to_dict(item) for item in self.dialects],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class ExternalCitationSourceResult:
    dialect_id: str
    sources: tuple[ExternalCitationSource, ...]
    provenance: ExternalCitationProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "dialect_id": self.dialect_id,
            "sources": [_source_to_dict(item) for item in self.sources],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class ExternalCitationResult:
    source_abbrev: str
    total: int
    citations: tuple[ExternalCitationHit, ...]
    provenance: ExternalCitationProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "source_abbrev": self.source_abbrev,
            "total": self.total,
            "citations": [_citation_to_dict(item) for item in self.citations],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(slots=True)
class _OpenLink:
    href: str
    parts: list[str] = field(default_factory=list)


class _IgnoredMarkupParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ignored_tag: str | None = None
        self.all_parts: list[str] = []

    def _start_ignored(self, tag: str) -> bool:
        if self.ignored_tag is not None:
            return True
        if tag in {"style", "script"}:
            self.ignored_tag = tag
            return True
        return False

    def _end_ignored(self, tag: str) -> bool:
        if self.ignored_tag is None:
            return False
        if tag == self.ignored_tag:
            self.ignored_tag = None
        return True

    def _record_data(self, data: str) -> bool:
        if self.ignored_tag is not None:
            return False
        self.all_parts.append(data)
        return True

    def ensure_complete(self) -> None:
        if self.ignored_tag is not None:
            raise ExternalCitationParseError(
                "CAL external-citation page contains an incomplete ignored subtree"
            )


class _DialectParser(_IgnoredMarkupParser):
    def __init__(self, source_url: str) -> None:
        super().__init__()
        self.source_url = source_url
        self.dialects: list[ExternalCitationDialect] = []
        self.open_link: _OpenLink | None = None
        self.open_dialect_id: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._start_ignored(tag):
            return
        if tag != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if not href:
            return
        target = urljoin(self.source_url, href)
        split = urlsplit(target)
        if split.path != _DIALECT_PATH:
            return
        _require_cal_origin(split, "dialect navigation")
        query = parse_qs(split.query, keep_blank_values=True)
        if set(query) - {"dial", "dial1"}:
            raise ExternalCitationParseError("CAL dialect navigation has unexpected query fields")
        dialect_values = query.get("dial", [])
        if len(dialect_values) != 1 or _DIALECT_RE.fullmatch(dialect_values[0]) is None:
            raise ExternalCitationParseError("CAL dialect navigation has an invalid dialect ID")
        if "dial1" in query and query["dial1"] != ["6"]:
            raise ExternalCitationParseError("CAL dialect navigation changed its fixed UI mode")
        if self.open_link is not None:
            raise ExternalCitationParseError("CAL dialect navigation contains nested links")
        self.open_link = _OpenLink(href=target)
        self.open_dialect_id = dialect_values[0]

    def handle_endtag(self, tag: str) -> None:
        if self._end_ignored(tag):
            return
        if tag != "a" or self.open_link is None:
            return
        label = _clean_text("".join(self.open_link.parts))
        if not label or self.open_dialect_id is None:
            raise ExternalCitationParseError("CAL dialect navigation has no rendered label")
        self.dialects.append(ExternalCitationDialect(dialect_id=self.open_dialect_id, label=label))
        self.open_link = None
        self.open_dialect_id = None

    def handle_data(self, data: str) -> None:
        if not self._record_data(data):
            return
        if self.open_link is not None:
            self.open_link.parts.append(data)


@dataclass(slots=True)
class _SourceRow:
    div_depth: int = 1
    abbreviation: str | None = None
    citations_url: str | None = None
    link: _OpenLink | None = None
    description_parts: list[str] = field(default_factory=list)
    description_depth: int = 0


class _SourceParser(_IgnoredMarkupParser):
    def __init__(self, source_url: str) -> None:
        super().__init__()
        self.source_url = source_url
        self.sources: list[ExternalCitationSource] = []
        self.row: _SourceRow | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._start_ignored(tag):
            return
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if self.row is None:
            if tag == "div" and "cit-row" in classes:
                self.row = _SourceRow()
            return

        if tag == "div":
            self.row.div_depth += 1

        if self.row.description_depth:
            self.row.description_depth += 1
            return

        if tag == "span" and "cit-defined" in classes:
            self.row.description_depth = 1
            return

        if tag == "a" and "cit-abbrev" in classes:
            if self.row.link is not None or self.row.abbreviation is not None:
                raise ExternalCitationParseError(
                    "CAL external-source row contains multiple abbreviation links"
                )
            href = attributes.get("href")
            if not href:
                raise ExternalCitationParseError(
                    "CAL external-source abbreviation link has no target"
                )
            abbreviation, target = _parse_source_target(self.source_url, href)
            self.row.abbreviation = abbreviation
            self.row.citations_url = target
            self.row.link = _OpenLink(href=target)

    def handle_endtag(self, tag: str) -> None:
        if self._end_ignored(tag):
            return
        if self.row is None:
            return

        if self.row.description_depth:
            self.row.description_depth -= 1
            if self.row.description_depth:
                return

        if tag == "a" and self.row.link is not None:
            label = _clean_text("".join(self.row.link.parts))
            if label != self.row.abbreviation:
                raise ExternalCitationParseError(
                    "CAL external-source link label does not match its abbreviation"
                )
            self.row.link = None
            return

        if tag == "div":
            self.row.div_depth -= 1
            if self.row.div_depth == 0:
                self._finish_row()

    def handle_data(self, data: str) -> None:
        if not self._record_data(data):
            return
        if self.row is None:
            return
        if self.row.link is not None:
            self.row.link.parts.append(data)
        if self.row.description_depth:
            self.row.description_parts.append(data)

    def _finish_row(self) -> None:
        assert self.row is not None
        if self.row.link is not None or self.row.description_depth:
            raise ExternalCitationParseError("CAL external-source row is incomplete")
        if self.row.abbreviation is None or self.row.citations_url is None:
            raise ExternalCitationParseError(
                "CAL external-source row lacks one abbreviation navigation target"
            )
        description = _optional_text("".join(self.row.description_parts))
        self.sources.append(
            ExternalCitationSource(
                abbreviation=self.row.abbreviation,
                description=description,
                citations_url=self.row.citations_url,
            )
        )
        self.row = None


@dataclass(slots=True)
class _CitationEntry:
    div_depth: int = 1
    lemma_key: str | None = None
    entry_url: str | None = None
    lemma_link: _OpenLink | None = None
    fields: dict[str, str | None] = field(default_factory=dict)
    capture_field: str | None = None
    capture_parts: list[str] = field(default_factory=list)
    capture_depth: int = 0


class _CitationParser(_IgnoredMarkupParser):
    _SPAN_FIELDS = {
        "cit-pos": "part_of_speech",
        "cit-coord": "reference",
        "cit-gloss": "gloss",
        "cit-text": "source_text",
        "result-count": "result_count",
    }

    def __init__(self, source_url: str) -> None:
        super().__init__()
        self.source_url = source_url
        self.headings: list[str] = []
        self.reported_counts: list[int] = []
        self.citations: list[ExternalCitationHit] = []
        self.heading_parts: list[str] | None = None
        self.entry: _CitationEntry | None = None
        self.page_capture_field: str | None = None
        self.page_capture_parts: list[str] = []
        self.page_capture_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._start_ignored(tag):
            return
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if self.heading_parts is not None:
            return
        if tag == "h1" and self.entry is None:
            self.heading_parts = []
            return

        if self.entry is None:
            if self.page_capture_field is not None:
                self.page_capture_depth += 1
                return
            if tag == "span" and "result-count" in classes:
                self.page_capture_field = "result_count"
                self.page_capture_parts = []
                self.page_capture_depth = 1
                return
            if tag == "div" and "cit-entry" in classes:
                self.entry = _CitationEntry()
            return

        if tag == "div":
            self.entry.div_depth += 1

        if self.entry.capture_field is not None:
            self.entry.capture_depth += 1
            return

        if tag == "a" and "cit-lemma" in classes:
            if self.entry.lemma_link is not None or self.entry.lemma_key is not None:
                raise ExternalCitationParseError(
                    "CAL external citation contains multiple lexical links"
                )
            href = attributes.get("href")
            if not href:
                raise ExternalCitationParseError("CAL external citation lexical link has no target")
            lemma_key, target = _parse_entry_target(self.source_url, href)
            self.entry.lemma_key = lemma_key
            self.entry.entry_url = target
            self.entry.lemma_link = _OpenLink(href=target)
            return

        if tag == "span":
            field_name = next(
                (field for css, field in self._SPAN_FIELDS.items() if css in classes),
                None,
            )
            if field_name is not None and field_name != "result_count":
                self._start_entry_capture(field_name)
                return

        if tag == "div" and "cit-xlation" in classes:
            self._start_entry_capture("translation")

    def handle_endtag(self, tag: str) -> None:
        if self._end_ignored(tag):
            return

        if self.heading_parts is not None:
            if tag == "h1":
                heading = _clean_text("".join(self.heading_parts))
                if heading:
                    self.headings.append(heading)
                self.heading_parts = None
            return

        if self.entry is None:
            if self.page_capture_field is not None:
                self.page_capture_depth -= 1
                if self.page_capture_depth == 0:
                    value = _clean_text("".join(self.page_capture_parts))
                    match = _RESULT_COUNT_RE.fullmatch(value)
                    if match is None:
                        raise ExternalCitationParseError(
                            "CAL external-citation result count is malformed"
                        )
                    self.reported_counts.append(int(match.group(1)))
                    self.page_capture_field = None
                    self.page_capture_parts = []
            return

        if self.entry.capture_field is not None:
            self.entry.capture_depth -= 1
            if self.entry.capture_depth == 0:
                field_name = self.entry.capture_field
                self.entry.fields[field_name] = _optional_text("".join(self.entry.capture_parts))
                self.entry.capture_field = None
                self.entry.capture_parts = []

        if tag == "a" and self.entry.lemma_link is not None:
            label = _clean_text("".join(self.entry.lemma_link.parts))
            if not label:
                raise ExternalCitationParseError(
                    "CAL external citation lexical link has no rendered label"
                )
            self.entry.fields["lemma_label"] = label
            self.entry.lemma_link = None
            return

        if tag == "div":
            self.entry.div_depth -= 1
            if self.entry.div_depth == 0:
                self._finish_entry()

    def handle_data(self, data: str) -> None:
        if not self._record_data(data):
            return
        if self.heading_parts is not None:
            self.heading_parts.append(data)
            return
        if self.entry is None:
            if self.page_capture_field is not None:
                self.page_capture_parts.append(data)
            return
        if self.entry.lemma_link is not None:
            self.entry.lemma_link.parts.append(data)
        if self.entry.capture_field is not None:
            self.entry.capture_parts.append(data)

    def _start_entry_capture(self, field_name: str) -> None:
        assert self.entry is not None
        if field_name in self.entry.fields:
            raise ExternalCitationParseError(
                f"CAL external citation repeats {field_name.replace('_', ' ')}"
            )
        self.entry.capture_field = field_name
        self.entry.capture_parts = []
        self.entry.capture_depth = 1

    def _finish_entry(self) -> None:
        assert self.entry is not None
        if self.entry.lemma_link is not None or self.entry.capture_field is not None:
            raise ExternalCitationParseError("CAL external citation row is incomplete")
        lemma_key = self.entry.lemma_key
        entry_url = self.entry.entry_url
        lemma_label = self.entry.fields.get("lemma_label")
        reference = self.entry.fields.get("reference")
        if lemma_key is None or entry_url is None or lemma_label is None or reference is None:
            raise ExternalCitationParseError(
                "CAL external citation lacks lemma navigation or source reference"
            )
        self.citations.append(
            ExternalCitationHit(
                lemma_key=lemma_key,
                lemma_label=lemma_label,
                part_of_speech=self.entry.fields.get("part_of_speech"),
                entry_url=entry_url,
                reference=reference,
                gloss=self.entry.fields.get("gloss"),
                source_text=self.entry.fields.get("source_text"),
                translation=self.entry.fields.get("translation"),
            )
        )
        self.entry = None


def parse_external_citation_dialects_page(
    response: CalResponse,
) -> ExternalCitationDialectPage:
    parser = _DialectParser(response.url)
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    parser.ensure_complete()
    if parser.open_link is not None:
        raise ExternalCitationParseError("CAL dialect navigation contains an incomplete link")
    if _DIALECT_MARKER not in _clean_text(" ".join(parser.all_parts)):
        raise ExternalCitationParseError("CAL citation finder lacks its dialect selector marker")
    ids = [item.dialect_id for item in parser.dialects]
    if len(set(ids)) != len(ids):
        raise ExternalCitationParseError("CAL citation finder repeats a dialect ID")
    if not parser.dialects:
        raise ExternalCitationParseError("CAL citation finder contains no recognizable dialects")
    return ExternalCitationDialectPage(dialects=tuple(parser.dialects))


def parse_external_citation_sources_page(
    response: CalResponse,
) -> ExternalCitationSourcePage:
    parser = _SourceParser(response.url)
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    parser.ensure_complete()
    if parser.row is not None:
        raise ExternalCitationParseError("CAL external-source page contains an incomplete row")

    page_text = _clean_text(" ".join(parser.all_parts))
    if _SOURCE_HEADING not in page_text:
        raise ExternalCitationParseError("CAL external-source page lacks its result heading")
    explicit_empty = _SOURCE_EMPTY_MARKER.lower() in page_text.lower()
    if explicit_empty and parser.sources:
        raise ExternalCitationParseError("CAL external-source page contradicts its empty marker")
    abbreviations = [item.abbreviation for item in parser.sources]
    if len(set(abbreviations)) != len(abbreviations):
        raise ExternalCitationParseError("CAL external-source page repeats an abbreviation")
    if not explicit_empty and not parser.sources:
        raise ExternalCitationParseError(
            "CAL external-source page contains neither source rows nor explicit empty state"
        )
    return ExternalCitationSourcePage(sources=tuple(parser.sources))


def parse_external_citations_page(response: CalResponse) -> ExternalCitationPage:
    parser = _CitationParser(response.url)
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    parser.ensure_complete()
    if (
        parser.entry is not None
        or parser.heading_parts is not None
        or parser.page_capture_field is not None
    ):
        raise ExternalCitationParseError(
            "CAL external-citation page has incomplete semantic markup"
        )

    headings = [
        heading for heading in parser.headings if heading.startswith(_CITATION_HEADING_PREFIX)
    ]
    if len(headings) != 1:
        raise ExternalCitationParseError("CAL external-citation page lacks one result heading")
    source_abbrev = headings[0].removeprefix(_CITATION_HEADING_PREFIX)
    if not source_abbrev:
        raise ExternalCitationParseError("CAL external-citation result heading has no source")

    page_text = _clean_text(" ".join(parser.all_parts))
    empty_match = _EMPTY_CITATIONS_RE.search(page_text)
    explicit_empty = empty_match is not None
    if empty_match is not None and _clean_text(empty_match.group(1)) != source_abbrev:
        raise ExternalCitationParseError(
            "CAL external-citation empty marker contradicts its result heading"
        )
    if explicit_empty and parser.citations:
        raise ExternalCitationParseError("CAL external-citation page contradicts its empty marker")
    if not explicit_empty and not parser.citations:
        raise ExternalCitationParseError(
            "CAL external-citation page contains neither citations nor explicit empty state"
        )
    if len(parser.reported_counts) > 1:
        raise ExternalCitationParseError("CAL external-citation page repeats its result count")
    total = 0 if explicit_empty else len(parser.citations)
    if parser.reported_counts:
        reported = parser.reported_counts[0]
        if reported != len(parser.citations):
            raise ExternalCitationParseError(
                "CAL external-citation result count does not match parsed citations"
            )
        total = reported
    return ExternalCitationPage(
        source_abbrev=source_abbrev,
        total=total,
        citations=tuple(parser.citations),
    )


class ExternalCitationService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def dialects(self) -> ExternalCitationDialectResult:
        result = await self._client.fetch(
            CalRequest(method="GET", path="citfinder.html"),
            parser=parse_external_citation_dialects_page,
            cache_namespace="external-citation-dialects-v1",
        )
        return ExternalCitationDialectResult(
            dialects=result.value.dialects,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="external_citation_dialects",
            ),
        )

    async def sources(self, dialect_id: str) -> ExternalCitationSourceResult:
        submitted = _prepare_dialect_id(dialect_id)
        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="display.notext.abbrevs.php",
                params=(("dial1", "6"), ("dial", submitted)),
            ),
            parser=parse_external_citation_sources_page,
            cache_namespace="external-citation-sources-v1",
        )
        return ExternalCitationSourceResult(
            dialect_id=submitted,
            sources=result.value.sources,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="external_citation_sources",
                dialect_id=submitted,
            ),
        )

    async def citations(self, source_abbrev: str) -> ExternalCitationResult:
        submitted = _prepare_source_abbrev(source_abbrev)
        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="displaycits.abbrev.php",
                params=(("abbrev", submitted),),
            ),
            parser=parse_external_citations_page,
            cache_namespace="external-citations-v1",
        )
        if result.value.source_abbrev != submitted:
            raise ExternalCitationParseError(
                "CAL external-citation result heading does not match the submitted source"
            )
        return ExternalCitationResult(
            source_abbrev=submitted,
            total=result.value.total,
            citations=result.value.citations,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="external_citations",
                source_abbrev=submitted,
            ),
        )


def _parse_source_target(source_url: str, href: str) -> tuple[str, str]:
    target = urljoin(source_url, href)
    split = urlsplit(target)
    if split.path != _CITATIONS_PATH:
        raise ExternalCitationParseError(
            "CAL external-source abbreviation targets an unexpected endpoint"
        )
    _require_cal_origin(split, "external-source navigation")
    query = parse_qs(split.query, keep_blank_values=True)
    if set(query) != {"abbrev"} or len(query["abbrev"]) != 1:
        raise ExternalCitationParseError(
            "CAL external-source abbreviation has ambiguous query semantics"
        )
    abbreviation = _returned_single_line(query["abbrev"][0], "source abbreviation")
    if len(abbreviation) > _MAX_SOURCE_ABBREV_CHARS:
        raise ExternalCitationParseError("CAL returned an invalid source abbreviation")
    return abbreviation, target


def _parse_entry_target(source_url: str, href: str) -> tuple[str, str]:
    target = urljoin(source_url, href)
    split = urlsplit(target)
    if split.path != _ENTRY_PATH:
        raise ExternalCitationParseError(
            "CAL external citation lexical link targets an unexpected endpoint"
        )
    _require_cal_origin(split, "external-citation lexical navigation")
    query = parse_qs(split.query, keep_blank_values=True)
    if set(query) != {"lemma", "cits"}:
        raise ExternalCitationParseError(
            "CAL external citation lexical link has unexpected query semantics"
        )
    lemma_values = query["lemma"]
    if len(lemma_values) != 1 or query["cits"] != ["all"]:
        raise ExternalCitationParseError(
            "CAL external citation lexical link has ambiguous query semantics"
        )
    returned = _returned_single_line(lemma_values[0], "lemma key")
    try:
        _, _, canonical = validate_lemma_key(returned)
    except ValueError as exc:
        raise ExternalCitationParseError(
            "CAL external citation returned a malformed lemma key"
        ) from exc
    return canonical, target


def _require_cal_origin(split: SplitResult, context: str) -> None:
    if (split.scheme.lower(), split.netloc.lower()) != _CAL_ORIGIN:
        raise ExternalCitationParseError(f"CAL {context} escapes the CAL origin")


def _prepare_dialect_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("dialect_id must be a string")
    candidate = value.strip(" ")
    if _DIALECT_RE.fullmatch(candidate) is None:
        raise ValueError("dialect_id must contain 1-6 ASCII decimal digits")
    return candidate


def _prepare_source_abbrev(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("source_abbrev must be a string")
    candidate = value.strip(" ")
    if not candidate:
        raise ValueError("source_abbrev must not be empty")
    if len(candidate) > _MAX_SOURCE_ABBREV_CHARS:
        raise ValueError(f"source_abbrev must be at most {_MAX_SOURCE_ABBREV_CHARS} characters")
    if any(
        (char.isspace() and char != " ") or unicodedata.category(char) in {"Cc", "Cf", "Cs"}
        for char in candidate
    ):
        raise ValueError("source_abbrev may contain only ordinary spaces, not controls")
    return candidate


def _returned_single_line(value: str, field_name: str) -> str:
    candidate = value.strip(" ")
    if not candidate or any(
        (char.isspace() and char != " ") or unicodedata.category(char) in {"Cc", "Cf", "Cs"}
        for char in candidate
    ):
        raise ExternalCitationParseError(f"CAL returned an invalid {field_name}")
    return candidate


def _clean_text(value: str) -> str:
    without_bidi = "".join(char for char in value if char not in _BIDI_FORMATTING)
    return " ".join(without_bidi.split())


def _optional_text(value: str) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _make_provenance(
    source_url: str,
    retrieved_at: datetime,
    *,
    operation: str,
    dialect_id: str | None = None,
    source_abbrev: str | None = None,
) -> ExternalCitationProvenance:
    return ExternalCitationProvenance(
        source="CAL",
        source_url=source_url,
        retrieved_at=retrieved_at,
        operation=operation,
        dialect_id=dialect_id,
        source_abbrev=source_abbrev,
    )


def _dialect_to_dict(item: ExternalCitationDialect) -> dict[str, object]:
    return {"dialect_id": item.dialect_id, "label": item.label}


def _source_to_dict(item: ExternalCitationSource) -> dict[str, object]:
    return {
        "abbreviation": item.abbreviation,
        "description": item.description,
        "citations_url": item.citations_url,
    }


def _citation_to_dict(item: ExternalCitationHit) -> dict[str, object]:
    return {
        "lemma_key": item.lemma_key,
        "lemma_label": item.lemma_label,
        "part_of_speech": item.part_of_speech,
        "entry_url": item.entry_url,
        "reference": item.reference,
        "gloss": item.gloss,
        "source_text": item.source_text,
        "translation": item.translation,
    }


def _provenance_to_dict(item: ExternalCitationProvenance) -> dict[str, object]:
    return {
        "source": item.source,
        "source_url": item.source_url,
        "retrieved_at": item.retrieved_at.isoformat(),
        "operation": item.operation,
        "dialect_id": item.dialect_id,
        "source_abbrev": item.source_abbrev,
    }


__all__ = [
    "ExternalCitationDialect",
    "ExternalCitationDialectPage",
    "ExternalCitationDialectResult",
    "ExternalCitationHit",
    "ExternalCitationPage",
    "ExternalCitationParseError",
    "ExternalCitationProvenance",
    "ExternalCitationResult",
    "ExternalCitationService",
    "ExternalCitationSource",
    "ExternalCitationSourcePage",
    "ExternalCitationSourceResult",
    "parse_external_citation_dialects_page",
    "parse_external_citation_sources_page",
    "parse_external_citations_page",
]
