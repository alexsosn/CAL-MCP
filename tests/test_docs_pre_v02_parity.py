"""Pre-v0.2 release documentation contract against executable and historical facts.

All checks are deterministic and must not contact CAL.
"""

from pathlib import Path

from cal_mcp.release_surface import CURRENT_PUBLIC_TOOLS, V01_PUBLIC_TOOLS

ROOT = Path(__file__).resolve().parents[1]


def _doc(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_readme_published_tool_table_matches_frozen_manifest() -> None:
    readme = _doc("README.md")
    assert len(V01_PUBLIC_TOOLS) == 36
    assert len(CURRENT_PUBLIC_TOOLS) == 37
    assert {"cal_bibliography_recent"} == CURRENT_PUBLIC_TOOLS - V01_PUBLIC_TOOLS

    # Scope this to the table, not to other documentation or references.
    table = readme.split("## v0.1 public surface", 1)[1].split("## System boundary", 1)[0]
    missing = sorted(name for name in V01_PUBLIC_TOOLS if f"`{name}`" not in table)
    assert missing == []
    assert "unreleased" in readme.lower()
    assert "0.2.0.dev0" in readme


def test_docs_index_advertises_published_targum_example_followups() -> None:
    index = _doc("docs/index.md")
    assert "`cal_targum_concordance_examples`" in index
    assert "`cal_targum_reflex_examples`" in index
    assert "not yet MCP-followable" not in index
    assert "[#109]" not in index
    assert "`cal_bibliography_recent()`" in index
    assert "unreleased" in index.lower()


def test_getting_started_distinguishes_new_bibliography_from_published_v01() -> None:
    guide = _doc("docs/getting-started.md")
    assert "cal_bibliography_recent()" in guide
    assert "0.2.0.dev0" in guide
    assert "cal-mcp==0.1.0" in guide
    assert "deferred to issue #39" not in guide
    assert "cal_targum_concordance_examples" in guide
    assert "cal_targum_reflex_examples" in guide
    assert "cal_kwic_full_context" in guide
    assert "cal_syriac_group" in guide


def test_public_integration_docs_distinguish_merged_agora_from_unpublished_marketplace() -> None:
    for path in (
        "README.md",
        "docs/index.md",
        "docs/limitations.md",
        "docs/integrations/standalone-mcp.md",
    ):
        content = _doc(path).lower()
        assert "agora" in content, path
        assert "merged" in content, path
        assert "candidate v1.1" in content, path
        assert "not yet published" in content or "not published" in content, path
        assert "deferred to issue #16" not in content, path
        assert "optional future discovery" not in content, path


def test_release_checklist_keeps_publication_separate_from_docs_merge() -> None:
    checklist = _doc("wiki/release-checklist.md")
    assert "(release-checklist.md)" in _doc("wiki/README.md")
    for token in (
        "0.2.0.dev0",
        "v0.2.0",
        "cal_bibliography_recent",
        "13-case",
        "25",
        "PyPI",
        "GitHub Release",
        "independent review",
        "not a release",
    ):
        assert token.lower() in checklist.lower()


def test_future_package_readme_does_not_repeat_stale_pypi_release_claims() -> None:
    readme = _doc("README.md")
    assert "No versioned release has been published yet" not in readme
    assert "active pre-release development" not in readme
    assert "cal-mcp==0.1.0" in readme
    checklist = _doc("wiki/release-checklist.md")
    assert "long description" in checklist
    assert "METADATA" in checklist
