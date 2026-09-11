from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextLine, TextToken

_CAL_SCHEME = "https"
_CAL_HOST = "cal.huc.edu"
_CONTEXT_PATH = "/showachapter.php"
_ASCII_DECIMAL_RE = re.compile(r"^[0-9]+$")
_MISSING_RE = re.compile(
    r"^NO CITATIONS FOR ([0-9]+) ([0-9]+) ARE CURRENTLY STORED$",
    re.IGNORECASE,
)
_IGNORED_TAGS = frozenset({"script", "style"})
_BLOCK_TAGS = frozenset({"center", "div", "h1", "h2", "h3", "p", "td", "th", "tr"})


class LexiconCitationContextParseError(CalContentError):
    """Raised when CAL citation-context markup no longer exposes required semantics."""


class LexiconCitationContextStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class LexiconCitationContextPage:
    status: LexiconCitationContextStatus
    source_label: str | None
    source_info_url: str | None
    lines: tuple[TextLine, ...]


@dataclass(frozen=True, slots=True)
class LexiconCitationContextProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    full_coordinate: str


@dataclass(frozen=True, slots=True)
class LexiconCitationContextResult:
    status: LexiconCitationContextStatus
    full_coordinate: str
    source_label: str | None
    source_info_url: str | None
    lines: tuple[TextLine, ...]
    provenance: LexiconCitationContextProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "full_coordinate": self.full_coordinate,
            "source_label": self.source_label,
            "source_info_url": self.source_info_url,
            "lines": [_line_to_dict(line) for line in self.lines],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class _Link:
    href: str
    text: str


@dataclass(frozen=True, slots=True)
class _Cell:
    text: str
    links: tuple[_Link, ...]


@dataclass(frozen=True, slots=True)
class _Row:
    cells: tuple[_Cell, ...]


@dataclass(slots=True)
class _OpenLink:
    href: str
    parts: list[str] = field(default_factory=list)


class _ContextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[_Row] = []
        self.links: list[_Link] = []
        self.blocks: list[str] = []
        self._row_cells: list[_Cell] | None = None
        self._cell_parts: list[str] | None = None
        self._cell_links: list[_Link] | None = None
        self._open_link: _OpenLink | None = None
        self._block_parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag in _BLOCK_TAGS:
            self._flush_block()
        if tag == "tr":
            if self._row_cells is not None:
                raise LexiconCitationContextParseError("CAL citation context contains nested rows")
            self._row_cells = []
        elif tag in {"td", "th"}:
            if self._cell_parts is not None:
                raise LexiconCitationContextParseError("CAL citation context contains nested cells")
            self._cell_parts = []
            self._cell_links = []
        elif tag == "a":
            if self._open_link is not None:
                raise LexiconCitationContextParseError("CAL citation context contains nested links")
            href = next((value for key, value in attrs if key == "href" and value), None)
            if href is None:
                raise LexiconCitationContextParseError("CAL citation context link has no target")
            self._open_link = _OpenLink(href=href)
        elif tag == "br":
            self._append_data(" ")

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            if tag in _IGNORED_TAGS:
                self._ignored_depth -= 1
            return
        if tag == "a" and self._open_link is not None:
            link = _Link(self._open_link.href, _clean_text("".join(self._open_link.parts)))
            self.links.append(link)
            if self._cell_links is not None:
                self._cell_links.append(link)
            self._open_link = None
        elif tag in {"td", "th"}:
            if self._cell_parts is None or self._cell_links is None:
                raise LexiconCitationContextParseError(
                    "CAL citation context closes an unopened cell"
                )
            if self._row_cells is None:
                raise LexiconCitationContextParseError("CAL citation context cell is outside a row")
            self._row_cells.append(
                _Cell(_clean_text("".join(self._cell_parts)), tuple(self._cell_links))
            )
            self._cell_parts = None
            self._cell_links = None
        elif tag == "tr":
            if self._row_cells is None:
                raise LexiconCitationContextParseError(
                    "CAL citation context closes an unopened row"
                )
            self.rows.append(_Row(tuple(self._row_cells)))
            self._row_cells = None
        if tag in _BLOCK_TAGS:
            self._flush_block()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self._append_data(data)

    def close(self) -> None:
        super().close()
        if self._ignored_depth:
            raise LexiconCitationContextParseError(
                "CAL citation context has an unclosed ignored subtree"
            )
        if (
            self._open_link is not None
            or self._cell_parts is not None
            or self._row_cells is not None
        ):
            raise LexiconCitationContextParseError(
                "CAL citation context has incomplete table markup"
            )
        self._flush_block()

    def _append_data(self, data: str) -> None:
        self._block_parts.append(data)
        if self._cell_parts is not None:
            self._cell_parts.append(data)
        if self._open_link is not None:
            self._open_link.parts.append(data)

    def _flush_block(self) -> None:
        text = _clean_text("".join(self._block_parts))
        if text:
            self.blocks.append(text)
        self._block_parts.clear()


def parse_lexicon_citation_context_page(
    response: CalResponse,
    *,
    requested_full_coordinate: str,
) -> LexiconCitationContextPage:
    requested = _validate_full_coordinate(requested_full_coordinate)
    _validate_response_identity(response.url, requested)

    parser = _ContextHTMLParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    source_label, source_info_url = _parse_source_info(parser.links, response.url)
    lines = tuple(
        line for row in parser.rows if (line := _parse_text_row(row, response.url)) is not None
    )
    missing_matches = [
        match for block in parser.blocks if (match := _MISSING_RE.fullmatch(block)) is not None
    ]

    if missing_matches:
        if len(missing_matches) != 1:
            raise LexiconCitationContextParseError(
                "CAL citation context repeats its no-citations marker"
            )
        match = missing_matches[0]
        if f"{match.group(1)}{match.group(2)}" != requested:
            raise LexiconCitationContextParseError(
                "CAL citation-context missing marker contradicts the requested coordinate"
            )
        if lines:
            raise LexiconCitationContextParseError(
                "CAL citation context mixes a no-citations marker with text rows"
            )
        return LexiconCitationContextPage(
            status=LexiconCitationContextStatus.NOT_FOUND,
            source_label=source_label,
            source_info_url=source_info_url,
            lines=(),
        )

    if not lines:
        raise LexiconCitationContextParseError(
            "CAL citation context has neither text rows nor an explicit no-citations marker"
        )
    if sum(line.coordinate == requested for line in lines) != 1:
        raise LexiconCitationContextParseError(
            "CAL citation context does not contain exactly one requested target row"
        )
    return LexiconCitationContextPage(
        status=LexiconCitationContextStatus.FOUND,
        source_label=source_label,
        source_info_url=source_info_url,
        lines=lines,
    )


class LexiconCitationContextService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def context(self, full_coordinate: str) -> LexiconCitationContextResult:
        requested = _validate_full_coordinate(full_coordinate)

        def parse_requested(response: CalResponse) -> LexiconCitationContextPage:
            return parse_lexicon_citation_context_page(
                response,
                requested_full_coordinate=requested,
            )

        fetched = await self._client.fetch(
            CalRequest(
                method="GET",
                path="showachapter.php",
                params=(("fullcoord", requested),),
            ),
            parser=parse_requested,
            cache_namespace="lexicon-citation-context-v1",
        )
        return LexiconCitationContextResult(
            status=fetched.value.status,
            full_coordinate=requested,
            source_label=fetched.value.source_label,
            source_info_url=fetched.value.source_info_url,
            lines=fetched.value.lines,
            provenance=LexiconCitationContextProvenance(
                source="CAL",
                source_url=fetched.source_url,
                retrieved_at=fetched.retrieved_at,
                operation="lexicon_citation_context",
                full_coordinate=requested,
            ),
        )


def _validate_full_coordinate(value: object) -> str:
    if type(value) is not str or _ASCII_DECIMAL_RE.fullmatch(value) is None or int(value) < 1:
        raise ValueError("full_coordinate must be a positive ASCII-decimal CAL coordinate")
    return value


def _validate_response_identity(source_url: str, requested: str) -> None:
    parsed = urlsplit(source_url)
    if (
        parsed.scheme != _CAL_SCHEME
        or parsed.netloc != _CAL_HOST
        or parsed.path != _CONTEXT_PATH
        or parsed.fragment
    ):
        raise LexiconCitationContextParseError(
            "CAL citation-context response came from an unexpected endpoint"
        )
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) != {"fullcoord"} or query.get("fullcoord") != [requested]:
        raise LexiconCitationContextParseError(
            "CAL citation-context response contradicts the requested coordinate"
        )


def _parse_source_info(links: list[_Link], source_url: str) -> tuple[str | None, str | None]:
    candidates = [link for link in links if _path_looks_like(link.href, "get_file_info.php")]
    if len(candidates) > 1:
        raise LexiconCitationContextParseError(
            "CAL citation context exposes multiple source-information links"
        )
    if not candidates:
        return None, None
    link = candidates[0]
    resolved = _validated_cal_url(source_url, link.href, "/get_file_info.php")
    query = parse_qs(urlsplit(resolved).query, keep_blank_values=True)
    if set(query) != {"coord"}:
        raise LexiconCitationContextParseError(
            "CAL citation-context source-information link has unexpected query semantics"
        )
    _validate_positive_decimal(_single_value(query, "coord"), "source-information coordinate")
    if not link.text:
        raise LexiconCitationContextParseError(
            "CAL citation-context source-information link has no rendered label"
        )
    return link.text, resolved


def _parse_text_row(row: _Row, source_url: str) -> TextLine | None:
    token_candidates = [
        link
        for cell in row.cells
        for link in cell.links
        if _path_looks_like(link.href, "getlex.php")
    ]
    if not token_candidates:
        return None
    if len(row.cells) != 2:
        raise LexiconCitationContextParseError(
            "CAL citation-context text row no longer has two semantic cells"
        )

    coordinate_cell, text_cell = row.cells
    token_links = [link for link in text_cell.links if _path_looks_like(link.href, "getlex.php")]
    if not token_links or len(token_links) != len(token_candidates):
        raise LexiconCitationContextParseError(
            "CAL citation-context lexical anchors moved outside the text cell"
        )

    tokens: list[TextToken] = []
    coordinate: str | None = None
    previous_word: int | None = None
    for link in token_links:
        resolved = _validated_cal_url(source_url, link.href, "/getlex.php")
        query = parse_qs(urlsplit(resolved).query, keep_blank_values=True)
        if set(query) != {"coord", "word"}:
            raise LexiconCitationContextParseError(
                "CAL citation-context token link has unexpected query semantics"
            )
        token_coordinate = _single_value(query, "coord")
        _validate_positive_decimal(token_coordinate, "token coordinate")
        word_value = _single_value(query, "word")
        if _ASCII_DECIMAL_RE.fullmatch(word_value) is None:
            raise LexiconCitationContextParseError(
                "CAL citation-context token has a non-ASCII-decimal word index"
            )
        word_index = int(word_value)
        if previous_word is not None and word_index <= previous_word:
            raise LexiconCitationContextParseError(
                "CAL citation-context token word indexes are not strictly increasing"
            )
        previous_word = word_index
        if coordinate is None:
            coordinate = token_coordinate
        elif token_coordinate != coordinate:
            raise LexiconCitationContextParseError(
                "CAL citation-context text row mixes multiple token coordinates"
            )
        if not link.text:
            raise LexiconCitationContextParseError(
                "CAL citation-context lexical token has no rendered label"
            )
        tokens.append(
            TextToken(
                coordinate=token_coordinate,
                word_index=word_index,
                text=link.text,
                lexical_url=resolved,
            )
        )
    assert coordinate is not None

    comment_candidates = [
        link for link in coordinate_cell.links if _path_looks_like(link.href, "comment.php")
    ]
    if len(comment_candidates) > 1:
        raise LexiconCitationContextParseError(
            "CAL citation-context text row exposes multiple comment links"
        )
    display_coordinate = coordinate_cell.text or None
    comment_url: str | None = None
    if comment_candidates:
        comment = comment_candidates[0]
        comment_url = _validated_cal_url(source_url, comment.href, "/comment.php")
        query = parse_qs(urlsplit(comment_url).query, keep_blank_values=True)
        if set(query) != {"coord"}:
            raise LexiconCitationContextParseError(
                "CAL citation-context comment link has unexpected query semantics"
            )
        comment_coordinate = _single_value(query, "coord")
        _validate_positive_decimal(comment_coordinate, "comment coordinate")
        if comment_coordinate != coordinate:
            raise LexiconCitationContextParseError(
                "CAL citation-context comment coordinate contradicts its text row"
            )
        if not comment.text:
            raise LexiconCitationContextParseError(
                "CAL citation-context comment link has no rendered coordinate"
            )
        display_coordinate = comment.text
    if not text_cell.text:
        raise LexiconCitationContextParseError("CAL citation-context text row has no rendered text")
    return TextLine(
        coordinate=coordinate,
        display_coordinate=display_coordinate,
        text=text_cell.text,
        tokens=tuple(tokens),
        comment_url=comment_url,
    )


def _validated_cal_url(source_url: str, href: str, expected_path: str) -> str:
    resolved = urljoin(source_url, href)
    parsed = urlsplit(resolved)
    if (
        parsed.scheme != _CAL_SCHEME
        or parsed.netloc != _CAL_HOST
        or parsed.path != expected_path
        or parsed.fragment
    ):
        raise LexiconCitationContextParseError(
            "CAL citation-context semantic link targets an unexpected endpoint"
        )
    return resolved


def _path_looks_like(href: str, filename: str) -> bool:
    return urlsplit(href).path.endswith(filename)


def _single_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key)
    if values is None or len(values) != 1 or not values[0]:
        raise LexiconCitationContextParseError(
            f"CAL citation-context link lacks one usable {key} value"
        )
    return values[0]


def _validate_positive_decimal(value: str, context: str) -> None:
    if _ASCII_DECIMAL_RE.fullmatch(value) is None or int(value) < 1:
        raise LexiconCitationContextParseError(f"CAL citation-context {context} is invalid")


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _line_to_dict(line: TextLine) -> dict[str, object]:
    return {
        "coordinate": line.coordinate,
        "display_coordinate": line.display_coordinate,
        "text": line.text,
        "tokens": [
            {
                "coordinate": token.coordinate,
                "word_index": token.word_index,
                "text": token.text,
                "lexical_url": token.lexical_url,
            }
            for token in line.tokens
        ],
        "comment_url": line.comment_url,
    }


def _provenance_to_dict(
    provenance: LexiconCitationContextProvenance,
) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "operation": provenance.operation,
        "full_coordinate": provenance.full_coordinate,
    }


__all__ = [
    "LexiconCitationContextPage",
    "LexiconCitationContextParseError",
    "LexiconCitationContextProvenance",
    "LexiconCitationContextResult",
    "LexiconCitationContextService",
    "LexiconCitationContextStatus",
    "parse_lexicon_citation_context_page",
]
