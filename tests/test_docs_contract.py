from __future__ import annotations

import importlib
import re
from pathlib import Path
from urllib.parse import unquote

import pytest
from mcp import Client

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TOOLS_DIR = DOCS / "tools"
DOCS_INDEX = DOCS / "index.md"

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

    assert len(tool_names) == 26
    assert missing == []


def test_docs_index_links_every_tool_page_and_records_deferred_capability() -> None:
    assert DOCS_INDEX.exists()
    index = DOCS_INDEX.read_text(encoding="utf-8")

    missing_links = [
        path.name
        for path in sorted(TOOLS_DIR.glob("*.md"))
        if f"tools/{path.name}" not in index
    ]
    assert missing_links == []
    assert "#39" in index
    assert "defer" in index.lower()


def test_relative_markdown_links_resolve() -> None:
    markdown_files = [ROOT / "README.md", *sorted(DOCS.rglob("*.md"))]
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
