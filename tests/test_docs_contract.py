from __future__ import annotations

import importlib
import re
from pathlib import Path
from urllib.parse import unquote

import pytest
from mcp import Client

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DOCS = ROOT / "docs"
TOOLS_DIR = DOCS / "tools"
DOCS_INDEX = DOCS / "index.md"
CONFIGURATION = DOCS / "configuration.md"
RESEARCH_AUDIT = DOCS / "research" / "issue-12-v0.1-contract-docs.md"
ARCHITECTURE = ROOT / "wiki" / "architecture.md"
LEXICON_DOC = TOOLS_DIR / "lexicon.md"
INPUT_DOC = DOCS / "concepts" / "input-and-transliteration.md"

REQUIRED_V01_DOCS = (
    "docs/index.md",
    "docs/getting-started.md",
    "docs/installation.md",
    "docs/configuration.md",
    "docs/concepts/cal-identifiers.md",
    "docs/concepts/input-and-transliteration.md",
    "docs/concepts/provenance-and-citation.md",
    "docs/concepts/errors-and-upstream-drift.md",
    "docs/guides/lexical-research.md",
    "docs/guides/corpus-context.md",
    "docs/guides/reproducible-citations.md",
    "docs/integrations/standalone-mcp.md",
    "docs/limitations.md",
)

_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def test_required_v01_user_docs_exist() -> None:
    missing = [path for path in REQUIRED_V01_DOCS if not (ROOT / path).exists()]
    assert missing == []


@pytest.mark.anyio
async def test_every_public_tool_is_covered_by_tool_docs() -> None:
    server_module = importlib.import_module("cal_mcp.server")
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tool_names = sorted(tool.name for tool in (await client.list_tools()).tools)

    tool_docs = "\n".join(path.read_text(encoding="utf-8") for path in TOOLS_DIR.glob("*.md"))
    missing = [tool_name for tool_name in tool_names if f"`{tool_name}`" not in tool_docs]

    assert len(tool_names) == 33
    assert missing == []


def test_readme_release_surface_tracks_public_tools() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "33 public tools" in readme
    assert "33-tool surface" in readme
    assert "`cal_convert_to_code`" in readme
    assert "`cal_lexicon_citation_context`" in readme
    assert "`cal_gloss_field`" in readme
    assert "`cal_text_information`" in readme
    assert "`cal_text_line_comments`" in readme
    assert "`cal_kwic_full_context`" in readme
    assert "`cal_syriac_group`" in readme


def test_docs_index_links_every_tool_page_and_records_deferred_capability() -> None:
    assert DOCS_INDEX.exists()
    index = DOCS_INDEX.read_text(encoding="utf-8")

    missing_links = [
        path.name for path in sorted(TOOLS_DIR.glob("*.md")) if f"tools/{path.name}" not in index
    ]
    assert missing_links == []
    assert "33 tools" in index
    assert "`cal_convert_to_code`" in index
    assert "`cal_lexicon_citation_context`" in index
    assert "`cal_gloss_field`" in index
    assert "`cal_text_information`" in index
    assert "`cal_text_line_comments`" in index
    assert "`cal_kwic_full_context`" in index
    assert "`cal_syriac_group`" in index
    assert "#39" in index
    assert "defer" in index.lower()


def test_configuration_documents_scalar_runtime_type_contract() -> None:
    configuration = CONFIGURATION.read_text(encoding="utf-8")

    assert "booleans and non-numeric values are rejected" in configuration
    assert "`cache_enabled` must be an actual boolean" in configuration
    assert "User-Agent must be a non-empty string" in configuration


def test_cross_cutting_request_bounds_preserve_lexicon_two_request_exception() -> None:
    research = RESEARCH_AUDIT.read_text(encoding="utf-8")
    architecture = ARCHITECTURE.read_text(encoding="utf-8")
    lexicon = LEXICON_DOC.read_text(encoding="utf-8")

    # cal_lexicon_lookup is intentionally the bounded two-request success-path exception.
    assert "successful lookup normally uses two CAL requests" in lexicon
    assert "one public operation maps to one CAL request" not in research
    assert "one explicit HTTP request" not in architecture
    assert "cal_lexicon_lookup" in research
    assert "two CAL requests" in research


def test_converter_docs_name_every_supported_v01_input_representation() -> None:
    text = INPUT_DOC.read_text(encoding="utf-8")

    for representation in (
        "unicode_transliteration",
        "hebrew",
        "syriac",
        "imperial_aramaic",
        "palmyrene",
        "nabataean",
        "hatran",
        "samaritan",
        "mandaic",
    ):
        assert f"`{representation}`" in text

    assert "does not transliterate Hebrew to Syriac" not in text
    assert "or either script to Roman code in v0.1" not in text


def test_converter_docs_explain_researched_finite_ambiguities() -> None:
    text = INPUT_DOC.read_text(encoding="utf-8")

    for grapheme in ("ש", "𐣣", "ࠔ", "ܖ"):
        assert f"`{grapheme}`" in text
    assert "32 candidates" in text
    assert "never" in text.lower() and "truncate" in text.lower()


def test_converter_docs_record_script_specific_edges_and_fail_closed_boundary() -> None:
    text = INPUT_DOC.read_text(encoding="utf-8")

    assert "`ࡖ`" in text and "`D`" in text
    assert "`ࡗ`" in text and "`kD`" in text
    assert "`ܧ`" in text and "`P`" in text
    assert "`ܞ`" in text and "unsupported" in text.lower()
    assert "combining marks" in text.lower()
    assert "fail" in text.lower() and "closed" in text.lower()


def test_lexicon_docs_name_conversion_path_provenance_fields() -> None:
    text = LEXICON_DOC.read_text(encoding="utf-8")

    for field in (
        "cal_code_word_candidates",
        "cal_code_query_candidates",
        "browse_prefixes",
        "selected_cal_code_candidates",
    ):
        assert f"`{field}`" in text


def test_relative_markdown_links_resolve() -> None:
    markdown_files = [README, *sorted(DOCS.rglob("*.md"))]
    broken: list[str] = []

    for markdown_file in markdown_files:
        text = markdown_file.read_text(encoding="utf-8")
        for raw_target in _MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#", "/")):
                continue

            target_without_fragment = target.split("#", 1)[0].split("?", 1)[0]
            if not target_without_fragment:
                continue
            resolved = (markdown_file.parent / unquote(target_without_fragment)).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                broken.append(f"{markdown_file.relative_to(ROOT)} -> {target}")
                continue
            if not resolved.exists():
                broken.append(f"{markdown_file.relative_to(ROOT)} -> {target}")

    assert broken == []
