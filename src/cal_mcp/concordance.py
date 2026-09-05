from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import _parse_lines
from cal_mcp.normalization import InputRepresentation, normalize_query

_ID_RE = re.compile(r"^[0-9]+$")
_SUFFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]{0,7}$")
_FREQUENCY_MARKER_RE = re.compile(r"^Frequencies of lemmas in text ([0-9]+)$", re.IGNORECASE)
_FREQUENCY_RE = re.compile(r"^([0-9]+)\s*:")
_TOTAL_RE = re.compile(r"^total examples:\s*([0-9]+)$", re.IGNORECASE)
_DIALECT_TOTAL_RE = re.compile(
    r"^([0-9]+)\s+examples?\s+found for\s+(.+?)\s+in dialect\s+([0-9]+)$",
    re.IGNORECASE,
)
_EMPTY_SCOPE_RE = re.compile(r"^no examples found in ([0-9]+)$", re.IGNORECASE)

_TEXT_SCRIPTS = {"transliteration": "R", "semitic": "S"}
_KWIC_SCRIPTS = {"roman": "R", "hebrew": "H", "syriac": "S"}
_KWIC_CHARSETS = frozenset({"R", "H", "S"})
_MAX_TEXT_IDS = 8


class ConcordanceParseError(CalContentError):
    """Raised when a CAL concordance page no longer exposes required semantics."""


class KwicScopeKind(StrEnum):
    TEXTS = "texts"
    DIALECT = "dialect"


@dataclass(frozen=True, slots=True)
class ConcordanceLemma:
    frequency: int
    lemma_key: str
    gloss: str
    kwic_url: str


@dataclass(frozen=True, slots=True)
class TextConcordancePage:
    lemmas: tuple[ConcordanceLemma, ...]


@dataclass(frozen=True, slots=True)
class KwicDialectRef:
    dialect_id: str
    label: str


@dataclass(frozen=True, slots=True)
class KwicDialectOptionsPage:
    dialects: tuple[KwicDialectRef, ...]


@dataclass(frozen=True, slots=True)
class KwicHit:
    file_id: str
    subtext_id: str | None
    target_coordinate: str
    context: str
    full_context_url: str
    charset: str


@dataclass(frozen=True, slots=True)
class KwicPage:
    total: int
    hits: tuple[KwicHit, ...]
    empty_scope_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConcordanceProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    lemma_key: str | None = None
    text_id: str | None = None
    scope_ids: tuple[str, ...] = ()
    script: str | None = None


@dataclass(frozen=True, slots=True)
class TextConcordanceResult:
    text_id: str
    script: str
    lemmas: tuple[ConcordanceLemma, ...]
    provenance: ConcordanceProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "text_id": self.text_id,
            "script": self.script,
            "lemmas": [_concordance_lemma_to_dict(item) for item in self.lemmas],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class KwicDialectOptionsResult:
    lemma_key: str
    dialects: tuple[KwicDialectRef, ...]
    provenance: ConcordanceProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "lemma_key": self.lemma_key,
            "dialects": [_dialect_to_dict(item) for item in self.dialects],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class KwicResult:
    lemma_key: str
    scope_kind: KwicScopeKind
    scope_ids: tuple[str, ...]
    total: int
    hits: tuple[KwicHit, ...]
    empty_scope_ids: tuple[str, ...]
    provenance: ConcordanceProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "lemma_key": self.lemma_key,
            "scope_kind": self.scope_kind.value,
            "scope_ids": list(self.scope_ids),
            "total": self.total,
            "hits": [_hit_to_dict(item) for item in self.hits],
            "empty_scope_ids": list(self.empty_scope_ids),
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class _TableLink:
    href: str
    text: str


@dataclass(frozen=True, slots=True)
class _TableCell:
    text: str
    links: tuple[_TableLink, ...]


@dataclass(frozen=True, slots=True)
class _TableRow:
    cells: tuple[_TableCell, ...]

    @property
    def text(self) -> str:
        return _clean_text(" ".join(cell.text for cell in self.cells))


@dataclass(slots=True)
class _OpenTableLink:
    href: str
    parts: list[str] = field(default_factory=list)


class _TableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[_TableRow] = []
        self._row: list[_TableCell] | None = None
        self._cell_parts: list[str] | None = None
        self._cell_links: list[_TableLink] = []
        self._open_link: _OpenTableLink | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
            return
        if tag in {"td", "th"} and self._row is not None:
            self._cell_parts = []
            self._cell_links = []
            return
        if tag == "a" and self._cell_parts is not None:
            href = next((value for key, value in attrs if key == "href" and value), "")
            self._open_link = _OpenTableLink(href=href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._open_link is not None:
            self._cell_links.append(
                _TableLink(
                    href=self._open_link.href,
                    text=_clean_text("".join(self._open_link.parts)),
                )
            )
            self._open_link = None
            return
        if tag in {"td", "th"} and self._row is not None and self._cell_parts is not None:
            self._row.append(
                _TableCell(
                    text=_clean_text("".join(self._cell_parts)),
                    links=tuple(self._cell_links),
                )
            )
            self._cell_parts = None
            self._cell_links = []
            return
        if tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(_TableRow(cells=tuple(self._row)))
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)
        if self._open_link is not None:
            self._open_link.parts.append(data)


@dataclass(slots=True)
class _DialectOptionBuilder:
    value: str
    parts: list[str] = field(default_factory=list)


class _DialectSelectorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.target_forms = 0
        self.inputs: dict[str, list[str]] = {}
        self.options: list[KwicDialectRef] = []
        self._in_target_form = False
        self._in_texts_select = False
        self._option: _DialectOptionBuilder | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "form":
            action = attr_map.get("action", "") or ""
            self._in_target_form = _is_path(action, "show1dialectKWIC.php")
            if self._in_target_form:
                self.target_forms += 1
            return
        if not self._in_target_form:
            return
        if tag == "input":
            name = attr_map.get("name")
            if name:
                self.inputs.setdefault(name, []).append(attr_map.get("value", "") or "")
            return
        if tag == "select":
            self._in_texts_select = attr_map.get("name") == "texts"
            return
        if tag == "option" and self._in_texts_select:
            self._option = _DialectOptionBuilder(value=attr_map.get("value", "") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self._option is not None:
            self.options.append(
                KwicDialectRef(
                    dialect_id=self._option.value,
                    label=_clean_text("".join(self._option.parts)),
                )
            )
            self._option = None
            return
        if tag == "select":
            self._in_texts_select = False
            return
        if tag == "form" and self._in_target_form:
            self._in_target_form = False

    def handle_data(self, data: str) -> None:
        if self._option is not None:
            self._option.parts.append(data)


def parse_text_concordance_page(
    response: CalResponse,
    *,
    requested_text_id: str,
    requested_charset: str,
) -> TextConcordancePage:
    lines = _parse_lines(response)
    markers = [
        match for line in lines if (match := _FREQUENCY_MARKER_RE.fullmatch(line.text)) is not None
    ]
    if len(markers) != 1 or markers[0].group(1) != requested_text_id:
        raise ConcordanceParseError("CAL text concordance marker does not match the request")

    parser = _TableHTMLParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    lemmas: list[ConcordanceLemma] = []
    for row in parser.rows:
        links = [
            (cell_index, link)
            for cell_index, cell in enumerate(row.cells)
            for link in cell.links
            if _is_path(link.href, "showKWIC.php")
        ]
        if not links:
            continue
        if len(links) != 1:
            raise ConcordanceParseError("CAL concordance row has multiple KWIC links")
        cell_index, link = links[0]
        if cell_index == 0 or cell_index + 1 >= len(row.cells):
            raise ConcordanceParseError("CAL concordance row is missing frequency or gloss")

        kwic_url = _cal_navigation_url(response.url, link.href, "showKWIC.php")
        query = parse_qs(urlsplit(kwic_url).query, keep_blank_values=True)
        lemma_key = _parse_returned_lemma_key(_single_query_value(query, "lemma", "KWIC lemma"))
        text_id = _single_query_value(query, "texts", "KWIC text")
        charset = _single_query_value(query, "charset", "KWIC charset")
        if text_id != requested_text_id or charset != requested_charset:
            raise ConcordanceParseError("CAL concordance row link contradicts the request")
        if link.text != lemma_key:
            raise ConcordanceParseError("CAL concordance lemma link text differs from its key")

        frequency_match = _FREQUENCY_RE.match(row.cells[cell_index - 1].text)
        gloss = row.cells[cell_index + 1].text.removeprefix(":").strip()
        if frequency_match is None or not gloss:
            raise ConcordanceParseError("CAL concordance row lacks frequency or gloss")
        lemmas.append(
            ConcordanceLemma(
                frequency=int(frequency_match.group(1)),
                lemma_key=lemma_key,
                gloss=gloss,
                kwic_url=kwic_url,
            )
        )

    if not lemmas:
        raise ConcordanceParseError("CAL text concordance contains no recognizable lemma rows")
    return TextConcordancePage(lemmas=tuple(lemmas))


def parse_kwic_dialect_options(
    response: CalResponse,
    *,
    lemma_key: str,
) -> KwicDialectOptionsPage:
    lemma, suffix, canonical_key = _validate_lemma_key(lemma_key)
    parser = _DialectSelectorParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    if parser.target_forms != 1:
        raise ConcordanceParseError("CAL KWIC dialect selector lacks one unique target form")
    if _single_form_value(parser.inputs, "lemma") != lemma:
        raise ConcordanceParseError("CAL dialect selector lemma differs from the request")
    if _single_form_value(parser.inputs, "pos") != suffix:
        raise ConcordanceParseError("CAL dialect selector POS differs from the request")

    seen: set[str] = set()
    dialects: list[KwicDialectRef] = []
    for option in parser.options:
        dialect_id = _parse_decimal_id(option.dialect_id, "dialect_id")
        if not option.label:
            raise ConcordanceParseError("CAL dialect selector option has no label")
        if dialect_id in seen:
            raise ConcordanceParseError("CAL dialect selector repeats a dialect identifier")
        seen.add(dialect_id)
        dialects.append(KwicDialectRef(dialect_id=dialect_id, label=option.label))
    if not dialects:
        raise ConcordanceParseError("CAL dialect selector contains no dialect options")

    del canonical_key
    return KwicDialectOptionsPage(dialects=tuple(dialects))


def parse_kwic_result(
    response: CalResponse,
    *,
    lemma_key: str,
    scope_kind: KwicScopeKind,
    scope_ids: tuple[str, ...],
) -> KwicPage:
    _, _, canonical_key = _validate_lemma_key(lemma_key)
    if not scope_ids:
        raise ConcordanceParseError("KWIC parser requires at least one requested scope")
    lines = _parse_lines(response)
    expected_heading = _expected_kwic_heading(canonical_key, scope_kind, scope_ids)
    if sum(line.text == expected_heading for line in lines) != 1:
        raise ConcordanceParseError("CAL KWIC heading does not match the requested scope")

    total = _parse_kwic_total(lines, canonical_key, scope_kind, scope_ids)
    empty_scope_ids = _parse_empty_scopes(lines, scope_ids)
    hits = _parse_kwic_hits(response)
    if total != len(hits):
        raise ConcordanceParseError("CAL KWIC total does not match parsed target hits")
    if total == 0 and not empty_scope_ids:
        raise ConcordanceParseError("CAL zero-hit KWIC lacks an explicit no-examples marker")

    if scope_kind is KwicScopeKind.TEXTS:
        hit_files = {hit.file_id for hit in hits}
        requested = set(scope_ids)
        if not hit_files.issubset(requested):
            raise ConcordanceParseError("CAL text-scoped KWIC returned an unrequested text")
        if hit_files.intersection(empty_scope_ids):
            raise ConcordanceParseError("CAL KWIC marks a text both empty and non-empty")
        if hit_files.union(empty_scope_ids) != requested:
            raise ConcordanceParseError("CAL KWIC omits a requested text scope")
    elif len(scope_ids) != 1:
        raise ConcordanceParseError("CAL dialect KWIC must have exactly one requested dialect")

    return KwicPage(total=total, hits=hits, empty_scope_ids=empty_scope_ids)


class ConcordanceService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def text_concordance(
        self,
        text_id: str,
        *,
        script: str = "semitic",
    ) -> TextConcordanceResult:
        normalized_text_id = _validate_decimal_id(text_id, "text_id")
        charset = _script_charset(script, _TEXT_SCRIPTS, "text concordance")

        def parse_requested(response: CalResponse) -> TextConcordancePage:
            return parse_text_concordance_page(
                response,
                requested_text_id=normalized_text_id,
                requested_charset=charset,
            )

        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="newconcord.php",
                params=(("text", normalized_text_id), ("cset", charset)),
            ),
            parser=parse_requested,
            cache_namespace="text-concordance-v1",
        )
        provenance = ConcordanceProvenance(
            source="CAL",
            source_url=result.source_url,
            retrieved_at=result.retrieved_at,
            operation="text_concordance",
            text_id=normalized_text_id,
            scope_ids=(normalized_text_id,),
            script=script,
        )
        return TextConcordanceResult(
            text_id=normalized_text_id,
            script=script,
            lemmas=result.value.lemmas,
            provenance=provenance,
        )

    async def kwic_texts(
        self,
        lemma_key: str,
        text_ids: Sequence[str],
        *,
        script: str = "roman",
    ) -> KwicResult:
        lemma, suffix, canonical_key = _validate_lemma_key(lemma_key)
        normalized_ids = _validate_text_ids(text_ids)
        charset = _script_charset(script, _KWIC_SCRIPTS, "KWIC")

        def parse_requested(response: CalResponse) -> KwicPage:
            return parse_kwic_result(
                response,
                lemma_key=canonical_key,
                scope_kind=KwicScopeKind.TEXTS,
                scope_ids=normalized_ids,
            )

        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path="showdialectKWIC.php",
                data=(
                    ("lemma", lemma),
                    ("pos", suffix),
                    ("texts", " ".join(normalized_ids)),
                    ("charset", charset),
                ),
            ),
            parser=parse_requested,
            cache_namespace="kwic-texts-v1",
        )
        provenance = ConcordanceProvenance(
            source="CAL",
            source_url=result.source_url,
            retrieved_at=result.retrieved_at,
            operation="kwic_texts",
            lemma_key=canonical_key,
            scope_ids=normalized_ids,
            script=script,
        )
        return _kwic_result(canonical_key, KwicScopeKind.TEXTS, result.value, provenance)

    async def kwic_dialects(self, lemma_key: str) -> KwicDialectOptionsResult:
        _, _, canonical_key = _validate_lemma_key(lemma_key)

        def parse_requested(response: CalResponse) -> KwicDialectOptionsPage:
            return parse_kwic_dialect_options(response, lemma_key=canonical_key)

        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="dKWIC.php",
                params=(("lemma", canonical_key),),
            ),
            parser=parse_requested,
            cache_namespace="kwic-dialects-v1",
        )
        return KwicDialectOptionsResult(
            lemma_key=canonical_key,
            dialects=result.value.dialects,
            provenance=ConcordanceProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="kwic_dialects",
                lemma_key=canonical_key,
            ),
        )

    async def kwic_dialect(self, lemma_key: str, dialect_id: str) -> KwicResult:
        lemma, suffix, canonical_key = _validate_lemma_key(lemma_key)
        normalized_dialect = _validate_decimal_id(dialect_id, "dialect_id")

        def parse_requested(response: CalResponse) -> KwicPage:
            return parse_kwic_result(
                response,
                lemma_key=canonical_key,
                scope_kind=KwicScopeKind.DIALECT,
                scope_ids=(normalized_dialect,),
            )

        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="show1dialectKWIC.php",
                params=(
                    ("lemma", lemma),
                    ("pos", suffix),
                    ("texts", normalized_dialect),
                ),
            ),
            parser=parse_requested,
            cache_namespace="kwic-dialect-v1",
        )
        provenance = ConcordanceProvenance(
            source="CAL",
            source_url=result.source_url,
            retrieved_at=result.retrieved_at,
            operation="kwic_dialect",
            lemma_key=canonical_key,
            scope_ids=(normalized_dialect,),
        )
        return _kwic_result(canonical_key, KwicScopeKind.DIALECT, result.value, provenance)


def _parse_kwic_hits(response: CalResponse) -> tuple[KwicHit, ...]:
    parser = _TableHTMLParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    hits: list[KwicHit] = []
    for row in parser.rows:
        links = [
            link
            for cell in row.cells
            for link in cell.links
            if _is_path(link.href, "get_a_kwicchapter.php")
        ]
        if not links:
            continue
        if len(links) != 1:
            raise ConcordanceParseError("CAL KWIC target row has multiple full-context links")
        link = links[0]
        full_context_url = _cal_navigation_url(
            response.url,
            link.href,
            "get_a_kwicchapter.php",
        )
        query = parse_qs(urlsplit(full_context_url).query, keep_blank_values=True)
        file_id = _parse_decimal_id(
            _single_query_value(query, "file", "KWIC file"),
            "file_id",
        )
        target = _parse_decimal_id(
            _single_query_value(query, "target", "KWIC target"),
            "target_coordinate",
        )
        charset = _single_query_value(query, "cset", "KWIC charset")
        if charset not in _KWIC_CHARSETS:
            raise ConcordanceParseError("CAL KWIC target link has an unknown charset")
        subtext_id = _optional_decimal_query_value(query, "sub", "subtext_id")
        if link.text != target:
            raise ConcordanceParseError("CAL KWIC target link text differs from its coordinate")

        context_parts = [
            cell.text
            for cell in row.cells
            if not any(candidate is link for candidate in cell.links) and cell.text
        ]
        if not context_parts:
            raise ConcordanceParseError("CAL KWIC target row has no rendered context")
        hits.append(
            KwicHit(
                file_id=file_id,
                subtext_id=subtext_id,
                target_coordinate=target,
                context=_clean_text(" ".join(context_parts)),
                full_context_url=full_context_url,
                charset=charset,
            )
        )
    return tuple(hits)


def _parse_kwic_total(
    lines: Sequence[object],
    lemma_key: str,
    scope_kind: KwicScopeKind,
    scope_ids: tuple[str, ...],
) -> int:
    texts = [getattr(line, "text", "") for line in lines]
    total_matches = [match for text in texts if (match := _TOTAL_RE.fullmatch(text)) is not None]
    dialect_matches = [
        match for text in texts if (match := _DIALECT_TOTAL_RE.fullmatch(text)) is not None
    ]

    if scope_kind is KwicScopeKind.TEXTS:
        if len(total_matches) != 1 or dialect_matches:
            raise ConcordanceParseError("CAL text-scoped KWIC lacks one unique total")
        return int(total_matches[0].group(1))

    if len(scope_ids) != 1:
        raise ConcordanceParseError("CAL dialect KWIC requires one dialect scope")
    if len(dialect_matches) == 1 and not total_matches:
        match = dialect_matches[0]
        if match.group(2) != lemma_key or match.group(3) != scope_ids[0]:
            raise ConcordanceParseError("CAL dialect KWIC total contradicts the request")
        return int(match.group(1))
    if len(total_matches) == 1 and not dialect_matches:
        return int(total_matches[0].group(1))
    raise ConcordanceParseError("CAL dialect KWIC lacks one unique total")


def _parse_empty_scopes(lines: Sequence[object], scope_ids: tuple[str, ...]) -> tuple[str, ...]:
    requested = set(scope_ids)
    empty: list[str] = []
    for line in lines:
        text = getattr(line, "text", "")
        match = _EMPTY_SCOPE_RE.fullmatch(text)
        if match is None:
            continue
        scope_id = match.group(1)
        if scope_id not in requested:
            raise ConcordanceParseError("CAL KWIC marks an unrequested scope as empty")
        if scope_id in empty:
            raise ConcordanceParseError("CAL KWIC repeats an empty-scope marker")
        empty.append(scope_id)
    return tuple(empty)


def _expected_kwic_heading(
    lemma_key: str,
    scope_kind: KwicScopeKind,
    scope_ids: tuple[str, ...],
) -> str:
    if scope_kind is KwicScopeKind.TEXTS:
        return f"Looking for {lemma_key} in dialect {' '.join(scope_ids)}"
    if len(scope_ids) != 1:
        raise ConcordanceParseError("CAL dialect KWIC requires one dialect scope")
    return f"Looking for {lemma_key} in {scope_ids[0]}"


def _validate_lemma_key(value: str) -> tuple[str, str, str]:
    if not isinstance(value, str):
        raise ValueError("lemma_key must be a string")
    candidate = value.strip(" ")
    if any(char.isspace() and char != " " for char in candidate):
        raise ValueError("lemma_key may contain only ASCII spaces")
    if candidate.count(" ") != 1:
        raise ValueError("lemma_key must contain one CAL lemma and one key suffix")
    lemma, suffix = candidate.rsplit(" ", 1)
    if not lemma or " " in lemma or _SUFFIX_RE.fullmatch(suffix) is None:
        raise ValueError("lemma_key has an invalid CAL lemma/key-suffix structure")

    base_lemma = lemma
    if "#" in lemma:
        base_lemma, homograph = lemma.rsplit("#", 1)
        if (
            not base_lemma
            or "#" in base_lemma
            or not homograph.isascii()
            or not homograph.isdecimal()
            or homograph.startswith("0")
        ):
            raise ValueError("lemma_key has an invalid CAL homograph suffix")
    normalize_query(base_lemma, representation=InputRepresentation.CAL_CODE)
    return lemma, suffix, f"{lemma} {suffix}"


def _parse_returned_lemma_key(value: str) -> str:
    try:
        _, _, canonical_key = _validate_lemma_key(value)
    except ValueError as exc:
        raise ConcordanceParseError("CAL concordance row contains an invalid lemma key") from exc
    if canonical_key != value:
        raise ConcordanceParseError("CAL concordance row lemma key is not canonical")
    return canonical_key


def _cal_navigation_url(source_url: str, href: str, filename: str) -> str:
    resolved = urljoin(source_url, href)
    source = urlsplit(source_url)
    target = urlsplit(resolved)
    if (target.scheme, target.netloc) != (source.scheme, source.netloc):
        raise ConcordanceParseError("CAL navigation link points outside the CAL origin")
    if not target.path.endswith(filename):
        raise ConcordanceParseError("CAL navigation link has an unexpected target path")
    return resolved


def _validate_decimal_id(value: str, name: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a CAL decimal identifier")
    return value


def _parse_decimal_id(value: str, name: str) -> str:
    if _ID_RE.fullmatch(value) is None:
        raise ConcordanceParseError(f"CAL returned a non-decimal {name}")
    return value


def _validate_text_ids(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("text_ids must be a sequence of CAL decimal identifiers")
    normalized = tuple(_validate_decimal_id(value, "text_id") for value in values)
    if not 1 <= len(normalized) <= _MAX_TEXT_IDS:
        raise ValueError(f"text_ids must contain between 1 and {_MAX_TEXT_IDS} identifiers")
    if len(set(normalized)) != len(normalized):
        raise ValueError("text_ids must not contain duplicates")
    return normalized


def _script_charset(script: str, mapping: dict[str, str], operation: str) -> str:
    if not isinstance(script, str) or script not in mapping:
        choices = ", ".join(sorted(mapping))
        raise ValueError(f"{operation} script must be one of: {choices}")
    return mapping[script]


def _single_query_value(
    query: dict[str, list[str]],
    key: str,
    label: str,
) -> str:
    values = query.get(key)
    if values is None or len(values) != 1 or not values[0]:
        raise ConcordanceParseError(f"CAL {label} parameter is missing or repeated")
    return values[0]


def _optional_decimal_query_value(
    query: dict[str, list[str]],
    key: str,
    name: str,
) -> str | None:
    values = query.get(key)
    if values is None:
        return None
    if len(values) != 1:
        raise ConcordanceParseError(f"CAL returned repeated {name} parameters")
    if not values[0]:
        return None
    return _parse_decimal_id(values[0], name)


def _single_form_value(inputs: dict[str, list[str]], name: str) -> str:
    values = inputs.get(name)
    if values is None or len(values) != 1 or not values[0]:
        raise ConcordanceParseError(f"CAL dialect selector lacks one {name} value")
    return values[0]


def _is_path(href: str, filename: str) -> bool:
    return urlsplit(href).path.endswith(filename)


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _kwic_result(
    lemma_key: str,
    scope_kind: KwicScopeKind,
    page: KwicPage,
    provenance: ConcordanceProvenance,
) -> KwicResult:
    return KwicResult(
        lemma_key=lemma_key,
        scope_kind=scope_kind,
        scope_ids=provenance.scope_ids,
        total=page.total,
        hits=page.hits,
        empty_scope_ids=page.empty_scope_ids,
        provenance=provenance,
    )


def _concordance_lemma_to_dict(item: ConcordanceLemma) -> dict[str, object]:
    return {
        "frequency": item.frequency,
        "lemma_key": item.lemma_key,
        "gloss": item.gloss,
        "kwic_url": item.kwic_url,
    }


def _dialect_to_dict(item: KwicDialectRef) -> dict[str, object]:
    return {"dialect_id": item.dialect_id, "label": item.label}


def _hit_to_dict(item: KwicHit) -> dict[str, object]:
    return {
        "file_id": item.file_id,
        "subtext_id": item.subtext_id,
        "target_coordinate": item.target_coordinate,
        "context": item.context,
        "full_context_url": item.full_context_url,
        "charset": item.charset,
    }


def _provenance_to_dict(item: ConcordanceProvenance) -> dict[str, object]:
    return {
        "source": item.source,
        "source_url": item.source_url,
        "retrieved_at": item.retrieved_at.isoformat(),
        "operation": item.operation,
        "lemma_key": item.lemma_key,
        "text_id": item.text_id,
        "scope_ids": list(item.scope_ids),
        "script": item.script,
    }


__all__ = [
    "ConcordanceLemma",
    "ConcordanceParseError",
    "ConcordanceProvenance",
    "ConcordanceService",
    "KwicDialectOptionsPage",
    "KwicDialectOptionsResult",
    "KwicDialectRef",
    "KwicHit",
    "KwicPage",
    "KwicResult",
    "KwicScopeKind",
    "TextConcordancePage",
    "TextConcordanceResult",
    "parse_kwic_dialect_options",
    "parse_kwic_result",
    "parse_text_concordance_page",
]
