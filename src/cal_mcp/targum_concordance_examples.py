"""One explicit CAL Targum concordance example text-ID group; no traversal."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from cal_mcp.client import CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import (
    KwicHit,
    KwicScopeKind,
    _apply_kwic_target_structure,
    _hit_to_dict,
    _parse_kwic_hit_lines,
    _validate_lemma_key,
)
from cal_mcp.errors import CalInputError, CalParseError
from cal_mcp.lexicon import _parse_lines
from cal_mcp.targum import TargumProvenance, _make_provenance, _provenance_to_dict

_MAX_TARGUM_GROUP_SIZE = 32
_MAX_TEXT_SELECTORS_BYTES = 256


class TargumConcordanceExamplesParseError(CalParseError):
    """CAL Targum example markup contradicts requested identity or target semantics."""


@dataclass(frozen=True, slots=True)
class TargumConcordanceExamplesPage:
    total: int
    hits: tuple[KwicHit, ...]


@dataclass(frozen=True, slots=True)
class TargumConcordanceExamplesResult:
    lemma_key: str
    text_ids: tuple[str, ...]
    total: int
    hits: tuple[KwicHit, ...]
    provenance: TargumProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "lemma_key": self.lemma_key,
            "text_ids": list(self.text_ids),
            "total": self.total,
            "hits": [_hit_to_dict(hit) for hit in self.hits],
            "provenance": _provenance_to_dict(self.provenance),
        }


def _validate_group(text_ids: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(text_ids, Sequence) or isinstance(text_ids, (str, bytes)):
        raise CalInputError("text_ids must be an ordered array of CAL decimal text IDs")
    ids = tuple(text_ids)
    if not 1 <= len(ids) <= _MAX_TARGUM_GROUP_SIZE:
        raise CalInputError("text_ids must contain 1 to 32 text identifiers")
    if any(
        not isinstance(value, str)
        or not value.isascii()
        or not value.isdecimal()
        or not 1 <= len(value) <= 8
        for value in ids
    ):
        raise CalInputError("each text_ids entry must be a CAL ASCII-decimal text ID")
    if len(set(ids)) != len(ids):
        raise CalInputError("text_ids must not contain duplicates")
    if len(" ".join(ids).encode("ascii")) > _MAX_TEXT_SELECTORS_BYTES:
        raise CalInputError("text_ids exceed the bounded source selector length")
    return ids


def _validate_response_identity(
    source_url: str, *, lemma: str, pos: str, ids: tuple[str, ...]
) -> None:
    try:
        url = urlsplit(source_url)
        port = url.port
    except ValueError as error:
        raise TargumConcordanceExamplesParseError("invalid CAL Targum example URL") from error
    query = parse_qs(url.query, keep_blank_values=True)
    if (
        url.scheme != "https"
        or url.hostname != "cal.huc.edu"
        or port is not None
        or url.username is not None
        or url.password is not None
        or url.fragment
        or url.path != "/show1dialectKWIC.php"
        or set(query) != {"lemma", "pos", "texts", "charset"}
        or query["lemma"] != [lemma]
        or query["pos"] != [pos]
        or query["texts"] != [" ".join(ids)]
        or query["charset"] != ["H"]
    ):
        raise TargumConcordanceExamplesParseError(
            "CAL Targum example response URL contradicts requested selectors"
        )


def parse_targum_concordance_examples_page(
    response: CalResponse, *, lemma_key: str, text_ids: Sequence[str]
) -> TargumConcordanceExamplesPage:
    lemma, pos, canonical = _validate_lemma_key(lemma_key)
    if canonical != lemma_key:
        raise CalInputError("lemma_key must be a canonical CAL lemma key")
    ids = _validate_group(text_ids)
    _validate_response_identity(response.url, lemma=lemma, pos=pos, ids=ids)
    lines = _parse_lines(response)
    texts = [getattr(line, "text", "") for line in lines]
    expected_header = f"Looking for {canonical} in {' '.join(ids)}"
    observed_headers = [line for line in texts if line.startswith("Looking for ")]
    if observed_headers != [expected_header]:
        raise TargumConcordanceExamplesParseError(
            "CAL Targum example group heading contradicts requested selectors"
        )
    summary_re = re.compile(
        r"^([0-9]+) examples found for "
        + re.escape(canonical)
        + r" in dialect "
        + re.escape(" ".join(ids))
        + r"$"
    )
    summary_lines = [line for line in texts if "examples found for" in line]
    totals = [m for text in summary_lines if (m := summary_re.fullmatch(text)) is not None]
    if len(totals) != 1 or len(summary_lines) != 1:
        raise TargumConcordanceExamplesParseError(
            "CAL Targum example page lacks its exact source-specific total"
        )
    total = int(totals[0].group(1))
    if not 1 <= total <= 10000:
        # CAL's observed page has ordinary positive counts; a real zero marker
        # must be separately fixture-backed rather than forged.
        raise TargumConcordanceExamplesParseError(
            "CAL Targum example page has no verified positive example count"
        )

    positioned = _parse_kwic_hit_lines(lines, response.url)
    checked = _apply_kwic_target_structure(
        response, positioned, scope_kind=KwicScopeKind.DIALECT
    )
    hits = tuple(hit for _, hit in checked)
    if len(hits) != total:
        raise TargumConcordanceExamplesParseError(
            "CAL Targum example count contradicts linked target lines"
        )
    if any(hit.file_id not in ids or hit.charset != "H" for hit in hits):
        raise TargumConcordanceExamplesParseError(
            "CAL Targum example target belongs to another text group"
        )
    return TargumConcordanceExamplesPage(total=total, hits=hits)


class TargumConcordanceExamplesService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def examples(
        self, lemma_key: str, text_ids: Sequence[str]
    ) -> TargumConcordanceExamplesResult:
        lemma, pos, canonical = _validate_lemma_key(lemma_key)
        if canonical != lemma_key:
            raise CalInputError("lemma_key must be a canonical CAL lemma key")
        ids = _validate_group(text_ids)
        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path="show1dialectKWIC.php",
                params=(
                    ("lemma", lemma),
                    ("pos", pos),
                    ("texts", " ".join(ids)),
                    ("charset", "H"),
                ),
            ),
            parser=lambda response: parse_targum_concordance_examples_page(
                response, lemma_key=canonical, text_ids=ids
            ),
            cache_namespace="targum-concordance-examples-v1",
        )
        return TargumConcordanceExamplesResult(
            lemma_key=canonical,
            text_ids=ids,
            total=result.value.total,
            hits=result.value.hits,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="targum_concordance_examples",
                lemma_key=canonical,
            ),
        )
