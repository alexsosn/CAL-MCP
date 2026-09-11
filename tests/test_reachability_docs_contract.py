from pathlib import Path

_INDEX = Path("docs/index.md")
_CURRENT_GAPS = {
    "#39": "recent",
    "#109": "targum",
    "#112": "prefix",
    "#127": "citation",
}
_RESOLVED_ROUTE_ISSUES = (
    "#78",
    "#97",
    "#101",
    "#105",
    "#106",
    "#107",
    "#108",
    "#113",
    "#125",
)


def _gap_section() -> str:
    text = _INDEX.read_text(encoding="utf-8")
    marker = "## Known current reachability gaps"
    assert marker in text
    section = text.split(marker, 1)[1]
    next_heading = section.find("\n## ")
    return section if next_heading < 0 else section[:next_heading]


def test_public_index_lists_every_current_route_gap_with_task_context() -> None:
    section = _gap_section().casefold()

    for issue, task_word in _CURRENT_GAPS.items():
        assert issue.casefold() in section
        assert task_word in section

    for issue in _RESOLVED_ROUTE_ISSUES:
        assert issue.casefold() not in section


def test_public_index_explains_parent_capability_and_followup_boundary() -> None:
    section = _gap_section().casefold()

    assert "implemented" in section
    assert "does not mean" in section
    assert "every" in section
    assert "follow-up" in section
    assert "mcp-followable" in section


def test_public_index_documents_bounded_alternative_to_show_all() -> None:
    section = _gap_section().casefold()

    assert "show all" in section
    assert "bounded" in section
    assert "cal_text_page" in section
    assert "not exposed" in section
