from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import _validate_lemma_key


class BibliographyParseError(CalContentError):
    """Raised when CAL bibliography markup no longer exposes required semantics."""


class BibliographyQueryKind(StrEnum):
    AUTHOR = "author"
    KEYWORD = "keyword"
    LEMMA = "lemma"


@dataclass(frozen=True, slots=True)
class BibliographyAuthorCandidate:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class BibliographyLink:
    label: str
    url: str
    query_kind: BibliographyQueryKind | None = None
    query_value: str | None = None


@dataclass(frozen=True, slots=True)
class BibliographyRecord:
    citation: str
    links: tuple[BibliographyLink, ...] = ()


@dataclass(frozen=True, slots=True)
class BibliographyAuthorOptionsPage:
    candidates: tuple[BibliographyAuthorCandidate, ...]


@dataclass(frozen=True, slots=True)
class BibliographyPage:
    heading: str
    records: tuple[BibliographyRecord, ...]


@dataclass(frozen=True, slots=True)
class BibliographyProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    original_query: str
    submitted_query: str


@dataclass(frozen=True, slots=True)
class BibliographyAuthorOptionsResult:
    prefix: str
    candidates: tuple[BibliographyAuthorCandidate, ...]
    provenance: BibliographyProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "prefix": self.prefix,
            "candidates": [_candidate_to_dict(item) for item in self.candidates],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class BibliographyResult:
    query_kind: BibliographyQueryKind
    query: str
    heading: str
    records: tuple[BibliographyRecord, ...]
    provenance: BibliographyProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "query_kind": self.query_kind.value,
            "query": self.query,
            "heading": self.heading,
            "records": [_record_to_dict(item) for item in self.records],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(slots=True)
class _OpenOption:
    value: str
    parts: list[str] = field(default_factory=list)


class _AuthorOptionsParser(HTMLParser):
    def __init__(self, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.candidates: list[BibliographyAuthorCandidate] = []
        self.all_parts: list[str] = []
        self.target_forms = 0
        self.target_selects = 0
        self._in_target_form = False
        self._in_target_select = False
        self._open_option: _OpenOption | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form":
            if self._in_target_form:
                raise BibliographyParseError("CAL bibliography contains nested author forms")
            action = attributes.get("action")
            if action and _is_expected_cal_target(self.source_url, action, "getbibauthor.php"):
                self.target_forms += 1
                self._in_target_form = True
            return
        if tag == "select" and self._in_target_form:
            if attributes.get("name") == "myauthor":
                self.target_selects += 1
                self._in_target_select = True
            return
        if tag == "option" and self._in_target_select:
            if self._open_option is not None:
                raise BibliographyParseError("CAL bibliography contains nested author options")
            value = attributes.get("value")
            if value is None:
                raise BibliographyParseError("CAL bibliography author option has no value")
            self._open_option = _OpenOption(value=value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self._open_option is not None:
            value = _returned_single_line(self._open_option.value, "author option value")
            label = _clean_text("".join(self._open_option.parts))
            if not label:
                raise BibliographyParseError("CAL bibliography author option has no label")
            self.candidates.append(BibliographyAuthorCandidate(value=value, label=label))
            self._open_option = None
            return
        if tag == "select" and self._in_target_select:
            if self._open_option is not None:
                raise BibliographyParseError("CAL bibliography author option is incomplete")
            self._in_target_select = False
            return
        if tag == "form" and self._in_target_form:
            if self._in_target_select or self._open_option is not None:
                raise BibliographyParseError("CAL bibliography author selector is incomplete")
            self._in_target_form = False

    def handle_data(self, data: str) -> None:
        self.all_parts.append(data)
        if self._open_option is not None:
            self._open_option.parts.append(data)


@dataclass(slots=True)
class _OpenRecordLink:
    href: str
    parts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _RecordBuilder:
    citation_parts: list[str] = field(default_factory=list)
    links: list[BibliographyLink] = field(default_factory=list)
    div_depth: int = 1
    open_link: _OpenRecordLink | None = None


class _BibliographyHTMLParser(HTMLParser):
    def __init__(self, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.headings: list[str] = []
        self.records: list[BibliographyRecord] = []
        self.all_parts: list[str] = []
        self._heading_parts: list[str] | None = None
        self._record: _RecordBuilder | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "h1":
            if self._heading_parts is not None:
                raise BibliographyParseError("CAL bibliography contains nested headings")
            self._heading_parts = []
            return

        if tag == "div":
            classes = set((attributes.get("class") or "").split())
            if self._record is None and "card" in classes:
                self._record = _RecordBuilder()
            elif self._record is not None:
                self._record.div_depth += 1
            return

        if tag == "a" and self._record is not None:
            if self._record.open_link is not None:
                raise BibliographyParseError("CAL bibliography contains nested record links")
            href = attributes.get("href")
            if href is None or not href.strip():
                raise BibliographyParseError("CAL bibliography record link has no target")
            self._record.open_link = _OpenRecordLink(href=href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._heading_parts is not None:
            heading = _clean_text("".join(self._heading_parts))
            if heading:
                self.headings.append(heading)
            self._heading_parts = None
            return

        if tag == "a" and self._record is not None and self._record.open_link is not None:
            label = _clean_text("".join(self._record.open_link.parts))
            self._record.links.append(
                _parse_bibliography_link(
                    self.source_url,
                    self._record.open_link.href,
                    label,
                )
            )
            self._record.open_link = None
            return

        if tag == "div" and self._record is not None:
            self._record.div_depth -= 1
            if self._record.div_depth == 0:
                if self._record.open_link is not None:
                    raise BibliographyParseError("CAL bibliography record link is incomplete")
                citation = _clean_text("".join(self._record.citation_parts))
                if not citation:
                    raise BibliographyParseError("CAL bibliography record has no citation text")
                self.records.append(
                    BibliographyRecord(citation=citation, links=tuple(self._record.links))
                )
                self._record = None

    def handle_data(self, data: str) -> None:
        self.all_parts.append(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._record is None:
            return
        if self._record.open_link is not None:
            self._record.open_link.parts.append(data)
        else:
            self._record.citation_parts.append(data)


_EMPTY_RESULT_RE = re.compile(r"\bNO\s+data\s+FOR\s+.+?\s+ARE\s+CURRENTLY\s+STORED\b", re.I)
_AUTHOR_EMPTY_RE = re.compile(r"\bNo\s+authors\s+found\s+matching\b", re.I)
_QUERY_ENDPOINTS = {
    "getbibauthor.php": BibliographyQueryKind.AUTHOR,
    "getbibsigla.php": BibliographyQueryKind.KEYWORD,
    "getbiblemma.php": BibliographyQueryKind.LEMMA,
}
_AUTHOR_MAX_LENGTH = 160
_KEYWORD_MAX_LENGTH = 128
_LEMMA_MAX_LENGTH = 128


def parse_author_options_page(response: CalResponse) -> BibliographyAuthorOptionsPage:
    parser = _AuthorOptionsParser(response.url)
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    if parser._open_option is not None or parser._in_target_select or parser._in_target_form:
        raise BibliographyParseError("CAL bibliography author selector is incomplete")

    page_text = _clean_text(" ".join(parser.all_parts))
    explicit_empty = _AUTHOR_EMPTY_RE.search(page_text) is not None
    if explicit_empty:
        if parser.candidates or parser.target_forms or parser.target_selects:
            raise BibliographyParseError(
                "CAL bibliography author page contradicts its no-match marker"
            )
        return BibliographyAuthorOptionsPage(candidates=())

    if parser.target_forms != 1 or parser.target_selects != 1 or not parser.candidates:
        raise BibliographyParseError(
            "CAL bibliography author page lacks one recognizable result selector"
        )
    values = [candidate.value for candidate in parser.candidates]
    if len(set(values)) != len(values):
        raise BibliographyParseError("CAL bibliography author selector repeats a candidate value")
    return BibliographyAuthorOptionsPage(candidates=tuple(parser.candidates))


def parse_bibliography_page(response: CalResponse) -> BibliographyPage:
    parser = _BibliographyHTMLParser(response.url)
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    if parser._record is not None or parser._heading_parts is not None:
        raise BibliographyParseError("CAL bibliography page contains incomplete semantic markup")

    headings = [
        heading for heading in parser.headings if heading.startswith("CAL Bibliography for ")
    ]
    if len(headings) != 1:
        raise BibliographyParseError("CAL bibliography page lacks one recognizable result heading")

    page_text = _clean_text(" ".join(parser.all_parts))
    explicit_empty = _EMPTY_RESULT_RE.search(page_text) is not None
    if explicit_empty and parser.records:
        raise BibliographyParseError("CAL bibliography page contradicts its no-data marker")
    if not explicit_empty and not parser.records:
        raise BibliographyParseError(
            "CAL bibliography page contains neither records nor explicit no-data"
        )
    return BibliographyPage(heading=headings[0], records=tuple(parser.records))


class BibliographyService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def authors(self, prefix: str) -> BibliographyAuthorOptionsResult:
        submitted = _prepare_single_line(prefix, "prefix", max_length=6)
        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path="browsenames.php",
                data=(("first3", submitted),),
            ),
            parser=parse_author_options_page,
            cache_namespace="bibliography-authors-v1",
        )
        return BibliographyAuthorOptionsResult(
            prefix=submitted,
            candidates=result.value.candidates,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="bibliography_authors",
                original_query=prefix,
                submitted_query=submitted,
            ),
        )

    async def author(self, author: str) -> BibliographyResult:
        submitted = _prepare_single_line(author, "author", max_length=_AUTHOR_MAX_LENGTH)
        return await self._result(
            query_kind=BibliographyQueryKind.AUTHOR,
            submitted=submitted,
            original=author,
            path="getbibauthor.php",
            operation="bibliography_author",
            cache_namespace="bibliography-author-v1",
        )

    async def keyword(self, keyword: str) -> BibliographyResult:
        submitted = _prepare_single_line(keyword, "keyword", max_length=_KEYWORD_MAX_LENGTH)
        return await self._result(
            query_kind=BibliographyQueryKind.KEYWORD,
            submitted=submitted,
            original=keyword,
            path="getbibsigla.php",
            operation="bibliography_keyword",
            cache_namespace="bibliography-keyword-v1",
        )

    async def lemma(self, lemma_key: str) -> BibliographyResult:
        submitted = _prepare_single_line(lemma_key, "lemma_key", max_length=_LEMMA_MAX_LENGTH)
        _, _, canonical_key = _validate_lemma_key(submitted)
        return await self._result(
            query_kind=BibliographyQueryKind.LEMMA,
            submitted=canonical_key,
            original=lemma_key,
            path="getbiblemma.php",
            operation="bibliography_lemma",
            cache_namespace="bibliography-lemma-v1",
        )

    async def _result(
        self,
        *,
        query_kind: BibliographyQueryKind,
        submitted: str,
        original: str,
        path: str,
        operation: str,
        cache_namespace: str,
    ) -> BibliographyResult:
        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path=path,
                params=(("myauthor", submitted),),
            ),
            parser=parse_bibliography_page,
            cache_namespace=cache_namespace,
        )
        expected_heading = f"CAL Bibliography for {submitted}"
        if result.value.heading != expected_heading:
            raise BibliographyParseError(
                "CAL bibliography result heading does not match the submitted query"
            )
        return BibliographyResult(
            query_kind=query_kind,
            query=submitted,
            heading=result.value.heading,
            records=result.value.records,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation=operation,
                original_query=original,
                submitted_query=submitted,
            ),
        )


def _parse_bibliography_link(source_url: str, href: str, label: str) -> BibliographyLink:
    if not label:
        raise BibliographyParseError("CAL bibliography record link has no label")
    resolved = urljoin(source_url, href)
    source = urlsplit(source_url)
    target = urlsplit(resolved)
    if (target.scheme, target.netloc) != (source.scheme, source.netloc):
        raise BibliographyParseError("CAL bibliography record link points outside the CAL origin")

    filename = target.path.rsplit("/", 1)[-1]
    query_kind = _QUERY_ENDPOINTS.get(filename)
    if query_kind is None:
        return BibliographyLink(label=label, url=resolved)

    values = parse_qs(target.query, keep_blank_values=True).get("myauthor")
    if values is None or len(values) != 1:
        raise BibliographyParseError("CAL bibliography navigation link has invalid query semantics")
    query_value = _returned_single_line(values[0], "bibliography query value")
    return BibliographyLink(
        label=label,
        url=resolved,
        query_kind=query_kind,
        query_value=query_value,
    )


def _is_expected_cal_target(source_url: str, href: str, filename: str) -> bool:
    resolved = urljoin(source_url, href)
    source = urlsplit(source_url)
    target = urlsplit(resolved)
    return (target.scheme, target.netloc) == (source.scheme, source.netloc) and target.path.rsplit(
        "/", 1
    )[-1] == filename


def _prepare_single_line(value: str, name: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    candidate = value.strip(" ")
    if not candidate:
        raise ValueError(f"{name} must not be empty")
    if len(candidate) > max_length:
        raise ValueError(f"{name} must not exceed {max_length} characters")
    if _contains_forbidden_control(candidate):
        raise ValueError(f"{name} must be a single-line value")
    return candidate


def _returned_single_line(value: str, name: str) -> str:
    candidate = value.strip(" ")
    if not candidate or _contains_forbidden_control(candidate):
        raise BibliographyParseError(f"CAL returned an invalid {name}")
    return candidate


def _contains_forbidden_control(value: str) -> bool:
    return any(
        (char.isspace() and char != " ") or ord(char) < 32 or ord(char) == 127 for char in value
    )


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _make_provenance(
    source_url: str,
    retrieved_at: datetime,
    *,
    operation: str,
    original_query: str,
    submitted_query: str,
) -> BibliographyProvenance:
    return BibliographyProvenance(
        source="CAL",
        source_url=source_url,
        retrieved_at=retrieved_at,
        operation=operation,
        original_query=original_query,
        submitted_query=submitted_query,
    )


def _candidate_to_dict(candidate: BibliographyAuthorCandidate) -> dict[str, object]:
    return {"value": candidate.value, "label": candidate.label}


def _link_to_dict(link: BibliographyLink) -> dict[str, object]:
    return {
        "label": link.label,
        "url": link.url,
        "query_kind": link.query_kind.value if link.query_kind is not None else None,
        "query_value": link.query_value,
    }


def _record_to_dict(record: BibliographyRecord) -> dict[str, object]:
    return {
        "citation": record.citation,
        "links": [_link_to_dict(item) for item in record.links],
    }


def _provenance_to_dict(provenance: BibliographyProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "operation": provenance.operation,
        "original_query": provenance.original_query,
        "submitted_query": provenance.submitted_query,
    }
