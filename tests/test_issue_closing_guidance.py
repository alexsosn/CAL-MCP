"""Offline contributor-policy regressions for blocked issue references (#315)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
DEV_LOOP = ROOT / "wiki" / "agentic-dev-loop.md"


def test_agent_instructions_distinguish_completed_from_blocked_issue_refs() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "Fixes #N" in text
    assert "Issue #N remains open" in text
    assert "negated" in text.lower()
    assert "blocked" in text.lower()
    assert "PR description" in text
    assert "merge-commit message" in text


def test_dev_loop_requires_closure_wording_guard_and_post_merge_verification() -> None:
    text = DEV_LOOP.read_text(encoding="utf-8")
    assert "Fixes #N" in text
    assert "Issue #N remains open" in text
    assert "negated" in text.lower()
    assert "blocked" in text.lower()
    assert "merge-commit message" in text
    assert "verify blocked issue states after merge" in text.lower()


def test_docs_do_not_require_closing_references_for_partially_addressed_issues() -> None:
    text = DEV_LOOP.read_text(encoding="utf-8")
    assert "Fully completed" in text
    assert "Partially addressed" in text
    assert "review" in text.lower()
