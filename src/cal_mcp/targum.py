from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.biblical import cal_biblical_book_id
from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import _validate_lemma_key


class TargumParseError(CalContentError):
    """Raised when CAL Targum markup no longer exposes required semantics."""


class TargumParallelStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class TargumSourceReading:
    label: str
    text: str
    chapter_url: str | None = None


@dataclass(frozen=True, slots=True)
class TargumParallelPage:
    status: TargumParallelStatus
    mt_text: str | None
    readings: tuple[TargumSourceReading, ...]


@dataclass(frozen=True, slots=True)
class TargumConcordanceRow:
    section: str | None
    label: str
    count: int
    example_url: str


@dataclass(frozen=True, slots=True)
class TargumConcordancePage:
    rows: tuple[TargumConcordanceRow, ...]
    total: int


@dataclass(frozen=True, slots=True)
class TargumHebrewLemmaCandidate:
    mt_lemma_id: str
    label: str
    pos: str


@dataclass(frozen=True, slots=True)
class TargumHebrewLemmaOptionsPage:
    candidates: tuple[TargumHebrewLemmaCandidate, ...]


@dataclass(frozen=True, slots=True)
class TargumReflex:
    lemma_key: str
    label: str
    frequency: int
    example_url: str


@dataclass(frozen=True, slots=True)
class TargumReflexPage:
    source_label: str
    mt_hebrew_lemma: str
    reflexes: tuple[TargumReflex, ...]


@dataclass(frozen=True, slots=True)
class TargumProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    book: str | None = None
    book_id: str | None = None
    chapter: int | None = None
    verse: int | None = None
    lemma_key: str | None = None
    targum: str | None = None
    initial: str | None = None
    mt_lemma_id: str | None = None


@dataclass(frozen=True, slots=True)
class TargumParallelResult:
    status: TargumParallelStatus
    book: str
    book_id: str
    chapter: int
    verse: int
    mt_text: str | None
    readings: tuple[TargumSourceReading, ...]
    provenance: TargumProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "book": self.book,
            "book_id": self.book_id,
            "chapter": self.chapter,
            "verse": self.verse,
            "mt_text": self.mt_text,
            "readings": [_reading_to_dict(item) for item in self.readings],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class TargumConcordanceResult:
    lemma_key: str
    rows: tuple[TargumConcordanceRow, ...]
    total: int
    provenance: TargumProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "lemma_key": self.lemma_key,
            "rows": [_concordance_row_to_dict(item) for item in self.rows],
            "total": self.total,
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class TargumHebrewLemmaOptionsResult:
    initial: str
    targum: str
    candidates: tuple[TargumHebrewLemmaCandidate, ...]
    provenance: TargumProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "initial": self.initial,
            "targum": self.targum,
            "candidates": [_hebrew_candidate_to_dict(item) for item in self.candidates],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class TargumReflexResult:
    targum: str
    mt_lemma_id: str
    source_label: str
    mt_hebrew_lemma: str
    reflexes: tuple[TargumReflex, ...]
    provenance: TargumProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "targum": self.targum,
            "mt_lemma_id": self.mt_lemma_id,
            "source_label": self.source_label,
            "mt_hebrew_lemma": self.mt_hebrew_lemma,
            "reflexes": [_reflex_to_dict(item) for item in self.reflexes],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(slots=True)
class _ParallelBlock:
    label_parts: list[str] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    hrefs: list[str] = field(default_factory=list)
    div_depth: int = 1
    script_depth: int = 0
    anchor_depth: int = 0


_IGNORED_CONTENT_TAGS = frozenset({"script", "style"})


class _ParallelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[str] = []
        self.all_parts: list[str] = []
        self.blocks: list[_ParallelBlock] = []
        self._heading_parts: list[str] | None = None
        self._block: _ParallelBlock | None = None
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _IGNORED_CONTENT_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        attributes = dict(attrs)
        if tag == "h1":
            if self._heading_parts is not None:
                raise TargumParseError("CAL Targum page contains nested result headings")
            self._heading_parts = []
            return

        if tag == "div":
            classes = set((attributes.get("class") or "").split())
            if self._block is None and "targum-block" in classes:
                self._block = _ParallelBlock()
            elif self._block is not None:
                self._block.div_depth += 1
            return

        if self._block is None:
            return
        if tag == "a":
            href = attributes.get("href")
            if href is None or not href.strip():
                raise TargumParseError("CAL Targum source link has no target")
            self._block.hrefs.append(href)
            self._block.anchor_depth += 1
            return
        if tag == "span":
            classes = set((attributes.get("class") or "").split())
            if classes.intersection({"heb", "syr"}):
                self._block.script_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            if tag in _IGNORED_CONTENT_TAGS:
                self._ignored_depth -= 1
            return
        if tag == "h1" and self._heading_parts is not None:
            heading = _clean_text("".join(self._heading_parts))
            if heading:
                self.headings.append(heading)
            self._heading_parts = None
            return

        if self._block is None:
            return
        if tag == "a" and self._block.anchor_depth:
            self._block.anchor_depth -= 1
            return
        if tag == "span" and self._block.script_depth:
            self._block.script_depth -= 1
            return
        if tag == "div":
            self._block.div_depth -= 1
            if self._block.div_depth == 0:
                self.blocks.append(self._block)
                self._block = None

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self.all_parts.append(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._block is None:
            return
        if self._block.script_depth:
            self._block.text_parts.append(data)
        else:
            self._block.label_parts.append(data)

    def close(self) -> None:
        super().close()
        if self._ignored_depth:
            raise TargumParseError("CAL Targum page has an unclosed ignored content subtree")


@dataclass(slots=True)
class _TableCell:
    kind: str
    parts: list[str] = field(default_factory=list)
    hrefs: list[str] = field(default_factory=list)


class _SemanticTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[str] = []
        self.all_parts: list[str] = []
        self.rows: list[tuple[_TableCell, ...]] = []
        self.table_count = 0
        self._heading_parts: list[str] | None = None
        self._in_table = False
        self._row: list[_TableCell] | None = None
        self._cell: _TableCell | None = None
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _IGNORED_CONTENT_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        attributes = dict(attrs)
        if tag == "h1":
            if self._heading_parts is not None:
                raise TargumParseError("CAL Targum page contains nested result headings")
            self._heading_parts = []
            return
        if tag == "table":
            if self._in_table:
                raise TargumParseError("CAL Targum result contains nested tables")
            self.table_count += 1
            self._in_table = True
            return
        if not self._in_table:
            return
        if tag == "tr":
            if self._row is not None:
                raise TargumParseError("CAL Targum result contains nested table rows")
            self._row = []
            return
        if tag in {"th", "td"} and self._row is not None:
            if self._cell is not None:
                raise TargumParseError("CAL Targum result contains nested table cells")
            self._cell = _TableCell(kind=tag)
            return
        if tag == "a" and self._cell is not None:
            href = attributes.get("href")
            if href is None or not href.strip():
                raise TargumParseError("CAL Targum result link has no target")
            self._cell.hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            if tag in _IGNORED_CONTENT_TAGS:
                self._ignored_depth -= 1
            return
        if tag == "h1" and self._heading_parts is not None:
            heading = _clean_text("".join(self._heading_parts))
            if heading:
                self.headings.append(heading)
            self._heading_parts = None
            return
        if tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._row.append(self._cell)
            self._cell = None
            return
        if tag == "tr" and self._row is not None:
            if self._cell is not None:
                raise TargumParseError("CAL Targum result contains an incomplete table cell")
            self.rows.append(tuple(self._row))
            self._row = None
            return
        if tag == "table" and self._in_table:
            if self._row is not None or self._cell is not None:
                raise TargumParseError("CAL Targum result contains incomplete table markup")
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self.all_parts.append(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._cell is not None:
            self._cell.parts.append(data)

    def close(self) -> None:
        super().close()
        if self._ignored_depth:
            raise TargumParseError("CAL Targum result has an unclosed ignored content subtree")


@dataclass(slots=True)
class _OpenCandidate:
    mt_lemma_id: str
    parts: list[str] = field(default_factory=list)


class _HebrewLemmaChooserParser(HTMLParser):
    def __init__(self, source_url: str, expected_action: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.expected_action = expected_action
        self.all_parts: list[str] = []
        self.candidates: list[TargumHebrewLemmaCandidate] = []
        self.target_forms = 0
        self._in_target_form = False
        self._open_candidate: _OpenCandidate | None = None
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _IGNORED_CONTENT_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        attributes = dict(attrs)
        if tag == "form":
            if self._in_target_form:
                raise TargumParseError("CAL MT lemma chooser contains nested forms")
            action = attributes.get("action")
            method = (attributes.get("method") or "").lower()
            if (
                action
                and method == "post"
                and _is_same_origin_path(self.source_url, action, self.expected_action)
            ):
                self.target_forms += 1
                self._in_target_form = True
            return
        if tag != "input" or not self._in_target_form:
            return
        if (attributes.get("type") or "").lower() != "radio" or attributes.get("name") != "R1":
            return
        self._finish_candidate()
        value = attributes.get("value")
        if value is None:
            raise TargumParseError("CAL MT lemma choice has no opaque identifier")
        self._open_candidate = _OpenCandidate(mt_lemma_id=value)

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            if tag in _IGNORED_CONTENT_TAGS:
                self._ignored_depth -= 1
            return
        if tag == "form" and self._in_target_form:
            self._finish_candidate()
            self._in_target_form = False

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self.all_parts.append(data)
        if self._open_candidate is not None:
            self._open_candidate.parts.append(data)

    def close(self) -> None:
        super().close()
        if self._ignored_depth:
            raise TargumParseError("CAL MT lemma chooser has an unclosed ignored content subtree")
        if self._in_target_form:
            raise TargumParseError("CAL MT lemma chooser form is incomplete")

    def _finish_candidate(self) -> None:
        if self._open_candidate is None:
            return
        mt_lemma_id = _returned_mt_lemma_id(self._open_candidate.mt_lemma_id)
        label = _clean_text("".join(self._open_candidate.parts))
        if not label:
            raise TargumParseError("CAL MT lemma choice has no rendered label")
        label_parts = label.rsplit(" ", 1)
        if len(label_parts) != 2 or not label_parts[0] or not label_parts[1]:
            raise TargumParseError("CAL MT lemma choice lacks a displayed part of speech")
        self.candidates.append(
            TargumHebrewLemmaCandidate(
                mt_lemma_id=mt_lemma_id,
                label=label,
                pos=label_parts[1],
            )
        )
        self._open_candidate = None


_INITIALS = frozenset(
    {
        "alef",
        "bet",
        "gimel",
        "dalet",
        "heh",
        "waw",
        "zayin",
        "xet",
        "tet",
        "yod",
        "kaf",
        "lamed",
        "mem",
        "nun",
        "samekh",
        "ayin",
        "peh",
        "cade",
        "qof",
        "resh",
        "shin",
        "sin",
        "taw",
    }
)
_TARGUM_CONFIG = {
    "onqelos": {
        "chooser_dir": "Omtlemmas",
        "chooser_action": "getOmtlemma.php",
        "reflex_path": "getOmtlemma.php",
        "example_path": "getOMT.php",
        "heading_source": "Onkelos",
    },
    "neofiti": {
        "chooser_dir": "mtlemmas",
        "chooser_action": "getNmtlemma.php",
        "reflex_path": "getNmtlemma.php",
        "example_path": "getNMT.php",
        "heading_source": "Neofiti",
    },
}
_COORDINATE_ERROR_RE = re.compile(r"\berror\s+in\s+coordinate\b", re.I)
_TOTAL_RE = re.compile(r"\btotal\s+examples:\s*(\d+)\b", re.I)
_PARALLEL_HEADING_PREFIX = "MT and targums for "
_CONCORDANCE_HEADING_PREFIX = "CAL: Targum KWIC counts for "


def parse_targum_parallel_page(
    response: CalResponse,
    *,
    book: str,
    chapter: int,
    verse: int,
) -> TargumParallelPage:
    parser = _ParallelParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    if parser._block is not None or parser._heading_parts is not None:
        raise TargumParseError("CAL parallel Targum page contains incomplete semantic markup")

    expected_heading = f"{_PARALLEL_HEADING_PREFIX}{book} {chapter}:{verse}"
    headings = [
        heading for heading in parser.headings if heading.startswith(_PARALLEL_HEADING_PREFIX)
    ]
    if headings != [expected_heading]:
        raise TargumParseError("CAL parallel Targum heading does not match the requested verse")

    page_text = _clean_text(" ".join(parser.all_parts))
    coordinate_error = _COORDINATE_ERROR_RE.search(page_text) is not None
    if coordinate_error:
        if parser.blocks:
            raise TargumParseError("CAL parallel Targum page contradicts its coordinate error")
        return TargumParallelPage(
            status=TargumParallelStatus.NOT_FOUND,
            mt_text=None,
            readings=(),
        )

    if len(parser.blocks) < 2:
        raise TargumParseError("CAL parallel Targum page lacks MT/source comparison blocks")

    mt_block = parser.blocks[0]
    mt_label = _clean_text("".join(mt_block.label_parts))
    mt_text = _clean_text("".join(mt_block.text_parts))
    if mt_label or mt_block.hrefs or not mt_text:
        raise TargumParseError("CAL parallel Targum MT block has unexpected semantics")

    readings: list[TargumSourceReading] = []
    for block in parser.blocks[1:]:
        label = _clean_text("".join(block.label_parts))
        text = _clean_text("".join(block.text_parts))
        if not label or not text:
            raise TargumParseError("CAL parallel Targum source block lacks label or text")
        if len(block.hrefs) > 1:
            raise TargumParseError("CAL parallel Targum source block has ambiguous links")
        chapter_url = None
        if block.hrefs:
            chapter_url = _validated_same_origin_url(
                response.url,
                block.hrefs[0],
                expected_path="get_a_chapter.php",
                context="Targum source chapter",
            )
        readings.append(TargumSourceReading(label=label, text=text, chapter_url=chapter_url))

    return TargumParallelPage(
        status=TargumParallelStatus.FOUND,
        mt_text=mt_text,
        readings=tuple(readings),
    )


def parse_targum_concordance_page(
    response: CalResponse,
    *,
    lemma_key: str,
) -> TargumConcordancePage:
    parser = _SemanticTableParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    _require_complete_table_parser(parser)

    expected_heading = f"{_CONCORDANCE_HEADING_PREFIX}{lemma_key}"
    headings = [
        heading for heading in parser.headings if heading.startswith(_CONCORDANCE_HEADING_PREFIX)
    ]
    if headings != [expected_heading]:
        raise TargumParseError("CAL Targum concordance heading does not match the submitted lemma")
    if parser.table_count != 1:
        raise TargumParseError("CAL Targum concordance lacks one recognizable result table")

    current_section: str | None = None
    rows: list[TargumConcordanceRow] = []
    for cells in parser.rows:
        if _is_table_header(cells, "Targum", "Occurrences"):
            continue
        if len(cells) == 1 and cells[0].kind == "th":
            section = _cell_text(cells[0])
            if not section or cells[0].hrefs:
                raise TargumParseError("CAL Targum concordance has malformed section semantics")
            current_section = section
            continue
        if len(cells) != 2 or any(cell.kind != "td" for cell in cells):
            raise TargumParseError("CAL Targum concordance contains an unrecognized result row")
        label = _cell_text(cells[0])
        count_text = _cell_text(cells[1])
        if not label or not count_text.isdecimal() or len(cells[0].hrefs) != 1 or cells[1].hrefs:
            raise TargumParseError("CAL Targum concordance row lacks required semantics")
        example_url = _validated_concordance_url(response.url, cells[0].hrefs[0], lemma_key)
        rows.append(
            TargumConcordanceRow(
                section=current_section,
                label=label,
                count=int(count_text),
                example_url=example_url,
            )
        )

    page_text = _clean_text(" ".join(parser.all_parts))
    totals = _TOTAL_RE.findall(page_text)
    if len(totals) != 1 or not rows:
        raise TargumParseError("CAL Targum concordance lacks complete count/total semantics")
    total = int(totals[0])
    if sum(row.count for row in rows) != total:
        raise TargumParseError("CAL Targum concordance row counts contradict the reported total")
    return TargumConcordancePage(rows=tuple(rows), total=total)


def parse_hebrew_lemma_options_page(
    response: CalResponse,
    *,
    targum: str,
) -> TargumHebrewLemmaOptionsPage:
    config = _targum_config(targum)
    parser = _HebrewLemmaChooserParser(response.url, config["chooser_action"])
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()

    page_text = _clean_text(" ".join(parser.all_parts))
    if "CAL: MT lemma chooser" not in page_text:
        raise TargumParseError("CAL MT lemma chooser lacks its semantic page marker")
    if parser.target_forms != 1 or not parser.candidates:
        raise TargumParseError("CAL MT lemma chooser lacks one recognizable selection form")
    ids = [candidate.mt_lemma_id for candidate in parser.candidates]
    if len(ids) != len(set(ids)):
        raise TargumParseError("CAL MT lemma chooser repeats an opaque lemma identifier")
    return TargumHebrewLemmaOptionsPage(candidates=tuple(parser.candidates))


def parse_targum_reflex_page(
    response: CalResponse,
    *,
    targum: str,
    mt_lemma_id: str,
) -> TargumReflexPage:
    config = _targum_config(targum)
    parser = _SemanticTableParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    _require_complete_table_parser(parser)

    heading_prefix = f"{config['heading_source']} correspondences to "
    headings = [
        heading for heading in parser.headings if heading.startswith(heading_prefix.rstrip())
    ]
    if len(headings) != 1 or not headings[0].startswith(heading_prefix):
        raise TargumParseError("CAL Targum reflex page lacks a complete source/result heading")
    mt_hebrew_lemma = _clean_text(headings[0][len(heading_prefix) :])
    if not mt_hebrew_lemma:
        raise TargumParseError("CAL Targum reflex page has no selected MT Hebrew lemma")
    if parser.table_count != 1:
        raise TargumParseError("CAL Targum reflex page lacks one recognizable result table")

    reflexes: list[TargumReflex] = []
    for cells in parser.rows:
        if _is_table_header(cells, "CAL lemma", "frequency"):
            continue
        if len(cells) != 2 or any(cell.kind != "td" for cell in cells):
            raise TargumParseError("CAL Targum reflex page contains an unrecognized result row")
        label = _cell_text(cells[0])
        frequency_text = _cell_text(cells[1])
        if (
            not label
            or not frequency_text.isdecimal()
            or len(cells[0].hrefs) != 1
            or cells[1].hrefs
        ):
            raise TargumParseError("CAL Targum reflex row lacks required semantics")
        example_url, lemma_key = _validated_reflex_url(
            response.url,
            cells[0].hrefs[0],
            expected_path=config["example_path"],
            mt_lemma_id=mt_lemma_id,
        )
        reflexes.append(
            TargumReflex(
                lemma_key=lemma_key,
                label=label,
                frequency=int(frequency_text),
                example_url=example_url,
            )
        )
    if not reflexes:
        raise TargumParseError("CAL Targum reflex page has no recognized correspondences")
    return TargumReflexPage(
        source_label=config["heading_source"],
        mt_hebrew_lemma=mt_hebrew_lemma,
        reflexes=tuple(reflexes),
    )


class TargumService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def parallel(
        self,
        book: str,
        chapter: int,
        verse: int,
        *,
        include_peshitta: bool = False,
        include_samaritan: bool = False,
    ) -> TargumParallelResult:
        book_id = _validate_book(book)
        submitted_chapter = _validate_positive_int(chapter, "chapter")
        submitted_verse = _validate_positive_int(verse, "verse")
        if not isinstance(include_peshitta, bool) or not isinstance(include_samaritan, bool):
            raise ValueError("Targum optional-version flags must be booleans")

        data: list[tuple[str, str]] = [
            ("bookname", book_id),
            ("chapter", _format_coordinate_number(submitted_chapter)),
            ("verse", _format_coordinate_number(submitted_verse)),
        ]
        if include_peshitta:
            data.append(("Peshitta", "ON"))
        if include_samaritan:
            data.append(("Sam", "ON"))
        result = await self._client.fetch(
            CalRequest(method="POST", path="showtargum.php", data=tuple(data)),
            parser=lambda response: parse_targum_parallel_page(
                response,
                book=book,
                chapter=submitted_chapter,
                verse=submitted_verse,
            ),
            cache_namespace="targum-parallel-v1",
        )
        return TargumParallelResult(
            status=result.value.status,
            book=book,
            book_id=book_id,
            chapter=submitted_chapter,
            verse=submitted_verse,
            mt_text=result.value.mt_text,
            readings=result.value.readings,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="targum_parallel",
                book=book,
                book_id=book_id,
                chapter=submitted_chapter,
                verse=submitted_verse,
            ),
        )

    async def concordance(self, lemma_key: str) -> TargumConcordanceResult:
        lemma, pos, canonical_key = _validate_lemma_key(lemma_key)
        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path="showtargumKWIC.php",
                data=(("lemma", lemma), ("pos", pos)),
            ),
            parser=lambda response: parse_targum_concordance_page(
                response,
                lemma_key=canonical_key,
            ),
            cache_namespace="targum-concordance-v1",
        )
        return TargumConcordanceResult(
            lemma_key=canonical_key,
            rows=result.value.rows,
            total=result.value.total,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="targum_concordance",
                lemma_key=canonical_key,
            ),
        )

    async def hebrew_lemmas(
        self,
        initial: str,
        targum: str,
    ) -> TargumHebrewLemmaOptionsResult:
        submitted_initial = _validate_initial(initial)
        submitted_targum = _validate_targum(targum)
        config = _targum_config(submitted_targum)
        path = f"{config['chooser_dir']}/{submitted_initial}MTlemma.html"
        result = await self._client.fetch(
            CalRequest(method="GET", path=path),
            parser=lambda response: parse_hebrew_lemma_options_page(
                response,
                targum=submitted_targum,
            ),
            cache_namespace=f"targum-hebrew-lemmas-{submitted_targum}-v1",
        )
        return TargumHebrewLemmaOptionsResult(
            initial=submitted_initial,
            targum=submitted_targum,
            candidates=result.value.candidates,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="targum_hebrew_lemmas",
                targum=submitted_targum,
                initial=submitted_initial,
            ),
        )

    async def hebrew_reflexes(
        self,
        targum: str,
        mt_lemma_id: str,
    ) -> TargumReflexResult:
        submitted_targum = _validate_targum(targum)
        submitted_id = _validate_mt_lemma_id(mt_lemma_id)
        config = _targum_config(submitted_targum)
        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path=config["reflex_path"],
                data=(("R1", submitted_id),),
            ),
            parser=lambda response: parse_targum_reflex_page(
                response,
                targum=submitted_targum,
                mt_lemma_id=submitted_id,
            ),
            cache_namespace=f"targum-hebrew-reflexes-{submitted_targum}-v1",
        )
        return TargumReflexResult(
            targum=submitted_targum,
            mt_lemma_id=submitted_id,
            source_label=result.value.source_label,
            mt_hebrew_lemma=result.value.mt_hebrew_lemma,
            reflexes=result.value.reflexes,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="targum_hebrew_reflexes",
                targum=submitted_targum,
                mt_lemma_id=submitted_id,
            ),
        )


def _validate_book(book: str) -> str:
    return cal_biblical_book_id(book)


def _validate_positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 1 or value > 999:
        raise ValueError(f"{name} must be between 1 and 999")
    return value


def _format_coordinate_number(value: int) -> str:
    return f"{value:02d}" if value < 100 else str(value)


def _validate_initial(initial: str) -> str:
    if not isinstance(initial, str) or initial not in _INITIALS:
        raise ValueError("initial must be one current CAL MT lemma selector slug")
    return initial


def _validate_targum(targum: str) -> str:
    if not isinstance(targum, str) or targum not in _TARGUM_CONFIG:
        raise ValueError("targum must be 'onqelos' or 'neofiti'")
    return targum


def _validate_mt_lemma_id(mt_lemma_id: str) -> str:
    if not isinstance(mt_lemma_id, str):
        raise ValueError("mt_lemma_id must be a string")
    candidate = mt_lemma_id.strip(" ")
    if not candidate.isdecimal() or len(candidate) > 8 or int(candidate) < 1:
        raise ValueError("mt_lemma_id must be a positive decimal identifier of at most 8 digits")
    return candidate


def _returned_mt_lemma_id(value: str) -> str:
    candidate = value.strip(" ")
    if not candidate.isdecimal() or int(candidate) < 1:
        raise TargumParseError("CAL returned an invalid opaque MT lemma identifier")
    return candidate


def _targum_config(targum: str) -> dict[str, str]:
    config = _TARGUM_CONFIG.get(targum)
    if config is None:
        raise ValueError("targum must be 'onqelos' or 'neofiti'")
    return config


def _require_complete_table_parser(parser: _SemanticTableParser) -> None:
    if (
        parser._heading_parts is not None
        or parser._in_table
        or parser._row is not None
        or parser._cell is not None
    ):
        raise TargumParseError("CAL Targum result contains incomplete semantic markup")


def _cell_text(cell: _TableCell) -> str:
    return _clean_text("".join(cell.parts))


def _is_table_header(cells: tuple[_TableCell, ...], first: str, second: str) -> bool:
    return (
        len(cells) == 2
        and all(cell.kind == "th" for cell in cells)
        and _cell_text(cells[0]) == first
        and _cell_text(cells[1]) == second
        and not cells[0].hrefs
        and not cells[1].hrefs
    )


def _validated_concordance_url(source_url: str, href: str, lemma_key: str) -> str:
    resolved = _validated_same_origin_url(
        source_url,
        href,
        expected_path="show1dialectKWIC.php",
        context="Targum concordance example",
    )
    target = urlsplit(resolved)
    query = parse_qs(target.query, keep_blank_values=True)
    lemma = _single_query_value(query, "lemma", "Targum concordance example")
    pos = _single_query_value(query, "pos", "Targum concordance example")
    texts = _single_query_value(query, "texts", "Targum concordance example")
    if not texts.strip() or f"{lemma} {pos}" != lemma_key:
        raise TargumParseError("CAL Targum concordance example link contradicts its result row")
    return resolved


def _validated_reflex_url(
    source_url: str,
    href: str,
    *,
    expected_path: str,
    mt_lemma_id: str,
) -> tuple[str, str]:
    resolved = _validated_same_origin_url(
        source_url,
        href,
        expected_path=expected_path,
        context="Targum reflex example",
    )
    target = urlsplit(resolved)
    query = parse_qs(target.query, keep_blank_values=True)
    returned_mt_id = _single_query_value(query, "MT", "Targum reflex example")
    lemma_key = _single_query_value(query, "cal", "Targum reflex example")
    if returned_mt_id != mt_lemma_id:
        raise TargumParseError("CAL Targum reflex example link contradicts the selected MT lemma")
    _, _, canonical_key = _validate_lemma_key(lemma_key)
    if canonical_key != lemma_key:
        raise TargumParseError("CAL Targum reflex example link contains a noncanonical lemma key")
    return resolved, canonical_key


def _validated_same_origin_url(
    source_url: str,
    href: str,
    *,
    expected_path: str,
    context: str,
) -> str:
    resolved = urljoin(source_url, href)
    source = urlsplit(source_url)
    target = urlsplit(resolved)
    if (target.scheme, target.netloc) != (source.scheme, source.netloc):
        raise TargumParseError(f"CAL {context} link points outside the CAL origin")
    if target.path.rsplit("/", 1)[-1] != expected_path:
        raise TargumParseError(f"CAL {context} link targets an unexpected endpoint family")
    return resolved


def _is_same_origin_path(source_url: str, href: str, expected_path: str) -> bool:
    resolved = urljoin(source_url, href)
    source = urlsplit(source_url)
    target = urlsplit(resolved)
    return (target.scheme, target.netloc) == (source.scheme, source.netloc) and target.path.rsplit(
        "/", 1
    )[-1] == expected_path


def _single_query_value(query: dict[str, list[str]], key: str, context: str) -> str:
    values = query.get(key)
    if values is None or len(values) != 1 or not values[0]:
        raise TargumParseError(f"CAL {context} link has invalid {key} query semantics")
    return values[0]


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _make_provenance(
    source_url: str,
    retrieved_at: datetime,
    *,
    operation: str,
    book: str | None = None,
    book_id: str | None = None,
    chapter: int | None = None,
    verse: int | None = None,
    lemma_key: str | None = None,
    targum: str | None = None,
    initial: str | None = None,
    mt_lemma_id: str | None = None,
) -> TargumProvenance:
    return TargumProvenance(
        source="CAL",
        source_url=source_url,
        retrieved_at=retrieved_at,
        operation=operation,
        book=book,
        book_id=book_id,
        chapter=chapter,
        verse=verse,
        lemma_key=lemma_key,
        targum=targum,
        initial=initial,
        mt_lemma_id=mt_lemma_id,
    )


def _reading_to_dict(reading: TargumSourceReading) -> dict[str, object]:
    return {"label": reading.label, "text": reading.text, "chapter_url": reading.chapter_url}


def _concordance_row_to_dict(row: TargumConcordanceRow) -> dict[str, object]:
    return {
        "section": row.section,
        "label": row.label,
        "count": row.count,
        "example_url": row.example_url,
    }


def _hebrew_candidate_to_dict(candidate: TargumHebrewLemmaCandidate) -> dict[str, object]:
    return {
        "mt_lemma_id": candidate.mt_lemma_id,
        "label": candidate.label,
        "pos": candidate.pos,
    }


def _reflex_to_dict(reflex: TargumReflex) -> dict[str, object]:
    return {
        "lemma_key": reflex.lemma_key,
        "label": reflex.label,
        "frequency": reflex.frequency,
        "example_url": reflex.example_url,
    }


def _provenance_to_dict(provenance: TargumProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "operation": provenance.operation,
        "book": provenance.book,
        "book_id": provenance.book_id,
        "chapter": provenance.chapter,
        "verse": provenance.verse,
        "lemma_key": provenance.lemma_key,
        "targum": provenance.targum,
        "initial": provenance.initial,
        "mt_lemma_id": provenance.mt_lemma_id,
    }
