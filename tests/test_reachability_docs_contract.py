"""Public route documentation distinguishes resolved work from deliberate boundaries."""

from pathlib import Path

_INDEX = Path("docs/index.md")
_RESOLVED_ROUTE_ISSUES = (
    "#78",
    "#97",
    "#101",
    "#105",
    "#106",
    "#107",
    "#108",
    "#109",
    "#112",
    "#113",
    "#125",
    "#127",
)


def _boundary_section() -> str:
    text = _INDEX.read_text(encoding="utf-8")
    marker = "## Release boundaries and deliberate limitations"
    assert marker in text
    section = text.split(marker, 1)[1]
    next_heading = section.find("\n## ")
    return section if next_heading < 0 else section[:next_heading]


def test_public_index_recognizes_completed_followups_and_unreleased_snapshot() -> None:
    section = _boundary_section().casefold()
    assert "targum" in section
    assert "cal_targum_concordance_examples" in section
    assert "cal_targum_reflex_examples" in section
    assert "published v0.1.0" in section
    assert "completed" in section and "#39" in section
    assert "unreleased 0.2.0.dev0" in section
    assert "cal_bibliography_recent" in section

    # Do not resurrect historical resolved routes as outstanding reachability gaps.
    for issue in _RESOLVED_ROUTE_ISSUES:
        assert issue not in section


def test_public_index_explains_explicit_followup_and_url_boundaries() -> None:
    section = _boundary_section().casefold()
    assert "selectors" in section
    assert "previous explicit" in section
    assert "never prefetched" in section
    assert "other cal urls" in section
    assert "not automatically mcp-followable" in section


def test_public_index_documents_bounded_alternative_to_show_all() -> None:
    section = _boundary_section().casefold()
    assert "show all" in section
    assert "bounded" in section
    assert "cal_text_page" in section
    assert "not exposed" in section
