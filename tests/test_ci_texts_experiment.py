"""Offline test-first contract for issue #347's *experimental* CI audit."""

import copy
import json
import sys
from pathlib import Path

import pytest

# The isolated experiment is not part of the installed cal_mcp package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.ci_texts.audit import DraftAuditError, audit_draft  # noqa: E402


def draft():
    return {
        "dialect": "Classical Syriac",
        "text": "ܓܒܪܐ ܚܙܐ ܒܝܬܐ܀ ܓܒܪܐ ܚܙܐ ܡܝܐ܀",
        "known_lemma_keys": ["draft:man", "draft:see", "draft:house"],
        "tokens": [
            {"surface": "ܓܒܪܐ", "lemma_keys": ["draft:man"]},
            {"surface": "ܚܙܐ", "lemma_keys": ["draft:see"]},
            {"surface": "ܒܝܬܐ", "lemma_keys": ["draft:house"]},
            {"surface": "ܓܒܪܐ", "lemma_keys": ["draft:man"]},
            {"surface": "ܚܙܐ", "lemma_keys": ["draft:see"]},
            {"surface": "ܡܝܐ", "lemma_keys": ["draft:water"]},
        ],
        "minimum_coverage": 0.8,
        "max_new_lemmas": 1,
        "evidence_status": "unverified",
        "linguistic_review": "pending",
    }


def test_counts_running_tokens_and_unique_novel_lemmas():
    result = audit_draft(draft())
    assert result["running_tokens"] == 6
    assert result["known_tokens"] == 5
    assert result["unknown_tokens"] == 1
    assert result["coverage"] == pytest.approx(5 / 6)
    assert result["new_lemma_keys"] == ["draft:water"]
    assert result["passes_lexical_budget"] is True
    assert result["linguistically_verified"] is False


def test_repeat_of_unfamiliar_token_reduces_coverage_without_inflating_new_lemmas():
    data = draft()
    data["text"] += " ܡܝܐ܀"
    data["tokens"].append({"surface": "ܡܝܐ", "lemma_keys": ["draft:water"]})
    data["minimum_coverage"] = 0.75
    result = audit_draft(data)
    assert result["running_tokens"] == 7
    assert result["unknown_tokens"] == 2
    assert result["new_lemma_keys"] == ["draft:water"]
    assert result["passes_lexical_budget"] is False


def test_clitic_with_one_unknown_lemma_counts_whole_running_token_as_unknown():
    data = draft()
    data["text"] = "ܒܒܝܬܐ"
    data["tokens"] = [{"surface": "ܒܒܝܬܐ", "lemma_keys": ["draft:in", "draft:house"]}]
    data["minimum_coverage"] = 0.0
    assert audit_draft(data)["unknown_tokens"] == 1


@pytest.mark.parametrize(
    "change",
    [
        lambda x: x["tokens"].pop(),
        lambda x: x["tokens"][0].update(surface="ܚܙܐ"),
        lambda x: x["tokens"][0].update(lemma_keys=[]),
        lambda x: x.update(text=""),
        lambda x: x.update(text="hello ܚܙܐ"),
        # U+0711 is a combining superscript alaph; not a standalone base letter.
        lambda x: x.update(
            text="ܑ",
            tokens=[{"surface": "ܑ", "lemma_keys": ["draft:man"]}],
        ),
        # U+0701 is Syriac punctuation, not a valid letter inside a surface token.
        lambda x: x.update(
            text="ܓܒܪܐ܁ܚܙܐ",
            tokens=[{"surface": "ܓܒܪܐ܁ܚܙܐ", "lemma_keys": ["draft:man"]}],
        ),
        lambda x: x.update(dialect="Biblical Aramaic"),
        lambda x: x.update(minimum_coverage=1.1),
        lambda x: x.update(max_new_lemmas=True),
        lambda x: x.update(evidence_status="CAL-verified"),
        lambda x: x.update(linguistic_review="approved"),
        lambda x: x.update(known_lemma_keys=["draft:man", "draft:man"]),
        lambda x: x["tokens"][0].update(lemma_keys=["draft:man", "draft:man"]),
    ],
)
def test_invalid_or_overclaimed_annotations_fail_closed(change):
    data = copy.deepcopy(draft())
    change(data)
    with pytest.raises(DraftAuditError):
        audit_draft(data)


def test_new_lemma_budget_is_independent_of_running_token_coverage():
    data = draft()
    data["max_new_lemmas"] = 0
    assert audit_draft(data)["passes_lexical_budget"] is False


def test_committed_unreviewed_specimen_has_reproducible_coverage():
    path = Path(__file__).resolve().parents[1] / "experiments/ci_texts/specimen_unreviewed.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    result = audit_draft(data)
    assert result["running_tokens"] == 20
    assert result["known_tokens"] == 19
    assert result["coverage"] == pytest.approx(0.95)
    assert result["new_lemma_keys"] == ["draft:big"]
    assert result["passes_lexical_budget"] is True
    assert result["linguistically_verified"] is False
