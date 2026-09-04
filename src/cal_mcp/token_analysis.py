from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import (
    LemmaRef,
    _lemma_key_from_href,
    _lemma_to_dict,
    _parse_lemma_header,
    _parse_lines,
)

_COORDINATE_RE = re.compile(r"^[0-9]+$")
_ANALYSIS_MARKER = "click on a headword to see a complete lexicon entry"
_NO_DATA_MARKER = "there is no data for this word"


class TokenAnalysisParseError(CalContentError):
    """Raised when a CAL token-analysis page no longer exposes required semantics."""


class TokenAnalysisStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class TokenAnalysisCandidate:
    analysis_label: str
    lemma: LemmaRef


@dataclass(frozen=True, slots=True)
class TokenAnalysisPage:
    candidates: tuple[TokenAnalysisCandidate, ...]


@dataclass(frozen=True, slots=True)
class TokenAnalysisProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    coordinate: str
    word_index: int


@dataclass(frozen=True, slots=True)
class TokenAnalysisResult:
    status: TokenAnalysisStatus
    coordinate: str
    word_index: int
    candidates: tuple[TokenAnalysisCandidate, ...]
    provenance: TokenAnalysisProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "coordinate": self.coordinate,
            "word_index": self.word_index,
            "candidates": [_candidate_to_dict(item) for item in self.candidates],
            "provenance": _provenance_to_dict(self.provenance),
        }


def parse_token_analysis_page(response: CalResponse) -> TokenAnalysisPage:
    lines = _parse_lines(response)
    page_text = " ".join(line.text.lower() for line in lines)
    marker_indices = [
        index for index, line in enumerate(lines) if line.text.lower() == _ANALYSIS_MARKER
    ]
    has_lemma_path = any(
        _is_lemma_path(link.href) for line in lines for link in line.links
    )

    if _NO_DATA_MARKER in page_text:
        if marker_indices or has_lemma_path:
            raise TokenAnalysisParseError(
                "CAL token-analysis page mixes explicit no-data with analysis markup"
            )
        return TokenAnalysisPage(candidates=())

    if len(marker_indices) != 1:
        raise TokenAnalysisParseError("CAL token-analysis page is missing its unique result marker")

    candidates: list[TokenAnalysisCandidate] = []
    index = marker_indices[0] + 1
    while index < len(lines):
        label_line = lines[index]
        if _is_return_to_text_browser(label_line):
            break
        if index + 1 >= len(lines):
            break

        lemma_line = lines[index + 1]
        lemma_path_links = tuple(
            link for link in lemma_line.links if _is_lemma_path(link.href)
        )
        if not lemma_path_links:
            if _parse_lemma_header(
                lemma_line.text,
                lemma_key="placeholder",
                require_gloss=True,
            ) is not None:
                raise TokenAnalysisParseError(
                    "CAL token-analysis candidate lemma header is missing its lemma link"
                )
            if candidates:
                break
            raise TokenAnalysisParseError(
                "CAL token-analysis result marker is not followed by a candidate"
            )

        if label_line.links:
            raise TokenAnalysisParseError("CAL token-analysis label unexpectedly contains links")
        analysis_label = label_line.text.strip()
        if not analysis_label:
            raise TokenAnalysisParseError(
                "CAL token-analysis candidate has an empty analysis label"
            )
        if len(lemma_path_links) != 1:
            raise TokenAnalysisParseError(
                "CAL token-analysis candidate has multiple lemma-entry links"
            )

        lemma_link = lemma_path_links[0]
        lemma_key = _lemma_key_from_href(lemma_link.href)
        if lemma_key is None:
            raise TokenAnalysisParseError(
                "CAL token-analysis candidate lemma link is missing its lemma key"
            )
        lemma = _parse_lemma_header(
            lemma_link.text,
            lemma_key=lemma_key,
            require_gloss=True,
        )
        if lemma is None:
            raise TokenAnalysisParseError(
                "CAL token-analysis candidate has an unrecognized lemma header"
            )

        candidates.append(TokenAnalysisCandidate(analysis_label=analysis_label, lemma=lemma))
        index += 2

    if not candidates:
        raise TokenAnalysisParseError(
            "CAL token-analysis page has neither candidates nor explicit no-data"
        )
    return TokenAnalysisPage(candidates=tuple(candidates))


class TokenAnalysisService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def analyze(self, coordinate: str, word_index: int) -> TokenAnalysisResult:
        normalized_coordinate = _validate_coordinate(coordinate)
        normalized_word_index = _validate_word_index(word_index)

        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="getlex.php",
                params=(
                    ("coord", normalized_coordinate),
                    ("word", str(normalized_word_index)),
                ),
            ),
            parser=parse_token_analysis_page,
            cache_namespace="token-analysis-v1",
        )
        status = (
            TokenAnalysisStatus.FOUND
            if result.value.candidates
            else TokenAnalysisStatus.NOT_FOUND
        )
        provenance = TokenAnalysisProvenance(
            source="CAL",
            source_url=result.source_url,
            retrieved_at=result.retrieved_at,
            coordinate=normalized_coordinate,
            word_index=normalized_word_index,
        )
        return TokenAnalysisResult(
            status=status,
            coordinate=normalized_coordinate,
            word_index=normalized_word_index,
            candidates=result.value.candidates,
            provenance=provenance,
        )


def _validate_coordinate(value: str) -> str:
    if not isinstance(value, str) or _COORDINATE_RE.fullmatch(value) is None:
        raise ValueError("coordinate must be a CAL decimal machine coordinate")
    return value


def _validate_word_index(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("word_index must be a non-negative integer")
    return value


def _is_lemma_path(href: str) -> bool:
    path = urlsplit(href).path
    return path.endswith("oneentry.php") or path.endswith("cal_entry_web.php")


def _is_return_to_text_browser(line: object) -> bool:
    links = getattr(line, "links", ())
    return any(urlsplit(link.href).path.endswith("newtextmenu.html") for link in links)


def _candidate_to_dict(candidate: TokenAnalysisCandidate) -> dict[str, object]:
    return {
        "analysis_label": candidate.analysis_label,
        "lemma": _lemma_to_dict(candidate.lemma),
    }


def _provenance_to_dict(provenance: TokenAnalysisProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "coordinate": provenance.coordinate,
        "word_index": provenance.word_index,
    }


__all__ = [
    "TokenAnalysisCandidate",
    "TokenAnalysisPage",
    "TokenAnalysisParseError",
    "TokenAnalysisProvenance",
    "TokenAnalysisResult",
    "TokenAnalysisService",
    "TokenAnalysisStatus",
    "parse_token_analysis_page",
]
