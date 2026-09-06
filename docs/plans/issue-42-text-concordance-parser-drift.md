# Issue #42 plan — current single-text concordance parser drift

**Plan date:** 2026-09-06

This plan follows the repository gate order: current-source research → committed plan → test-only RED → minimal parser correction → focused/full GREEN → documentation/research synchronization → PR → exact-head independent adversarial review → review-fix RED/GREEN if required.

## Contract to preserve

No public MCP schema changes.

```text
cal_text_concordance(text_id, script="semitic")
```

continues to perform exactly one bounded CAL GET and returns ordered `ConcordanceLemma` items with upstream frequency, lemma key, gloss, KWIC URL, and unchanged provenance.

The current request remains:

```text
GET /newconcord.php?text=<text_id>&cset=<R|S>
```

Issue #42 changes only private response parsing for the currently observed inline row markup.

## RED gate

Before touching production code:

1. add a minimal reduced fixture for the 2026-09-06 `13250` inline `<span>...<br>` shape;
2. add a focused regression test proving the expected ordered frequency/lemma/gloss/KWIC semantics;
3. add current-shape malformed-row coverage where a numeric frequency row loses its relevant link or gloss;
4. establish a valid RED in CI: install, Ruff lint, Ruff format, and mypy green; pytest fails only because the current production parser recognizes no current inline lemma rows.

The fixture contains only a few representative rows, not the full live response.

**RED evidence:** PR CI run `34041950093` at test-only head `7a6347f43dbf595ab9f80975e8e97f505fff766d` passed install, Ruff lint, Ruff format, and mypy. Pytest collected 378 tests and finished `1 failed, 377 passed`; the sole failure was `test_current_inline_text_concordance_preserves_ordered_semantics`, which raised the pre-fix `CAL text concordance contains no recognizable lemma rows` error. The two malformed-inline tests already passed fail-closed.

## Minimal implementation

Keep `parse_text_concordance_page()` marker validation unchanged.

Add a strict current-inline parser using the already shared `_parse_lines()` semantic representation:

- detect current mode only when a semantic line contains both a numeric frequency prefix and a `showKWIC.php` link;
- once current mode is detected, treat every numeric frequency-prefixed semantic line in the concordance row stream as a candidate row and fail if it does not contain exactly one relevant link;
- find the linked lemma text in the rendered line in order, parse the integer frequency from the prefix, and require the post-link segment to begin with `:` and contain a non-empty gloss;
- validate the link through the same single-value, same-origin/path, requested-text, requested-charset, decoded-lemma, and link-text checks used by the table path;
- preserve row order and do not deduplicate;
- if current inline mode is absent, retain the existing strict table parser as a compatibility fallback;
- if neither parser yields rows, keep the existing explicit `ConcordanceParseError`.

Extract only the smallest shared helper needed to avoid having two contradictory link-validation implementations.

**Implementation checkpoint:** commit `1fa30e1eff67e9307ebfdc59216ba9e9a23e995c` adds the inline-row parser and one shared concordance-link validator, keeps the earlier table parser as fallback, appends the dated root research update, and removes all temporary edit/probe files. Public service request construction and advanced/dialect KWIC parsing are unchanged.

## Failure invariants

Tests must continue to prove fail-closed behavior for:

- marker/requested text mismatch;
- wrong or repeated `texts`, `charset`, or `lemma` link parameters;
- link text that contradicts its decoded lemma key;
- missing frequency;
- missing/empty gloss;
- multiple KWIC links in one semantic row;
- numeric current-style row with no KWIC link once inline mode is established;
- no recognized rows.

Advanced/dialect KWIC parsing is out of scope and must remain unchanged.

## Review-regression checkpoint

The first adversarial invariant pass found a concrete gap before final review: once inline mode is recognized, a later `showKWIC.php` row with its frequency prefix removed can fall outside the current contiguous frequency-row window and therefore be silently skipped. A dedicated test, `test_current_inline_mode_rejects_kwic_row_without_frequency`, was added test-first. The first run at `f163dd545472b2dcf62f8219f39791444bb4b65f` was not a valid behavioral RED because Ruff format stopped before pytest; the formatting-only correction at `f85b75629542f2dd994d298b739aedd677da048b` changes no parser behavior. This checkpoint commit exists only to trigger normal PR CI on that exact behavior. A valid review-regression RED must reach pytest with Ruff/format/mypy green and fail on that new test before production code is hardened.

## GREEN and verification

Run, in order:

```text
pytest <focused concordance regression tests>
ruff check .
ruff format --check .
mypy
pytest
```

Normal checks remain offline.

After deterministic GREEN, one optional bounded live production-parser confirmation against the same fixed `13250` URL may be used to prove the release regression is actually closed. If used, it must be one request, no retry/traversal, and the temporary workflow must be deleted immediately.

## Documentation/research gate

Before review:

- keep `docs/research/issue-42-text-concordance-parser-drift.md` as the detailed evidence record;
- append the changed markup assumption to root `research.md` as a dated research update;
- update user docs only if user-visible behavior/limitations changed; this parser-only restoration should require no public tool-reference change;
- no architecture decision update is needed because the public contract and durable boundaries remain unchanged.

## Independent adversarial review gate

Review the exact final PR head independently from the implementation path. The reviewer must try to falsify the correction by checking:

- whether an unrelated numeric line can be misclassified as a lemma row;
- whether a missing current row can be silently skipped after inline mode begins;
- whether multiple/contradictory links can pass;
- whether gloss parsing can absorb adjacent rows or presentation text;
- whether old table compatibility weakens fail-closed behavior;
- whether one public call still makes exactly one CAL request;
- whether advanced/dialect KWIC code changed accidentally;
- whether the minimal fixture actually represents the 2026-09-06 current shape;
- whether research/load evidence is complete and no temporary probe workflow remains.

Any blocker gets a test-only review-regression RED before its fix, then full GREEN and a fresh exact-head independent re-review.
