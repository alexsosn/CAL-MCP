# Issue #6 research — bounded CAL concordance and KWIC

**Rechecked:** 2026-09-05

This note records the bounded live evidence used before implementing issue #6. It is a ticket-level research artifact; normal CI remains offline.

## Current CAL workflows

CAL currently exposes three distinct concordance/KWIC paths that should not be collapsed into one implicit crawl.

### 1. Basic single-text concordance

`searching/basic_concordance.html` posts a dialect selector (`R1`) to `/show_files_for_KWIC.php`. That response is a text-selection list. For Old Aramaic (`R1=1`) it currently exposes text links such as:

```text
/newconcord.php?text=13250&cset=S
```

for the Tel Dan Stele.

The selected `newconcord.php` page is not itself a KWIC context list. It is a lemma-frequency index for exactly one text, headed `Frequencies of lemmas in text 13250`. Each row preserves:

- an upstream frequency;
- a CAL lemma key such as `mlk N`;
- a short CAL gloss;
- a link to `/showKWIC.php?...` for that lemma in the selected text.

A bounded Tel Dan probe returned a 7 KB response and 42 linked lemma/frequency rows. The same text IDs are already discoverable through issue #7's text tools, so CAL-MCP does not need to reproduce the preliminary dialect → file-list step as a second public discovery surface.

### 2. Advanced KWIC over explicit text IDs

`searching/concordance_search.html` currently posts to `/showdialectKWIC.php` with:

```text
lemma=<CAL lemma spelling>
pos=<CAL part-of-speech/internal suffix>
texts=<one or more CAL text IDs separated by ASCII spaces>
charset=<R|H|S>
```

CAL's help page explicitly says that multiple text numbers are separated by spaces. A bounded query for `mlk N` across only two short Old Aramaic texts (`12250 13250`) returned per-text sections, including an explicit `no examples found in 12250`, six Tel Dan target hits, and `total examples: 6`.

Each hit links its target coordinate to `get_a_kwicchapter.php` and exposes CAL file/subtext/script parameters in that link. The displayed target row contains the KWIC line context. Duplicate target coordinates can legitimately occur when the requested lemma appears more than once on one line, so CAL-MCP must preserve hit order and duplicates rather than deduplicating by coordinate.

The current explicit empty shape is a successful HTTP 200 page with per-scope `no examples found in ...` plus `total examples: 0`.

### 3. KWIC for one CAL dialect

A lexicon entry's `Complete KWIC concordance` link opens `dKWIC.php?lemma=<CAL lemma key>`. The selector page currently contains hidden lemma/POS values plus a `texts` select whose values are opaque CAL dialect IDs and whose rendered labels are CAL dialect names.

For example, the current `nqr V` selector includes IDs such as `1`, `2`, `3`, `41`, ... with labels including Old Aramaic, Imperial/Official Aramaic, Biblical Aramaic, Palmyrene, Nabataean, Hatran, Qumran, Syriac, Babylonian Talmudic, Mandaic, and others.

Selecting one dialect calls `show1dialectKWIC.php` with the lemma, POS/internal suffix, and dialect ID. A bounded `)ryk#2 A` / Biblical Aramaic (`texts=3`) probe returned exactly one target coordinate and `1 example found`. This result uses the same target-coordinate/full-context link semantics as advanced KWIC.

Because dialect IDs are CAL-owned selectors rather than CAL-MCP identifiers, a public dialect-discovery operation should expose the current ID/label pairs instead of hard-coding a permanent mapping into the adapter.

## The documented `lth` context control is stale in the current form

CAL's concordance help page still documents a `number-of-words` field, maximum 20, and the current page JavaScript still references `lth`. However, the rendered advanced form no longer contains an `lth` control.

A bounded A/B probe sent the same one-hit advanced KWIC request with `lth=1` and `lth=20`. Both responses were exactly 2971 bytes and exposed identical semantic output. CAL-MCP therefore must not advertise a context-window parameter that current CAL appears to ignore.

## Boundedness and continuation

No page number, next-page link, continuation token, or stable result-limit parameter was exposed by the representative current KWIC result pages. The basic single-text concordance is one frequency-index response; advanced and dialect KWIC return their complete current result in one response.

The adapter therefore should:

- perform one upstream request per frequency-index, text-scoped KWIC, dialect-selector, or dialect-KWIC call;
- never iterate result pages or text/dialect combinations automatically;
- cap one text-scoped KWIC call to a small explicit number of caller-supplied text IDs;
- rely on the shared decoded-response safety cap (2 MiB by default) for unexpectedly large complete responses;
- fail with the shared response-size error rather than silently truncate hits;
- expose no fake pagination or ignored `lth` option.

## Input and fidelity implications

- Concordance/KWIC lemma input is the CAL lemma key used by CAL's own links/forms. CAL-MCP should validate it structurally and as CAL code, then preserve the submitted spelling rather than perform linguistic inference.
- Text and dialect IDs are opaque decimal CAL identifiers. Malformed values fail locally; no fallback search is attempted.
- Multi-text order is caller-controlled and should be preserved in the request/provenance. Duplicate text IDs should be rejected locally.
- Basic concordance rendering currently distinguishes `Transliteration` and `Semitic`; advanced KWIC exposes `Roman`, `Hebrew`, and `Syriac` character-set choices. These are rendering choices, not separate lexical analyses.
- KWIC hit count must match CAL's rendered total. Count/link mismatches are parser drift, not partial success.
- Empty results, upstream/network/content failures, and successful-but-unrecognized markup remain distinct.

## Sources

- https://cal.huc.edu/searching/basic_concordance.html
- https://cal.huc.edu/searching/concordance_search.html
- https://cal.huc.edu/searching/help_concordance_search.html
- https://cal.huc.edu/dKWIC.php?lemma=nqr+V
- bounded branch-only result probes described above

## Research load

Four temporary branch-only research runs used ten bounded requests total: three form/selector GETs, two selection/result probes, three final result/empty probes, and two one-hit `lth` comparison requests. No page iteration or corpus traversal was performed. The temporary workflow was deleted before implementation planning.
