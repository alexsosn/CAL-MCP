# Issue #47 plan — recover current CAL lexicon browse anchors

**Plan date:** 2026-09-06

Required gate order: research → committed plan → test-only RED → minimal implementation → focused/full offline GREEN → bounded live confirmation → exact-head independent adversarial review → merge.

## Contract to preserve

- public MCP schema is unchanged;
- `cal_lexicon_lookup` keeps the same arguments and result models;
- browse discovery remains one GET to `browseSKEYheaders.php` with the normalized quoted `first3` prefix;
- exact candidate selection may perform at most one subsequent selected-entry request;
- CAL order, canonical lemma keys, headwords, pronunciation, POS, glosses, aliases, and provenance remain source-controlled;
- explicit no-match remains distinct from parser drift;
- normal CI remains offline.

## Test-only RED gate

Before production changes, add a reduced current-shape fixture containing malformed unclosed jump-menu anchors followed by valid lexicon candidate anchors and glosses.

Add deterministic regressions proving:

1. `parse_browse_page` currently fails on that fixture, reproducing the live drift;
2. after correction, the first valid candidate is independently linked and parsed as canonical `br N` rather than being swallowed by a stale jump-menu anchor;
3. a second candidate remains independently linked and ordered;
4. adjacent gloss text still belongs to the intended candidate;
5. pre-existing valid browse fixtures remain unchanged;
6. explicit no-match pages still return an empty `BrowsePage`;
7. unrelated malformed/current-looking content without valid candidate semantics still raises `LexiconParseError`.

Establish a behavioral RED with Ruff lint/format and strict mypy green and failures limited to the new regression.

## Minimal implementation

Change only the shared semantic anchor recovery needed by the reproduced markup:

- when `_SemanticHTMLParser.handle_starttag` receives a new `a` while `_open_link.tag == "a"`, finalize the existing anchor before starting the new one;
- do not model nested HTML anchors with synthetic depth, because nested anchors are invalid HTML and browsers repair them as sibling anchors;
- preserve `_OpenLink.depth` behavior for non-anchor synthetic link-like spans if still required by existing citation handling;
- do not introduce browse-specific raw-HTML parsing or endpoint-specific regex extraction;
- do not weaken fail-closed browse/result checks.

If implementation requires broader shared-parser behavior than this plan, stop and update research/plan before proceeding.

## Focused/full GREEN gate

Run the issue-specific lexicon regressions first, then the complete deterministic repository suite:

```text
ruff check .
ruff format --check .
mypy
pytest
```

All normal checks must remain CAL-independent.

## Bounded live confirmation

After offline GREEN, run one fixed confirmation against:

```text
GET https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22
```

Use the production parser/client with no retries, no traversal, and a one-request hard bound. Confirmation must prove that current live browse parsing returns at least the exact `br N` candidate with CAL provenance/ordering intact. Do not fetch the selected full entry in this confirmation; #15's later capped release smoke owns end-to-end tool confirmation.

Delete any temporary live workflow/helper after execution.

## Independent adversarial review gate

Review the exact final PR head independently from implementation history. Try to falsify:

- that the regression actually contains an unclosed prior anchor and would fail if recovery were removed;
- that the implementation does not silently discard the stale anchor's visible text or merge its href with the next candidate;
- that multiple valid candidate anchors after malformed menu markup are independent and ordered;
- that ordinary valid anchors still behave identically;
- that citation `span.cit-ref-plain` and excluded citation-content logic are not weakened;
- that new-anchor recovery cannot turn malformed non-result pages into false lexical matches;
- that explicit no-match remains explicit;
- that no public schema/request-count behavior changed;
- that live confirmation is one fixed request and normal CI is offline.

Any blocking finding gets a test-first review regression, full GREEN, and a fresh exact-head review.

## Merge/resume gate

Only merge #47 after exact-head CI GREEN, bounded live confirmation, and clean independent review. After merge, resume #15 by synchronizing its release branch with current `main`, re-running exact-head package/offline checks and the capped release smoke before reviewing or publishing anything.
