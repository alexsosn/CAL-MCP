"""Offline, adversarial contract for bounded dependent CAL MCP smoke."""

import importlib

from cal_mcp.release_surface import CURRENT_PUBLIC_TOOLS
from cal_mcp.stdio_live_smoke import DEFAULT_SMOKE_CASES, SmokeOutcome


def _module():
    return importlib.import_module("cal_mcp.pre_release_followup_smoke")


_EXPECTED_NEW_TOOLS = {
    "cal_lexicon_citation_context",
    "cal_text_line_comments",
    "cal_kwic_dialect",
    "cal_kwic_full_context",
    "cal_bibliography_author",
    "cal_bibliography_keyword",
    "cal_targum_concordance_examples",
    "cal_targum_hebrew_reflexes",
    "cal_targum_reflex_examples",
    "cal_external_citation_sources",
    "cal_external_citations",
    "cal_syriac_group",
}


def test_followup_batch_covers_every_remaining_public_tool_exactly_once() -> None:
    module = _module()
    from cal_mcp.pre_release_smoke import BATCH_CASES

    previously = {case.tool for case in DEFAULT_SMOKE_CASES} | {case.tool for case in BATCH_CASES}
    assert CURRENT_PUBLIC_TOOLS - previously == _EXPECTED_NEW_TOOLS
    assert len(module.STEPS) == 21
    assert len({step.name for step in module.STEPS}) == 21
    actual = {step.tool for step in module.STEPS if step.tool not in previously}
    assert actual == _EXPECTED_NEW_TOOLS
    assert sum(step.tool in _EXPECTED_NEW_TOOLS for step in module.STEPS) == 12


def test_every_followup_requires_a_previous_validated_parent() -> None:
    module = _module()
    for step in module.STEPS:
        if step.parent is not None:
            assert module.select_arguments(step, {}) is None
            assert step.arguments is None
    assert all(step.parent is not None for step in module.STEPS if step.tool in _EXPECTED_NEW_TOOLS)


def test_typed_selectors_come_from_returned_payload_not_an_arbitrary_url() -> None:
    module = _module()
    args = module.select_arguments(
        module.STEP_BY_NAME["kwic_context"],
        {
            "kwic_hits": {
                "hits": [
                    {
                        "file_id": "13250",
                        "target_coordinate": "132501001",
                        "charset": "R",
                        "subtext_id": None,
                        "full_context_url": "https://evil.example/forged",
                    }
                ]
            }
        },
    )
    assert args == {
        "file_id": "13250",
        "target_coordinate": "132501001",
        "charset": "R",
    }
    assert (
        module.select_arguments(
            module.STEP_BY_NAME["kwic_context"],
            {"kwic_hits": {"hits": [{"full_context_url": "https://evil.example"}]}},
        )
        is None
    )


def test_selected_author_comes_from_cal_candidates() -> None:
    module = _module()
    step = module.STEP_BY_NAME["bibliography_author"]
    assert module.select_arguments(step, {"authors": {"candidates": []}}) is None
    args = module.select_arguments(
        step,
        {"authors": {"candidates": [{"value": "Kaufman, Stephen A.", "label": "Kaufman"}]}},
    )
    assert args == {"author": "Kaufman, Stephen A."}


def test_frozen_21_step_acceptance_cannot_pass_on_skips_or_partial_io() -> None:
    module = _module()
    good = tuple(SmokeOutcome(step.name, "ok", "success") for step in module.STEPS)
    assert module.complete_batch(good, 21)
    assert module.complete_batch(good, 25)
    assert not module.complete_batch(good, 20)
    assert not module.complete_batch(good, 26)
    assert not module.complete_batch(good[:-1], 22)
    assert not module.complete_batch(good + good[-1:], 22)
    assert not module.complete_batch(
        good[:-1] + (SmokeOutcome(good[-1].case, "skipped_dependency", "no parent"),),
        22,
    )


def test_invalid_targum_lemma_and_syrian_group_are_not_guessed() -> None:
    module = _module()
    assert (
        module.select_arguments(
            module.STEP_BY_NAME["targum_reflex"],
            {"hebrew_lemmas": {"candidates": [{"mt_lemma_id": "0001"}]}},
        )
        is None
    )
    assert (
        module.select_arguments(
            module.STEP_BY_NAME["syriac_group"],
            {"syriac_category": {"items": [{"upstream_id": "60420", "navigation_kind": "text"}]}},
        )
        is None
    )
