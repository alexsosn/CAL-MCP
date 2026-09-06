# Issue #47 plan — restore current CAL lexicon browse parsing

**Issue:** #47  
**Research:** `docs/research/issue-47-lexicon-browse-drift.md`  
**Scope owner:** lexicon semantic extraction / browse parsing only

## Frozen problem statement

Current CAL browse pages contain malformed jump-table anchors that omit literal `</a>` tags before table-cell boundaries. Browsers repair those anchors; Python's `HTMLParser` does not. CAL-MCP's shared semantic parser therefore carries a stale jump link into later cells and swallows valid `oneentry.php` candidate anchors, causing a successful `br` browse response to fail with `LexiconParseError`.

The CAL request contract, candidate link contract, public MCP schema, one-request browse bound, provenance, and pagination policy remain unchanged.

## Non-goals

- no automatic `NEXT PAGE` traversal;
- no release/publishing work from issues #15/#46;
- no lexicon model/schema redesign;
- no broader pronunciation/headword heuristic cleanup;
- no CAL data correction or inferred aliases;
- no generic permissive HTML recovery that turns malformed lexical semantics into partial success.

## Gate 1 — deterministic RED

Commit tests/fixture before production changes.

### Reduced upstream-shape fixture

Add one deliberately reduced fixture captured from the 2026-09-06 `br` structural shape. It contains only:

1. malformed jump-table cells whose `<a>` tags are implicitly closed by `</td>` rather than literal `</a>`;
2. two ordered, well-formed `oneentry.php` candidate cells using the current nested lemma/pronunciation/POS markup and `<br>` + gloss structure;
3. one navigation/continuation link proving it is ignored rather than exposed as a candidate.

The fixture records the source URL/date in comments and must not contain the full CAL page.

### Regression assertions

Add a parser test that requires the reduced current shape to yield ordered candidates with exact CAL lemma keys, headwords, POS, and glosses. On the unmodified parser this test must fail for the same reason as the release smoke: no entries/no explicit no-match.

Add a malformed-current-row regression with at least one otherwise valid candidate followed by a candidate-like `oneentry.php` link missing a required semantic such as POS or lemma key. The parser must raise `LexiconParseError` instead of returning a silently partial candidate list. This should also be RED on the pre-fix parser.

Retain/explicitly exercise the existing well-formed browse fixture so alias handling and old compatible markup stay green.

### RED evidence

Run the focused lexicon test set on the test-only commit. Record that the new current-shape and partial-result regressions fail for their intended reasons while unrelated/static checks are not changed by production code.

## Gate 2 — smallest implementation

### Semantic HTML recovery

Modify `_SemanticHTMLParser` only as far as needed to respect browser-level anchor boundaries for the observed malformed table navigation.

Preferred invariant: an open anchor cannot leak across a table-cell boundary. At `</td>` / `</th>`, finalize the currently rendered anchor before flushing the cell. This mirrors the rendered DOM boundary without introducing arbitrary document-wide repair.

Keep `span.cit-ref-plain` handling and valid nested span behavior unchanged. Do not loosen ignored-content or citation-boundary checks.

### Browse fail-closed hardening

In `parse_browse_page()`, distinguish ordinary navigation links from candidate-like CAL entry links. If a link targets the recognized lexical entry handler (`oneentry.php` / `cal_entry_web.php`) but lacks a usable `lemma` key or recognizable required lemma-header semantics, raise `LexiconParseError` instead of silently skipping it when other candidates are valid.

Do not reinterpret unrelated links as candidates. Preserve CAL order and existing alias/gloss extraction behavior.

## Gate 3 — focused and full offline GREEN

Run, in order:

1. focused lexicon parser/service regressions;
2. `ruff check .`;
3. `ruff format --check .`;
4. `mypy`;
5. full `pytest` with normal CI network-independent behavior.

Any failure caused by the change is fixed before live confirmation. No test may require CAL network access.

## Gate 4 — docs/research synchronization

- keep the focused research artifact as the detailed evidence record;
- append a dated root `research.md` entry for the changed upstream assumption if practical in the same PR;
- no `wiki/decisions.md` update unless implementation reveals a durable architecture change;
- public lexicon docs need no semantic/schema change unless implementation changes user-visible behavior beyond restoring the documented lookup contract.

## Gate 5 — bounded live confirmation

After offline GREEN, perform one fixed live `br` lookup through the production service/tool path with cache controlled/disabled and a strict request cap. Expected behavior:

- browse response parses at least one candidate;
- exact `br` candidate selection follows the existing service contract;
- total CAL requests stay within the already documented lookup bound;
- no pagination traversal occurs;
- provenance remains CAL source URL + actual retrieval timestamp.

If the production lookup needs the selected full entry and current full-entry parsing fails for an unrelated drift, record/open a separate release blocker rather than broadening #47 without a failing regression and issue update.

The live gate is temporary/branch-only and removed before final review.

## Gate 6 — logically independent adversarial review

Open a focused PR closing #47. Review the exact final head independently from this plan/implementation rationale, using the issue and repository invariants as authority.

Required adversarial checks:

- malformed navigation recovery cannot cause semantic candidate loss or invention;
- candidate-like malformed rows fail closed even when valid rows precede/follow them;
- valid well-formed browse and alias fixtures remain unchanged;
- no `NEXT PAGE` hidden traversal or request-count expansion;
- full-entry/citation parsing is not weakened by shared-parser changes;
- no public schema/provenance/normalization behavior drifts;
- tests would fail if the anchor-boundary fix were removed;
- the exact reviewed head is the head merged.

Request changes on any blocker; revise with new failing tests first for behavior changes, rerun full gates, and repeat independent review on the new exact head.
