from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp import Client

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.release_surface import V01_PUBLIC_TOOLS
from cal_mcp.texts import (
    TextCatalogueResult,
    TextCategoryRef,
    TextProvenance,
    TextService,
    TextSpecializedCollectionRef,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
DOCS = Path(__file__).parents[1] / "docs" / "tools" / "texts.md"
_RETRIEVED_AT = datetime(2026, 9, 11, tzinfo=UTC)


def _fixture_response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def _provenance() -> TextProvenance:
    return TextProvenance(
        source="CAL",
        source_url="https://cal.huc.edu/newtextmenu.html",
        retrieved_at=_RETRIEVED_AT,
        operation="catalogue",
    )


class CatalogueTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if request.path == "newtextmenu.html":
            return _fixture_response(
                "text_catalogue_root.html",
                "https://cal.huc.edu/newtextmenu.html",
            )
        if request.path == "showsubtexts.php":
            return _fixture_response(
                "text_catalogue_biblical.html",
                "https://cal.huc.edu/showsubtexts.php?subtext=3",
            )
        raise AssertionError(f"unexpected request: {request}")


@pytest.mark.anyio
async def test_root_catalogue_serializes_explicit_shallow_navigation_metadata() -> None:
    transport = CatalogueTransport()
    result = await TextService(CalHttpClient(transport=transport)).catalogue()

    payload = result.to_dict()
    assert payload["recursive"] is False
    assert payload["has_unexpanded_children"] is True
    assert set(payload) == {
        "categories",
        "texts",
        "specialized_collections",
        "provenance",
        "recursive",
        "has_unexpanded_children",
    }
    assert [(item["category_id"], item["label"]) for item in payload["categories"]] == [
        ("3", "Biblical Aramaic"),
        ("21", "Qumran"),
    ]
    assert [(item["file_id"], item["label"]) for item in payload["texts"]] == [
        ("13250", "Tel Dan Stele")
    ]
    assert transport.requests == [CalRequest(method="GET", path="newtextmenu.html")]


@pytest.mark.anyio
async def test_text_only_catalogue_level_is_nonrecursive_without_known_child_navigation() -> None:
    transport = CatalogueTransport()
    result = await TextService(CalHttpClient(transport=transport)).catalogue(category_id="3")

    payload = result.to_dict()
    assert payload["recursive"] is False
    assert payload["has_unexpanded_children"] is False
    assert [item["subtext_id"] for item in payload["texts"]] == ["1", "2", "4"]
    assert transport.requests == [
        CalRequest(method="GET", path="showsubtexts.php", params=(("subtext", "3"),))
    ]


def test_ordinary_child_category_counts_as_unexpanded_navigation() -> None:
    result = TextCatalogueResult(
        categories=(TextCategoryRef(category_id="99", label="Child"),),
        texts=(),
        provenance=_provenance(),
    )

    payload = result.to_dict()
    assert payload["recursive"] is False
    assert payload["has_unexpanded_children"] is True


def test_specialized_collection_counts_as_unexpanded_navigation() -> None:
    result = TextCatalogueResult(
        categories=(),
        texts=(),
        specialized_collections=(
            TextSpecializedCollectionRef(
                collection_key="syriac",
                label="Syriac",
                follow_up_tool="cal_syriac_texts",
                selector_name="category",
                supported_selectors=("all",),
            ),
        ),
        provenance=_provenance(),
    )

    payload = result.to_dict()
    assert payload["recursive"] is False
    assert payload["has_unexpanded_children"] is True


@pytest.mark.anyio
async def test_catalogue_input_schema_remains_category_only() -> None:
    server_module = importlib.import_module("cal_mcp.server")
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    schema = tools["cal_text_catalogue"].model_dump(by_alias=True)["inputSchema"]
    assert set(schema.get("properties", {})) == {"category_id"}
    assert "recursive" not in schema.get("properties", {})


def test_shallow_catalogue_metadata_does_not_change_release_surface() -> None:
    assert len(V01_PUBLIC_TOOLS) == 32
    assert "cal_text_catalogue" in V01_PUBLIC_TOOLS


def test_text_docs_define_shallow_metadata_without_claiming_global_completeness() -> None:
    docs = DOCS.read_text(encoding="utf-8")

    assert "`recursive`" in docs
    assert "`has_unexpanded_children`" in docs
    assert "has_unexpanded_children=false" in docs
    assert "does not" in docs.lower()
    assert "exhaust" in docs.lower()
