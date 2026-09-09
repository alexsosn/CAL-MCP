from __future__ import annotations

import importlib
import socket
from pathlib import Path

import pytest
from mcp import Client

ROOT = Path(__file__).resolve().parents[1]

_SINGLE_FETCH_DESCRIPTION_TOOLS = (
    "cal_gloss_search",
    "cal_gloss_field",
    "cal_citation_text_search",
    "cal_token_analysis",
    "cal_text_concordance",
    "cal_kwic_texts",
    "cal_kwic_dialect",
    "cal_bibliography_authors",
    "cal_bibliography_author",
    "cal_bibliography_keyword",
    "cal_bibliography_lemma",
    "cal_targum_parallel",
    "cal_syriac_missing_words",
    "cal_syriac_peshitta_parallel",
    "cal_external_citation_dialects",
    "cal_external_citation_sources",
    "cal_external_citations",
    "cal_dictionary_collation",
)

_FAMILY_DOCS = {
    "search": ROOT / "docs" / "tools" / "search.md",
    "token-analysis": ROOT / "docs" / "tools" / "token-analysis.md",
    "concordance": ROOT / "docs" / "tools" / "concordance.md",
    "bibliography": ROOT / "docs" / "tools" / "bibliography.md",
    "dictionary-collation": ROOT / "docs" / "tools" / "dictionary-collation.md",
    "targum": ROOT / "docs" / "tools" / "targum.md",
    "syriac": ROOT / "docs" / "tools" / "syriac.md",
    "external-citations": ROOT / "docs" / "tools" / "external-citations.md",
}

_STALE_DOC_PHRASES = {
    "search": (
        "one call performs exactly one field-result request",
        "one mcp call performs exactly one cal search request",
    ),
    "token-analysis": ("performs exactly **one** user-initiated cal request",),
    "concordance": (
        "each public call performs exactly **one** user-initiated cal request",
        "every operation has an exact one-request upper bound",
    ),
    "bibliography": (
        "each public call performs exactly **one** user-initiated cal request",
        "every bibliography operation has an exact one-request upper bound",
    ),
    "dictionary-collation": (
        "each call performs exactly one user-initiated cal request",
        "performs exactly one bounded post to cal",
    ),
    "targum": (
        "each public tool call performs exactly **one** user-initiated cal request",
        "every public targum operation performs exactly one cal request",
    ),
    "syriac": (
        "every public operation performs exactly **one** user-initiated cal request",
        "every public syriac studies operation performs exactly one cal request",
    ),
    "external-citations": ("each tool call performs exactly one bounded cal request",),
}


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


@pytest.mark.anyio
async def test_single_fetch_public_descriptions_are_cache_aware(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("public tool introspection must remain offline")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    stale: list[str] = []
    for tool_name in _SINGLE_FETCH_DESCRIPTION_TOOLS:
        description = _normalize(tools[tool_name].description or "")
        if not all(
            anchor in description
            for anchor in (
                "at most one new logical cal request",
                "cache hit",
                "no new upstream i/o",
            )
        ):
            stale.append(tool_name)

    assert stale == []


def test_non_text_family_docs_are_cache_single_flight_and_retry_aware() -> None:
    failures: list[str] = []
    for family, path in _FAMILY_DOCS.items():
        raw = path.read_text(encoding="utf-8").lower()
        normalized = _normalize(raw)
        for anchor in (
            "at most one new logical cal request",
            "completed cache hit",
            "zero new upstream i/o",
            "single-flight",
            "bounded retry",
        ):
            if anchor not in normalized:
                failures.append(f"{family}: missing {anchor!r}")
        for stale_phrase in _STALE_DOC_PHRASES[family]:
            if stale_phrase in raw:
                failures.append(f"{family}: stale {stale_phrase!r}")

    assert failures == []


def test_request_wording_preserves_operation_specific_shapes() -> None:
    concordance = _normalize(_FAMILY_DOCS["concordance"].read_text(encoding="utf-8"))
    dictionary = _normalize(_FAMILY_DOCS["dictionary-collation"].read_text(encoding="utf-8"))

    assert "one exact cal lemma key in one explicit decimal dialect id" in concordance
    assert (
        "cal_dictionary_collation operation submits at most one new logical post-shaped cal request"
        in dictionary
    )


@pytest.mark.anyio
async def test_local_converter_remains_zero_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("local converter must not open a network socket")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    description = _normalize(tools["cal_convert_to_code"].description or "")
    assert "without any cal network request" in description


def test_lexicon_docs_preserve_bounded_multi_request_exception() -> None:
    lexicon = _normalize((ROOT / "docs" / "tools" / "lexicon.md").read_text(encoding="utf-8"))

    assert "a successful lookup normally uses two cal requests" in lexicon
    assert "eight browser requests plus one entry request" in lexicon
    assert "at most eight unique browser-prefix requests" in lexicon
