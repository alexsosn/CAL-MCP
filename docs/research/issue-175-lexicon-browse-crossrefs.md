# Issue #175 research — browse cross-reference rows are distinct from target entries

**Date:** 2026-10-03  
**Base:** `main` after #208 (`112e9fb`)  
**Related blocker discovered by this research:** #222

## Trigger

Issue #175 was opened after `cal_lexicon_browse("$l")` and the equivalent Syriac-script
prefix failed live. The initial hypothesis was that CAL's arrow rows were a new candidate shape
that the parser could not read.

Current evidence shows two separate problems:

1. arrow rows are already being accepted on many pages, but their semantics are flattened into
   ordinary `LemmaRef` entries by attaching the left-hand spelling as `aliases`;
2. the current `$l` page additionally contains a lemma header with an uncertainty marker,
   `šlh n.f.?`, which the shared lemma-header parser rejects. That independent parser defect is
   tracked in #222 and also occurs on a non-arrow row.

The first problem is #175's cross-reference modeling defect. The second must be repaired before
`$l` can be used as the final live acceptance case for #175.

## Bounded current CAL evidence

All requests were explicit single browse pages. No NEXT PAGE link, lemma-entry link, or other
returned navigation was followed.

### Run 37081675499 — original `$l` shape plus narrow controls

Three GETs were made: `$l`, `$lh`, and `$l)`.

The current `$l` page contains both:

- an ordinary linked header `[šl] (šal) n.m.`; and
- an arrow row whose displayed left-hand form is `šlhˀw` and whose sole lemma link targets
  `lemma="$l)hw N"` with `cits=all`.

The bracketed header is therefore real current CAL markup, not text invented by the earlier
report. The two narrower controls did not expose candidate rows in this probe.

### Run 37081796185 — independent current cross-reference family

Two GETs were made: `b` and `by`.

The current `by` page contains multiple arrow rows. Two directly observed examples are:

- displayed source `by dynˀ` → target lemma key `byt@dyn N`;
- displayed source `by dny` → target lemma key `dn#2 N`.

The target links again use the ordinary CAL `oneentry.php` route with exactly the lemma selector
and `cits=all`. The neighboring `b` page supplied a non-arrow control in the structural probe.

This establishes that cross-reference rows are not a one-off `$l` anomaly and that a redirect may
point to a lemma key outside the lexical prefix that selected the browse page.

### Run 37081866587 — current parser applied to every candidate link

Two GETs were made: `$l` and `by`. This probe installed the current repository and ran the same
`_parse_lines`, `_parse_lemma_header`, and `parse_browse_page` code used by CAL-MCP.

Results:

- `parse_browse_page(by)` succeeds and currently returns 48 flattened entries despite many arrow
  rows;
- the bracketed `[šl] (šal) n.m.` header parses successfully;
- observed arrow targets such as `$l)hw N`, `$lwh N`, `$lb$ V`, and the independent `by`
  targets parse successfully as lemma headers;
- `parse_browse_page($l)` fails because `$lh N` is displayed as `šlh n.f.?`; that linked
  header fails `_parse_lemma_header`;
- the same `$lh N` / `n.f.?` shape occurs once with an arrow before it and once as an ordinary
  entry, so treating arrow rows separately cannot by itself make `$l` succeed.

Issue #222 owns the uncertain-POS parser boundary and is now merged into this branch. #175 should not widen POS parsing as an incidental side effect.

Total research load across the three runs: **7 explicit GETs** (3 + 2 + 2). Repeated `$l` / `by`
requests were deliberate parser-validation controls. There was no pagination or link traversal.

## Current implementation mismatch

`parse_browse_page` currently treats every `oneentry.php`/entry link as an ordinary candidate.
When text before the link contains an arrow, it takes the left-hand text, splits it on commas, and
stores those strings in `LemmaRef.aliases`. It then appends the linked target as a normal
`LemmaRef` to `BrowsePage.entries`.

That loses the upstream row type:

- callers cannot tell that CAL rendered a redirect rather than an entry;
- the left-hand displayed form is semantically attached to the target lemma as if CAL had declared
  it an alias on the target entry;
- a target outside the requested browse prefix appears as though it were an ordinary result for
  that prefix;
- the target can later appear again as a genuine ordinary entry, with no way to distinguish the
  two occurrences.

No additional request is needed to model the row correctly. The browse page already provides both
the displayed source text and the exact linked target lemma key.

## Evidence-backed cross-reference boundary

The sampled current arrow rows have this shape:

1. non-empty rendered text before exactly one arrow;
2. exactly one linked CAL lemma target after the arrow;
3. the target link uses CAL's normal lemma-entry route and carries a usable `lemma` key;
4. no automatic follow-up to the target entry is necessary.

A candidate with an arrow but missing the source text, with multiple arrows, with no usable target
key, with multiple target links, or with unrelated loose content must fail closed rather than be
reclassified heuristically.

The displayed source should be preserved as CAL rendered it after the repository's normal
whitespace cleanup. It should not be normalized into CAL code or split into invented lexical
fields unless separate evidence supports that transformation.

## Public-model implication

Cross-references need a browse-specific typed representation rather than `LemmaRef.aliases`.
The public result must expose at least:

- that the row is a cross-reference;
- CAL's displayed left-hand source text;
- the exact target `lemma_key` from the validated link.

The linked target header can be preserved as already-rendered target metadata without fetching the
entry, but the source text must not become an alias on that target.

Because ordinary entries and redirects are interleaved on current pages, the implementation plan
must preserve CAL row order. A browse-specific ordered row/item model is preferable to two
unordered projections that cannot reconstruct the original sequence. If compatibility projections
such as `entries` are retained, their semantics must be explicit and must not silently claim that
redirect rows are ordinary entries.

## Dependency on #222

#222 was merged before #175 RED. The cross-reference row contract therefore builds on the shared
support for the current uncertain `n.f.?` lemma-header shape, without changing that grammar here.

## Final installed-stdio acceptance

**Run 37220555515 — 2026-10-04.**

The candidate was installed from the branch and exercised through the public stdio MCP surface with
three explicit `cal_lexicon_browse` calls:

1. CAL-code `$l`;
2. Syriac `ܫܠ`;
3. CAL-code `by`.

The first two normalize to the same CAL browse request, so the client's completed-request cache
reused the `$l` response for the Syriac spelling. The three MCP calls therefore produced exactly
two CAL GETs: one `$l` page and one `by` page. No continuation or lemma-entry link was followed.

Observed public results:

- `$l`: 48 ordered rows = 39 ordinary entries + 9 cross-references;
- `ܫܠ`: the same 48/39/9 result and the expected `$l)hw N` cross-reference;
- `by`: 48 ordered rows = 29 ordinary entries + 19 cross-references;
- the researched `šlhˀw → $l)hw N` and `by dny → dn#2 N` rows were present;
- redirect source text did not leak into any ordinary entry's `aliases`.

This confirms the typed-row model on current CAL data while keeping upstream request volume below
the planned three-request ceiling.

