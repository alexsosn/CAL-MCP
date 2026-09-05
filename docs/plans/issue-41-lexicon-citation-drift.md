# Issue #41 plan — fix current CAL lexicon citation-count drift

**Plan date:** 2026-09-06

This ticket follows research → plan → fixture/test-only RED → minimal parser fix → full offline GREEN → exact-head adversarial review → review-regression RED/GREEN if needed → guarded merge.

## Scope

Restore faithful parsing of current CAL full-entry citation blocks where citation links, not semicolons inside linked citation text, define citation-record boundaries.

The public `cal_lexicon_lookup` contract, two-request successful lookup flow, provenance model, and rendered citation-count integrity check remain unchanged.

## Frozen research conclusion

Current live `br N` contains one `▶ 3 citations` block with exactly three citation links. The existing parser produces six records because it re-splits each linked citation's rendered chunk on semicolons. One semicolon is part of a linked citation's own transliteration/translation text; other semicolons are presentation separators immediately before subsequent citation links.

Existing reduced fixture coverage also shows that semicolon splitting must remain for *unlinked prefix* citation records before the first linked citation.

## TDD RED gate

Before changing `src/cal_mcp/lexicon.py`:

1. add a minimal reduced fixture representing the current three-linked-citation shape;
2. add regression tests that assert exactly three parsed citations with correct link/text association and preservation of an internal semicolon;
3. retain/extend a mismatch regression proving a genuinely incorrect `▶ N citations` marker still fails closed;
4. run normal CI.

A valid RED requires:

- install green;
- `ruff check .` green;
- `ruff format --check .` green;
- strict `mypy` green;
- pytest failing only because the current linked-citation parser creates false extra records for the new fixture.

No production code may change before this RED is established.

## Minimal implementation

Modify `_parse_citations()` only as needed:

- wholly unlinked lines: keep semicolon splitting;
- unlinked prefix before the first link: keep semicolon splitting;
- each linked citation: use its link as the record start and the next link/end-of-line as the record end;
- trim only presentation separator punctuation at the boundary between linked records;
- preserve semicolons inside linked citation text;
- do not generate raw citation records from semicolon fragments inside linked chunks.

Do **not** remove or relax `_SenseBuilder.freeze()`'s expected-count equality check.

## Required regression assertions

The new current-shape fixture must prove:

- `▶ 3 citations` + three links → exactly three `Citation` records;
- references remain `AGnEx 4.9`, `JSBhom 71day1 293`, `BT Yev 76a(40)`;
- each URL remains attached to its corresponding reference;
- separator semicolons before the next link do not create records or pollute the preceding text;
- an internal semicolon in the final linked citation remains in `Citation.text`;
- existing mixed raw-prefix + linked citations still parse to their rendered count;
- rendered count mismatch still raises `LexiconParseError`.

## Full GREEN gate

Run the repository's normal deterministic suite:

```text
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
pytest
```

Normal CI must remain offline.

## Optional bounded verification

After offline GREEN, at most one fixed live verification of `br N` may be run with retries/cache disabled and concurrency 1. It must not be required by normal CI and any temporary workflow must delete itself before final review.

The live verification should fail if the MCP call returns `is_error`, not merely check that a result object exists.

## Adversarial review gate

Freeze an exact final SHA and review skeptically against:

1. current live evidence and the reduced fixture;
2. count integrity — no broad weakening of `▶ N citations` validation;
3. mixed raw/link behavior — raw prefix records still supported;
4. linked text fidelity — internal punctuation/scripts preserved;
5. boundary ambiguity — no silent loss of a genuinely unlinked trailing citation;
6. existing lexicon inline-style, nested-sense, depth-one-subsense, and citation regressions;
7. no public schema/request-volume change;
8. no temporary workflow/helper in the final diff.

Any blocker enters review-regression RED → minimal fix → full GREEN → fresh exact-head review.

## Merge gate

Merge only when research and plan precede implementation, the valid RED is recorded, full offline CI is green, the exact final SHA receives a clean independent review, no review threads remain, and guarded merge pins that reviewed SHA.

## CAL load impact

Implementation/testing are offline. Research has already used two fixed additional `br N` entry requests beyond the release probe. Any post-fix live check is capped at one additional request sequence for the same explicit entry; no crawl or enumeration.