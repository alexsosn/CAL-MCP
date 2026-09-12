# Issue #112 plan — bounded CAL lexicon prefix browsing

**Plan date:** 2026-09-12  
**Research:** `docs/research/issue-112-lexicon-prefix-browse.md`  
**Baseline:** `main` at `2f291988c5557ecd6eaedd90ab2be3403d931b05`

Sequence: research → plan → deterministic RED → minimal implementation → docs/release-surface sync → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen public contract

Add one task-level tool:

```text
cal_lexicon_browse(
  prefix: string,
  representation: InputRepresentation | null = null,
  continuation: string | null = null
)
```

Semantics:

- one explicit **1-character** prefix is CAL's JUMP TO mode;
- **2–3 characters** are CAL's documented typed prefix mode;
- each call returns exactly one CAL browse page;
- `next_continuation` is explicit and caller-controlled;
- no entry page or next browse page is fetched automatically.

`cal_lexicon_lookup` is unchanged.

## Result model

In `src/cal_mcp/lexicon.py` add:

```python
@dataclass(frozen=True, slots=True)
class LexiconBrowseProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    original_prefix: str
    normalized_prefix: str
    representation: str
    conversion_strategy: str
    continuation: str | None = None
@dataclass(frozen=True, slots=True)
class LexiconBrowseResult:
    prefix: str
    normalized_prefix: str
    entries: tuple[LemmaRef, ...]
    next_continuation: str | None
    provenance: LexiconBrowseProvenance
```

`to_dict()` preserves CAL row order and serializes `entries` with existing `_lemma_to_dict()`.

Extend internal `BrowsePage` additively:

```python
next_continuation: str | None = None
```

The default keeps existing constructors/tests source-compatible.

## Parser isolation

Do **not** make exact lookup depend on pagination parsing.

Keep current `parse_browse_page(response)` semantics for `LexiconLookupService`: parse ordered lemma rows / explicit no-match only and ignore navigation as today.

Add a focused public-browse parser, e.g.:

```python
parse_lexicon_browse_page(response) -> BrowsePage
```

It should reuse the same lemma-row extraction helper but additionally parse one canonical `NEXT PAGE` continuation.

This prevents an unrelated navigation-markup change from breaking exact lexical lookup while still making the new browse operation fail closed on its own pagination contract.

## Initial-prefix preparation

Add a private helper returning one unambiguous CAL-code browse prefix plus conversion metadata.

Rules:

1. call `convert_to_cal_code(prefix, representation=representation)`;
2. allow only representations documented by the current browser:
   - `CAL_CODE`
   - `ROMAN_SHARED`
   - `UNICODE_TRANSLITERATION`
   - `HEBREW`
   - `SYRIAC`
3. require exactly one converted word;
4. require exactly one candidate; otherwise raise `AmbiguousQueryError` before transport with guidance to choose one explicit CAL-code candidate via `cal_convert_to_code`;
5. validate the resulting browse prefix as either:
   - 1–3 CAL consonant code characters from the browser's documented alphabet; or
   - one documented bound-form pattern `<CAL consonant>_`;
6. no spaces/multiword input, no empty input, and no arbitrary CAL syntax.

The accepted CAL-code consonant set is the browser table:

```text
) b g d h w z x T y k l m n s ( p P c q r $ & t
```

This deliberately does not broaden the browser to script families CAL does not document on `fullbrowser.html`, even if the generic conversion tool supports them elsewhere.

## Continuation input validation

`continuation` is adapter-owned CAL `sortkey` state, never a URL.

Before transport require:

- `str`, nonempty after no trimming/rewrite;
- length <= 128;
- printable ASCII only;
- no control characters;
- reject URL/query structure delimiters that are not required by the observed sortkey contract: `&`, `=`, `?`, `#`, `/`, `\\`, `:`;
- do not percent-decode/re-encode manually; pass it as one HTTP query value.

The fixed request is always:

```text
GET browseSKEYheaders.php?direction=1&sortkey=<continuation>
```

Callers are documented to pass only `next_continuation` returned by this tool. No public `direction`, path, URL, or arbitrary query fields are accepted.

## NEXT PAGE parser

On the public browse parser, inspect rendered links whose text normalizes case-insensitively to `NEXT PAGE`.

Require zero or one such link. If present:

- resolve relative to `response.url`;
- scheme = `https`;
- host = `cal.huc.edu`;
- exact path = `/browseSKEYheaders.php`;
- no fragment;
- query keys exactly `{direction, sortkey}`;
- `direction == "1"` exactly once;
- one nonempty `sortkey` value;
- parsed `sortkey` passes the same continuation validator before being returned.

Any `NEXT PAGE` label with a wrong route/query fails closed. Multiple `NEXT PAGE` links fail closed even when identical.

Unrelated links, JUMP TO links, entry links, and the page's back/start markers are not pagination controls for this operation.

An explicit CAL no-match page may return `entries=()` only when there is no continuation. No-match plus `NEXT PAGE` is contradictory and fails closed.

## Service

Add `LexiconBrowseService` in `lexicon.py`:

```text
browse(prefix, representation=None, continuation=None)
```

Initial request:

```python
CalRequest(
    method="GET",
    path="browseSKEYheaders.php",
    params=(("first3", f'"{normalized_prefix}"'),),
)
```

Continuation request:

```python
CalRequest(
    method="GET",
    path="browseSKEYheaders.php",
    params=(("direction", "1"), ("sortkey", continuation)),
)
```

Both use `parse_lexicon_browse_page` and one browse cache namespace. One call emits at most one logical CAL request.

The result keeps the original caller prefix and the normalized CAL-code prefix even on continuation calls. Prefix conversion is local and deterministic on every call; it performs no network I/O.

## Server / release surface

In `src/cal_mcp/server.py`:

- import `LexiconBrowseService`;
- add `cal_lexicon_browse` beside `cal_lexicon_lookup`;
- document one-page/explicit-continuation semantics in the tool docstring and server instructions.

In `src/cal_mcp/release_surface.py` add `cal_lexicon_browse`. v0.1 public tool count becomes **34**.

Update release/inventory tests and any documentation that pins the count/name set. Do not add aliases or a second one-letter-specific tool.

## Gate 1 — deterministic RED

Create a focused test module, preferably `tests/test_lexicon_browse.py`, after this plan commit.

RED expectations:

1. current-shaped `br` fixture returns ordered lemma refs without exact filtering;
2. `NEXT PAGE` returns the decoded validated sortkey as `next_continuation`;
3. one-letter `b` and two/three-character initial calls issue exactly one `first3` request with quoted CAL code;
4. Unicode transliteration/Hebrew/Syriac inputs normalize through existing conversion code to the same request shape when unambiguous;
5. an ambiguous Hebrew/Syriac prefix fails locally before transport;
6. unsupported representation, multiword input, zero/too-many browse characters, or arbitrary CAL syntax fails locally;
7. continuation call emits exactly one fixed `direction=1&sortkey=...` request and does not include `first3`;
8. presence of `NEXT PAGE` never causes a second request automatically;
9. wrong-origin/path/query/direction/fragment, empty sortkey, duplicate NEXT links, and invalid continuation syntax fail closed;
10. explicit CAL no-match serializes `entries=[]` and no continuation; unknown empty markup remains `LexiconParseError`;
11. `cal_lexicon_lookup` regression suite remains unchanged/green;
12. normal CI remains offline.

Accepted RED must pass Ruff lint/format and strict mypy; pytest failures must be limited to the absent #112 behavior/surface.

## Gate 2 — minimal implementation

Expected production changes:

- `src/cal_mcp/lexicon.py`
- `src/cal_mcp/server.py`
- `src/cal_mcp/release_surface.py`

No changes to:

- HTTP retry/cache policy;
- lexicon entry parsing;
- exact lookup matching/fan-out behavior;
- arbitrary URL support;
- automatic pagination.

## Gate 3 — docs

Update at least:

- `docs/tools/lexicon.md`: browse vs lookup, 1-char jump vs 2–3-char prefix, explicit continuation, input representations, no auto-expansion;
- `docs/index.md`: capability matrix includes lexicon browsing/discovery;
- release notes/public tool inventory where the current 33-tool count is stated.

Do not claim a single call returns all matching entries. Do not claim continuation values are scholarly CAL identifiers.

## Gate 4 — GREEN

Require deterministic and latest-compatible matrices to pass dependency verification, Ruff lint, Ruff format, strict mypy, full pytest, release-surface equality, docs contracts, and package tests on the exact candidate SHA.

Refetch `main` before review; synchronize if it advanced.

## Gate 5 — logically independent adversarial review

Review the exact GREEN head from current CAL evidence, #112 research/plan, and raw diff. Challenge:

1. whether any call can trigger more than one CAL request;
2. automatic pagination or entry prefetch;
3. ambiguity merging / invented ordering;
4. unsupported representation leakage;
5. arbitrary CAL syntax or URL/query injection through prefix/continuation;
6. canonical NEXT PAGE origin/path/query/direction enforcement;
7. no-match vs parser-drift distinction;
8. preservation of alias/homograph/order semantics;
9. exact lookup isolation/backward compatibility;
10. public schema/tool-count/docs synchronization;
11. normal CI network isolation.

Any blocker gets a focused regression first, then a minimal fix, dual GREEN, and a fresh exact-head review.

## Merge / cleanup

After clean review:

- mark PR ready;
- squash-merge guarded by exact head SHA;
- confirm #112 closes;
- delete or otherwise retire the stale `research/issue-112-prefix-browse` branch so no orphaned duplicate remains.

## CAL load impact

Research used one root browser page, one one-letter browse page, and one explicit continuation. Production stays exactly one browse-page request per explicit call, with zero hidden traversal.