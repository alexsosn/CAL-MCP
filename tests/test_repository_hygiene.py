from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_no_issue_scoped_review_helpers_are_tracked() -> None:
    leftovers = {
        *ROOT.glob(".github/issue*_review_fix.py"),
        *ROOT.glob(".github/workflows/issue*-review-fix.yml"),
        *ROOT.glob(".github/workflows/issue-*-review-fix.yml"),
    }

    assert sorted(path.relative_to(ROOT).as_posix() for path in leftovers) == []
