from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalInputError
from cal_mcp.lexicon import (
    _NOT_FOUND_PHRASES,
    LemmaRef,
    LexiconParseError,
    _is_lemma_entry_href,
    _lemma_key_from_href,
    _lemma_to_dict,
    _parse_lemma_header,
    _parse_lines,
)
from cal_mcp.normalization import (
    AmbiguousQueryError,
    CalCodeConversion,
    InputRepresentation,
    UnsupportedQueryError,
    convert_to_cal_code,
)

_BROWSE_PATH = "browseSKEYheaders.php"
_CAL_ORIGIN = ("https", "cal.huc.edu")
_CAL_CONSONANTS = frozenset(")bgdhwzxTyklmns(pPcqr$&t")
_ALLOWED_REPRESENTATIONS = frozenset(
    {
        InputRepresentation.CAL_CODE,
        InputRepresentation.ROMAN_SHARED,
        InputRepresentation.UNICODE_TRANSLITERATION,
        InputRepresentation.HEBREW,
        InputRepresentation.SYRIAC,
    }
)
_CONTINUATION_MAX_LENGTH = 128
_CONTINUATION_FORBIDDEN = frozenset("&=?#/\\:")


class LexiconBrowseRowKind(StrEnum):
    ENTRY = "entry"
    CROSS_REFERENCE = "cross_reference"


@dataclass(frozen=True, slots=True)
class LexiconBrowseRow:
    kind: LexiconBrowseRowKind
    lemma: LemmaRef | None = None
    source_text: str | None = None
    target_lemma_key: str | None = None
    target_label: str | None = None


@dataclass(frozen=True, slots=True)
class LexiconBrowsePage:
    rows: tuple[LexiconBrowseRow, ...]
    entries: tuple[LemmaRef, ...]
    next_continuation: str | None = None


@dataclass(frozen=True, slots=True)
class LexiconBrowseProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    original_prefix: str
    normalized_prefix: str
    representation: str
    conversion_strategy: str
    continuation: str | None = None


@dataclass(frozen=True, slots=True)
class LexiconBrowseResult:
    prefix: str
    normalized_prefix: str
    rows: tuple[LexiconBrowseRow, ...]
    entries: tuple[LemmaRef, ...]
    next_continuation: str | None
    provenance: LexiconBrowseProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "prefix": self.prefix,
            "normalized_prefix": self.normalized_prefix,
            "rows": [_browse_row_to_dict(item) for item in self.rows],
            "entries": [_lemma_to_dict(item) for item in self.entries],
            "next_continuation": self.next_continuation,
            "provenance": _provenance_to_dict(self.provenance),
        }


def parse_lexicon_browse_page(response: CalResponse) -> LexiconBrowsePage:
    lines = _parse_lines(response)
    rows: list[LexiconBrowseRow] = []
    entries: list[LemmaRef] = []

    for index, line in enumerate(lines):
        lemma_links = tuple(link for link in line.links if _is_lemma_entry_href(link.href))
        arrow_count = line.text.count("→")

        if arrow_count:
            if arrow_count != 1:
                raise LexiconParseError(
                    "CAL lexicon browse cross-reference has multiple arrows"
                )
            if len(lemma_links) != 1 or len(line.links) != 1:
                raise LexiconParseError(
                    "CAL lexicon browse cross-reference must have one target link"
                )

            arrow_index = line.text.index("→")
            source_text = line.text[:arrow_index].strip()
            if not source_text:
                raise LexiconParseError(
                    "CAL lexicon browse cross-reference has an empty source"
                )

            target = lemma_links[0]
            target_key = _lemma_key_from_href(target.href)
            if target_key is None:
                raise LexiconParseError(
                    "CAL lexicon browse cross-reference target lacks a lemma key"
                )
            target_label = target.text.strip()
            if not target_label:
                raise LexiconParseError(
                    "CAL lexicon browse cross-reference target has an empty label"
                )

            target_index = line.text.find(target_label, arrow_index + 1)
            if target_index < 0:
                raise LexiconParseError(
                    "CAL lexicon browse cross-reference target label is not rendered "
                    "after the arrow"
                )
            between = line.text[arrow_index + 1 : target_index].strip()
            trailing = line.text[target_index + len(target_label) :].strip()
            if between or trailing:
                raise LexiconParseError(
                    "CAL lexicon browse cross-reference has unrelated rendered text"
                )

            rows.append(
                LexiconBrowseRow(
                    kind=LexiconBrowseRowKind.CROSS_REFERENCE,
                    source_text=source_text,
                    target_lemma_key=target_key,
                    target_label=target_label,
                )
            )
            continue

        if not lemma_links:
            continue
        if len(lemma_links) != 1:
            raise LexiconParseError(
                "CAL lexicon browse entry row has multiple lemma links"
            )

        link = lemma_links[0]
        lemma_key = _lemma_key_from_href(link.href)
        if lemma_key is None:
            raise LexiconParseError(
                "CAL lexicon browse candidate is missing a usable lemma key"
            )
        parsed = _parse_lemma_header(link.text, lemma_key=lemma_key, require_gloss=False)
        if parsed is None:
            raise LexiconParseError(
                "CAL lexicon browse candidate is missing a recognizable lemma header"
            )

        gloss = parsed.gloss
        for next_line in lines[index + 1 :]:
            if "→" in next_line.text or any(
                _is_lemma_entry_href(item.href) for item in next_line.links
            ):
                break
            if next_line.text:
                gloss = next_line.text
                break

        lemma = LemmaRef(
            lemma_key=parsed.lemma_key,
            headwords=parsed.headwords,
            pronunciation=parsed.pronunciation,
            part_of_speech=parsed.part_of_speech,
            gloss=gloss,
            aliases=(),
        )
        rows.append(LexiconBrowseRow(kind=LexiconBrowseRowKind.ENTRY, lemma=lemma))
        entries.append(lemma)

    if not rows:
        page_text = " ".join(line.text.lower() for line in lines)
        if not any(phrase in page_text for phrase in _NOT_FOUND_PHRASES):
            raise LexiconParseError(
                "CAL lexicon browse page contains neither rows nor explicit no-match"
            )

    next_links = [
        link
        for line in lines
        for link in line.links
        if " ".join(link.text.split()).casefold() == "next page"
    ]
    if len(next_links) > 1:
        raise LexiconParseError("CAL lexicon browse page exposes multiple NEXT PAGE links")

    next_continuation: str | None = None
    if next_links:
        next_continuation = _continuation_from_link(response.url, next_links[0].href)
        if not rows:
            raise LexiconParseError("CAL lexicon no-match page unexpectedly exposes NEXT PAGE")

    return LexiconBrowsePage(
        rows=tuple(rows),
        entries=tuple(entries),
        next_continuation=next_continuation,
    )


class LexiconBrowseService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def browse(
        self,
        prefix: str,
        *,
        representation: InputRepresentation | None = None,
        continuation: str | None = None,
    ) -> LexiconBrowseResult:
        conversion, normalized_prefix = _prepare_prefix(prefix, representation)
        if continuation is None:
            request = CalRequest(
                method="GET",
                path=_BROWSE_PATH,
                params=(("first3", f'"{normalized_prefix}"'),),
            )
        else:
            submitted_continuation = _validate_continuation(continuation)
            request = CalRequest(
                method="GET",
                path=_BROWSE_PATH,
                params=(("direction", "1"), ("sortkey", submitted_continuation)),
            )

        result = await self._client.fetch(
            request,
            parser=parse_lexicon_browse_page,
            cache_namespace="lexicon-public-browse-v1",
        )
        return LexiconBrowseResult(
            prefix=prefix,
            normalized_prefix=normalized_prefix,
            rows=result.value.rows,
            entries=result.value.entries,
            next_continuation=result.value.next_continuation,
            provenance=LexiconBrowseProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="lexicon_browse",
                original_prefix=prefix,
                normalized_prefix=normalized_prefix,
                representation=conversion.representation.value,
                conversion_strategy=conversion.strategy.value,
                continuation=continuation,
            ),
        )


def _prepare_prefix(
    prefix: str,
    representation: InputRepresentation | None,
) -> tuple[CalCodeConversion, str]:
    if representation is not None and representation not in _ALLOWED_REPRESENTATIONS:
        raise UnsupportedQueryError(
            "CAL lexicon browsing supports CAL code, shared Roman input, Unicode "
            "transliteration, Hebrew, or Syriac"
        )

    conversion = convert_to_cal_code(prefix, representation=representation)
    if conversion.representation not in _ALLOWED_REPRESENTATIONS:
        raise UnsupportedQueryError(
            "CAL lexicon browsing supports CAL code, shared Roman input, Unicode "
            "transliteration, Hebrew, or Syriac"
        )
    if len(conversion.words) != 1:
        raise UnsupportedQueryError("CAL lexicon browse prefix must be one word")

    candidates = conversion.words[0].candidates
    if len(candidates) != 1:
        raise AmbiguousQueryError(
            "CAL lexicon browse prefix has multiple CAL-code candidates; use "
            "cal_convert_to_code and choose one explicit CAL-code prefix"
        )
    normalized = candidates[0]
    if not _valid_browse_prefix(normalized):
        raise UnsupportedQueryError(
            "CAL lexicon browse prefix must be one to three documented CAL consonants "
            "or one consonant followed by underscore"
        )
    return conversion, normalized


def _valid_browse_prefix(value: str) -> bool:
    if len(value) == 2 and value[1] == "_":
        return value[0] in _CAL_CONSONANTS
    return 1 <= len(value) <= 3 and all(char in _CAL_CONSONANTS for char in value)


def _continuation_from_link(source_url: str, href: str) -> str:
    resolved = urlsplit(urljoin(source_url, href))
    if (resolved.scheme, resolved.netloc) != _CAL_ORIGIN:
        raise LexiconParseError("CAL lexicon NEXT PAGE link changed origin")
    if resolved.path != f"/{_BROWSE_PATH}":
        raise LexiconParseError("CAL lexicon NEXT PAGE link changed endpoint")
    if resolved.fragment:
        raise LexiconParseError("CAL lexicon NEXT PAGE link unexpectedly has a fragment")

    query = parse_qs(resolved.query, keep_blank_values=True)
    if set(query) != {"direction", "sortkey"}:
        raise LexiconParseError("CAL lexicon NEXT PAGE query shape changed")
    if query.get("direction") != ["1"]:
        raise LexiconParseError("CAL lexicon NEXT PAGE direction changed")
    sortkeys = query.get("sortkey")
    if sortkeys is None or len(sortkeys) != 1 or not sortkeys[0]:
        raise LexiconParseError("CAL lexicon NEXT PAGE sortkey is missing or repeated")
    try:
        return _validate_continuation(sortkeys[0])
    except CalInputError as exc:
        raise LexiconParseError(
            "CAL lexicon NEXT PAGE sortkey is outside the safe contract"
        ) from exc


def _validate_continuation(value: str) -> str:
    if not isinstance(value, str):
        raise CalInputError("continuation must be a string returned by cal_lexicon_browse")
    if not value or value != value.strip():
        raise CalInputError("continuation must be nonempty without surrounding whitespace")
    if len(value) > _CONTINUATION_MAX_LENGTH:
        raise CalInputError("continuation is too long")
    if any(ord(char) < 0x20 or ord(char) > 0x7E for char in value):
        raise CalInputError("continuation must contain printable ASCII only")
    if any(char in _CONTINUATION_FORBIDDEN for char in value):
        raise CalInputError("continuation contains URL or query delimiters")
    return value


def _browse_row_to_dict(row: LexiconBrowseRow) -> dict[str, object]:
    if row.kind is LexiconBrowseRowKind.ENTRY:
        if row.lemma is None:
            raise AssertionError("entry browse row lacks lemma data")
        return {
            "kind": row.kind.value,
            "lemma": _lemma_to_dict(row.lemma),
        }

    if (
        row.source_text is None
        or row.target_lemma_key is None
        or row.target_label is None
    ):
        raise AssertionError("cross-reference browse row lacks target data")
    return {
        "kind": row.kind.value,
        "source_text": row.source_text,
        "target_lemma_key": row.target_lemma_key,
        "target_label": row.target_label,
    }


def _provenance_to_dict(provenance: LexiconBrowseProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "operation": provenance.operation,
        "original_prefix": provenance.original_prefix,
        "normalized_prefix": provenance.normalized_prefix,
        "representation": provenance.representation,
        "conversion_strategy": provenance.conversion_strategy,
        "continuation": provenance.continuation,
    }


__all__ = [
    "LexiconBrowsePage",
    "LexiconBrowseProvenance",
    "LexiconBrowseResult",
    "LexiconBrowseRow",
    "LexiconBrowseRowKind",
    "LexiconBrowseService",
    "parse_lexicon_browse_page",
]
