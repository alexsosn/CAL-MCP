# Issue #175 plan — model lexicon browse cross-references as ordered rows

**Date:** 2026-10-03  
**Research:** `docs/research/issue-175-lexicon-browse-crossrefs.md`  
**Dependency:** #222 merged as `67154f05`; this branch is synchronized with that `main` state before RED.

## Goal

Preserve CAL's current distinction between ordinary lexicon browse entries and arrow
cross-references. A redirect row must expose CAL's displayed left-hand source plus the exact linked
target lemma key without fetching the target and without attaching the source to the target as
`LemmaRef.aliases`.

## Public model

Add a browse-specific ordered row model instead of changing the shared `LemmaRef` semantics.

Each serialized row has an explicit `kind`:

- `entry`: contains one ordinary parsed `lemma` (`LemmaRef`);
- `cross_reference`: contains:
  - `source_text`: CAL's cleaned rendered text to the left of the arrow;
  - `target_lemma_key`: the exact validated lemma key from the sole target link;
  - `target_label`: CAL's cleaned rendered text inside that link.

`LexiconBrowseResult.rows` preserves CAL candidate-row order.

Keep `entries` as a convenience projection containing only genuine ordinary entry rows, in their
relative CAL order. This intentionally fixes the pre-v0.1 semantic bug where redirect targets were
reported as ordinary entries. Do not populate target aliases from arrow source text.

Do not add a target-entry fetch, normalized source form, inferred POS, or inferred headword fields
to cross-reference rows.

## Parser boundary

Classify a candidate line as a cross-reference before parsing the target as a lemma header.

An evidence-backed cross-reference line must have:

1. exactly one rendered arrow `→`;
2. non-empty source text before the arrow;
3. exactly one CAL lemma-entry link after the arrow;
4. a usable target lemma key;
5. non-empty rendered target label;
6. no unrelated rendered text after the target link.

Anything close but structurally different fails closed. In particular, do not treat arbitrary
unlinked text before a normal entry as a redirect merely because a lemma link exists.

Ordinary candidate rows continue through the existing strict `_parse_lemma_header` path and retain
the current gloss-follow-up behavior. The bracketed current header `[šl] (šal) n.m.` remains an
ordinary entry.

The `šlh n.f.?` ordinary header is outside #175's parser scope; #222 now supplies that shared parser support.

## TDD gates

After #222 is merged into `main`, merge/rebase this branch onto that exact main before RED.

### RED

Use reduced structural fixtures derived from the recorded current shapes, with synthetic gloss text
where possible.

Pin at least:

1. ordinary bracketed entry → `kind="entry"`;
2. `šlhˀw → $l)hw N`-shape row → ordered `kind="cross_reference"` with exact source, target
   key and target label;
3. independent `by dny → dn#2 N`-shape redirect whose target falls outside the browse prefix;
4. a redirect target that later also appears as a genuine ordinary entry stays two distinct rows;
5. `entries` contains only ordinary rows and never gains the redirect source as an alias;
6. serialization preserves mixed row order;
7. malformed redirect shapes fail closed:
   - empty source;
   - multiple arrows;
   - zero or multiple lemma targets;
   - target link without a usable lemma key;
   - non-empty trailing rendered content after the target;
8. existing no-match and NEXT PAGE contracts remain unchanged.

The RED must fail against the current flattened parser before production changes.

### GREEN

Implement only the browse-row model and evidence-backed classifier needed by the RED. Avoid changes
to generic lookup/entry parsing beyond shared serialization helpers required for the new row type.

## Documentation / schema

Update:

- `docs/tools/lexicon-browse.md`;
- the server tool docstring/example contract;
- `CHANGELOG.md` / release-surface documentation where browse result semantics are summarized;
- `research.md` only if later implementation evidence materially changes R-060.

Document explicitly that `entries` means ordinary browse entries and `rows` is the authoritative
ordered mixed browse result.

## Validation

1. full offline CI in both repository matrices;
2. bounded installed-wheel/stdio live acceptance after #222:
   - CAL-code `$l`;
   - Syriac-script `ܫܠ`;
   - independent current `by` page;
3. assert at least one typed cross-reference on `$l` and `by`, ordinary entries still present,
   and no redirect source appears as an alias on its target;
4. no NEXT PAGE following or target-entry fetching;
5. remove temporary live workflow and rerun workflow-free CI;
6. fresh logically independent adversarial review of the exact final SHA before merge.

Final live budget: three explicit browse calls, sequential, no continuation or entry follow-up.

## Validation result

Installed-wheel/stdio acceptance run `37220555515` passed on 2026-10-04. The public tool returned
typed mixed rows for `$l`, equivalent Syriac `ܫܠ`, and `by`. The observed row counts were
`48/39/9` (rows/ordinary entries/cross-references) for `$l` and `ܫܠ`, and `48/29/19` for
`by`. Redirect source text remained absent from ordinary-entry aliases.

Because `$l` and `ܫܠ` normalize identically, cache reuse reduced the three explicit MCP calls
to two CAL GETs. No continuation or target-entry fetch occurred. The temporary live workflow was
removed immediately afterward; the remaining gates are workflow-free CI and exact-head adversarial
review.

