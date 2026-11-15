"""Offline, adversarial contract for bounded dependent CAL MCP smoke."""

import asyncio
import importlib
from types import SimpleNamespace

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


class _FakeClient:
    def __init__(self, result, *, missing_tool: str | None = None) -> None:
        self.result = result
        self.missing_tool = missing_tool
        self.calls: list[str] = []

    async def list_tools(self):
        return SimpleNamespace(
            tools=[
                SimpleNamespace(name=name, output_schema={"type": "object"})
                for name in CURRENT_PUBLIC_TOOLS
                if name != self.missing_tool
            ]
        )

    async def call_tool(self, name: str, arguments: dict[str, object]):
        self.calls.append(name)
        return self.result


def test_dependency_batch_rejects_broken_registry_before_cal() -> None:
    module = _module()
    fake = _FakeClient(None, missing_tool="cal_bibliography_keyword")
    outcomes = asyncio.run(module.run_cases(fake))
    assert len(outcomes) == 1
    assert outcomes[0].category == "harness"
    assert fake.calls == []


def test_dependency_batch_does_not_guess_a_missing_citation_handle(monkeypatch) -> None:
    module = _module()
    fake = _FakeClient(
        SimpleNamespace(is_error=False, structured_content={"entry": {"senses": []}})
    )
    monkeypatch.setattr(
        module,
        "evaluate_tool_result",
        lambda case, tool, result: SmokeOutcome(case.name, "ok", "success"),
    )
    outcomes = asyncio.run(module.run_cases(fake))
    assert [outcome.case for outcome in outcomes] == ["lexicon", "lexicon_context"]
    assert [outcome.category for outcome in outcomes] == ["ok", "drift"]
    assert fake.calls == ["cal_lexicon_lookup"]


def test_remaining_batch_is_exact_safe_suffix_after_comment_drift() -> None:
    module = _module()
    expected = tuple(step.name for step in module.STEPS[4:])
    assert len(expected) == 17
    assert expected[0] == "kwic_dialects"
    assert expected[-1] == "syriac_group"
    assert tuple(step.name for step in module.REMAINDER_STEPS) == expected
    assert all(step.tool != "cal_text_line_comments" for step in module.REMAINDER_STEPS)
    preceding_tools = {"cal_lexicon_lookup", "cal_text_page"}
    assert all(step.tool not in preceding_tools for step in module.REMAINDER_STEPS)
    assert module.REMAINDER_STEPS[0].parent is None


def test_remaining_batch_cannot_vacuously_pass_or_hide_unattempted_tools() -> None:
    module = _module()
    passed = tuple(SmokeOutcome(step.name, "ok", "success") for step in module.REMAINDER_STEPS)
    assert module.complete_remaining(passed, 17)
    assert module.complete_remaining(passed, 25)
    assert not module.complete_remaining(passed, 16)
    assert not module.complete_remaining(passed, 26)
    assert not module.complete_remaining(passed[:-1], 17)
    assert not module.complete_remaining(passed + passed[-1:], 18)
    wrong = passed[:-1] + (SmokeOutcome(passed[-1].case, "drift", "changed CAL"),)
    assert not module.complete_remaining(wrong, 17)
    assert not module.complete_batch(passed, 17)


def test_remaining_only_never_calls_preceding_text_or_comment_even_on_429(
    monkeypatch,
) -> None:
    module = _module()
    fake = _FakeClient(
        SimpleNamespace(
            is_error=True,
            structured_content={"error": {"kind": "upstream_http", "status_code": 429}},
        )
    )
    monkeypatch.setattr(
        module,
        "evaluate_tool_result",
        lambda case, tool, result: SmokeOutcome(case.name, "unavailable", "CAL 429"),
    )
    outcomes = asyncio.run(module.run_cases(fake, steps=module.REMAINDER_STEPS))
    assert tuple(outcome.case for outcome in outcomes) == ("kwic_dialects",)
    assert fake.calls == ["cal_kwic_dialects"]
    assert not module.complete_remaining(outcomes, 1)


def test_syrian_only_is_exactly_the_unattempted_final_two_steps() -> None:
    module = _module()
    assert len(module.SYRIAC_STEPS) == 2
    assert tuple(step.name for step in module.SYRIAC_STEPS) == ("syriac_category", "syriac_group")
    assert module.SYRIAC_STEPS[0].parent is None
    assert module.SYRIAC_STEPS[1].parent == "syriac_category"
    assert module.SYRIAC_STEPS[1].tool == "cal_syriac_group"


def test_syrian_only_acceptance_cannot_hide_non_attempted_group() -> None:
    module = _module()
    passing = tuple(SmokeOutcome(step.name, "ok", "success") for step in module.SYRIAC_STEPS)
    assert module.complete_syriac(passing, 2)
    assert not module.complete_syriac(passing, 1)
    assert not module.complete_syriac(passing, 3)
    assert not module.complete_syriac(passing[:-1], 2)
    failed = passing[:-1] + (SmokeOutcome("syriac_group", "drift", "bad group"),)
    assert not module.complete_syriac(failed, 2)
    assert not module.complete_remaining(passing, 2)


def test_comment_followup_requires_actual_canonical_cal_link_and_identity() -> None:
    module = _module()
    step = module.STEP_BY_NAME["text_comments"]
    coordinate = "1325002"
    canonical = "https://cal.huc.edu/comment.php?coord=1325002"

    def args_for(link: str | None) -> dict[str, object] | None:
        parent = {
            "text_page": {
                "page": {
                    "lines": [
                        {"coordinate": coordinate, "comment_url": link},
                    ]
                }
            }
        }
        return module.select_arguments(step, parent)

    assert args_for(canonical) == {"coordinate": coordinate}
    for invalid in (
        None,
        "",
        "https://example.org/comment.php?coord=1325002",
        "http://cal.huc.edu/comment.php?coord=1325002",
        "https://cal.huc.edu/comment.php?coord=1325003",
        "https://cal.huc.edu/comment.php?coord=1325002&coord=1325003",
        "https://cal.huc.edu/comment.php?coord=1325002&extra=1",
        "https://cal.huc.edu/comment.php?coord=1325002#fragment",
    ):
        assert args_for(invalid) is None


def test_live_external_citations_selector_only_uses_verified_nonempty_ebpar_source() -> None:
    module = _module()
    step = module.STEP_BY_NAME["external_citations"]
    canonical = "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar"

    def args_for(sources: list[dict[str, str]], dialect_id: str = "6"):
        return module.select_arguments(
            step, {"external_sources": {"dialect_id": dialect_id, "sources": sources}}
        )

    assert args_for([{"abbreviation": "EbPar", "citations_url": canonical}]) == {
        "source_abbrev": "EbPar"
    }
    # The current CAL source-list has two independently described rows sharing EbPar.
    assert args_for(
        [
            {"abbreviation": "EbPar", "citations_url": canonical},
            {"abbreviation": "EbPar", "citations_url": canonical},
        ]
    ) == {"source_abbrev": "EbPar"}
    historical_url = "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH"
    assert args_for([{"abbreviation": "1CorH", "citations_url": historical_url}]) is None
    assert args_for([{"abbreviation": "EbPar", "citations_url": canonical}], dialect_id="7") is None
    for invalid in (
        "",
        "http://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar",
        "https://example.org/displaycits.abbrev.php?abbrev=EbPar",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar&extra=1",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar&abbrev=1CorH",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar#fragment",
    ):
        assert args_for([{"abbreviation": "EbPar", "citations_url": invalid}]) is None
        assert (
            args_for(
                [
                    {"abbreviation": "EbPar", "citations_url": canonical},
                    {"abbreviation": "EbPar", "citations_url": invalid},
                ]
            )
            is None
        )
