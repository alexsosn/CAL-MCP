from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LemmaRef, LexiconParseError, _lemma_to_dict, _parse_lines, parse_browse_page
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


@dataclass(frozen=True, slots=True)
class LexiconBrowsePage:
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
    entries: tuple[LemmaRef, ...]
    next_continuation: str | None
    provenance: LexiconBrowseProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "prefix": self.prefix,
            "normalized_prefix": self.normalized_prefix,
            "entries": [_lemma_to_dict(item) for item in self.entries],
            "next_continuation": self.next_continuation,
            "provenance": _provenance_to_dict(self.provenance),
        }


def parse_lexicon_browse_page(response: CalResponse) -> LexiconBrowsePage:
    base = parse_browse_page(response)
    next_links = [
        link
        for line in _parse_lines(response)
        for link in line.links
        if " ".join(link.text.split()).casefold() == "next page"
    ]
    if len(next_links) > 1:
        raise LexiconParseError("CAL lexicon browse page exposes multiple NEXT PAGE links")

    next_continuation: str | None = None
    if next_links:
        next_continuation = _continuation_from_link(response.url, next_links[0].href)
        if not base.entries:
            raise LexiconParseError("CAL lexicon no-match page unexpectedly exposes NEXT PAGE")

    return LexiconBrowsePage(
        entries=base.entries,
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
    except ValueError as exc:
        raise LexiconParseError("CAL lexicon NEXT PAGE sortkey is outside the safe contract") from exc


def _validate_continuation(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("continuation must be a string returned by cal_lexicon_browse")
    if not value or value != value.strip():
        raise ValueError("continuation must be nonempty without surrounding whitespace")
    if len(value) > _CONTINUATION_MAX_LENGTH:
        raise ValueError("continuation is too long")
    if any(ord(char) < 0x20 or ord(char) > 0x7E for char in value):
        raise ValueError("continuation must contain printable ASCII only")
    if any(char in _CONTINUATION_FORBIDDEN for char in value):
        raise ValueError("continuation contains URL or query delimiters")
    return value


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
    "LexiconBrowseService",
    "parse_lexicon_browse_page",
]
