from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "path",
    [
        "docs/research/issue-73-native-unicode-lexicon-pass-through.md",
        "docs/plans/issue-73-native-unicode-lexicon-pass-through.md",
        "docs/tools/lexicon.md",
    ],
)
def test_issue73_contract_documents_cal_native_bound_form_separator(path: str) -> None:
    text = Path(path).read_text(encoding="utf-8")

    assert "CAL-native bound-form `_` separator" in text
