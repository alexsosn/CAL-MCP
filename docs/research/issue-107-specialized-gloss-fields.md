# Issue #107 research — CAL specialized gloss-field search

**Rechecked:** 2026-09-08
**Baseline:** `main` at `591d80cef54187efdbf74fdb5fbaaa21c8f108e1`

This research rechecks CAL's current human-facing **Search by Specialized Field** workflow and the existing CAL-MCP English-gloss adapter. It does not enumerate result sets across fields.

## Current CAL workflow

Current entry page:

```text
https://cal.huc.edu/searching/englishnew.html
```

CAL distinguishes ordinary English-gloss search from a separate **Search by Specialized Field** section. The current ordered choices are:

1. alchemy
2. anatomy
3. architecture
4. astronomy
5. botany, flora
6. cantillation
7. chemistry
8. geography
9. geology, gemology
10. geometry
11. grammar
12. liturgy
13. logic
14. magic
15. mathematics
16. medicine
17. music
18. philosophy
19. topography
20. zoology, fauna

These links do not submit the visible field label as an ordinary gloss query. They call `newsearchmngs.php` with a private leading-parenthesis prefix token and `secondary=true`.

Current link mapping, rechecked from CAL's rendered field links:

| Public slug | CAL label | Private `English` token |
| --- | --- | --- |
| `alchemy` | alchemy | `(alchem` |
| `anatomy` | anatomy | `(anat` |
| `architecture` | architecture | `(arch` |
| `astronomy` | astronomy | `(astron` |
| `botany` | botany, flora | `(bot` |
| `cantillation` | cantillation | `(cantill` |
| `chemistry` | chemistry | `(chem` |
| `geography` | geography | `(geog` |
| `geology` | geology, gemology | `(geol` |
| `geometry` | geometry | `(geom` |
| `grammar` | grammar | `(gram` |
| `liturgy` | liturgy | `(liturg` |
| `logic` | logic | `(logic` |
| `magic` | magic | `(magic` |
| `mathematics` | mathematics | `(math` |
| `medicine` | medicine | `(med` |
| `music` | music | `(music` |
| `philosophy` | philosophy | `(philos` |
| `topography` | topography | `(topog` |
| `zoology` | zoology, fauna | `(zool` |

The private token is CAL indexing syntax, not a meaningful free-text synonym expansion. For example, selecting **alchemy** currently navigates to:

```text
newsearchmngs.php?English=(alchem&secondary=true
```

while selecting **anatomy** uses `(anat` and **astronomy** uses `(astron`.

## Why generic `cal_gloss_search("alchemy")` is not equivalent

`cal_gloss_search(query, all_glosses=...)` currently sends the caller's literal English query to `newsearchmngs.php`. CAL's specialized-field links instead submit a parenthesized indexing prefix and force secondary-gloss search.

Therefore a caller who knows only the human label `alchemy` cannot reproduce CAL's field workflow faithfully without knowing the private `(alchem` token. Passing the display word as ordinary free text is a different CAL query.

The missing capability is selector/discoverability, not result parsing.

## Result semantics and parser reuse

Representative current field results for alchemy, anatomy, and astronomy render the same lemma-list structure consumed by `parse_gloss_search_page()`:

- ordered CAL lemma/headword links;
- rendered pronunciation/POS/gloss metadata through the shared lexicon browse parser;
- no second result-page family specific to fields was observed.

`EnglishSearchService.search_gloss()` already separates transport from `parse_gloss_search_page()`, so a field operation can reuse the existing parser while using a distinct public selector and provenance kind.

The existing explicit gloss empty marker and parser-drift semantics should remain shared. An unknown public field should fail locally before any CAL request rather than becoming a literal English query or guessed prefix.

## Public-contract choice

Do not overload the existing required `query` parameter with a mutually exclusive field mode and do not make callers supply a dummy query.

Add one bounded task-level operation:

```text
cal_gloss_field(field: GlossField)
```

where `GlossField` is a string enum with the 20 readable slugs above. The enum itself makes the supported field vocabulary discoverable through the MCP schema; user docs also list labels and slugs.

This is preferable to:

- exposing raw `(alchem`-style tokens;
- guessing field intent inside ordinary `cal_gloss_search`;
- adding a separate network discovery call for a small current controlled vocabulary;
- adding both a discovery tool and a search tool when the enum schema already carries the choices.

## Result model

Use a dedicated result wrapper because `GlossSearchResult.all_glosses` describes ordinary primary-vs-all-gloss search, whereas a specialized-field selection is a different CAL research task.

Proposed result:

```text
field: <readable slug>
label: <current CAL human label>
matches: <ordered existing LemmaRef values>
provenance:
  source: CAL
  source_url: actual field-result URL
  retrieved_at: actual retrieval time
  original_query: readable field slug
  submitted_query: private current CAL field token
  search_kind: gloss_field
```

The private token may appear in provenance as the actual submitted CAL semantics, but it is never accepted as a public selector.

## Request shape and bound

One explicit field search performs exactly one bounded request:

```text
GET /newsearchmngs.php
English=<mapped private token>
secondary=true
```

CAL's field navigation uses GET links, so the adapter should preserve that current method rather than route the field through the ordinary POST merely because the parser is shared.

No field expands to multiple queries, no result links are followed, and no all-fields operation enumerates results.

## Drift boundary

The 20-value mapping is current upstream navigation metadata. If CAL changes a private token, a live result may drift and the focused live-smoke/research process can update the mapping; normal CI remains deterministic/offline.

Tests should pin at least:

- an early field (`alchemy` -> `(alchem`);
- a middle field with a nontrivial display synonym (`geology` -> label `geology, gemology`, token `(geol`);
- a late field (`zoology` -> label `zoology, fauna`, token `(zool`);
- exact one-request GET semantics;
- result parser reuse and order;
- enum/local rejection of unsupported values through the public/server schema.

## Sources

Rechecked 2026-09-08:

- https://cal.huc.edu/searching/englishnew.html
- current field links from that page to `newsearchmngs.php`
- representative current field results for alchemy, anatomy, astronomy
- `src/cal_mcp/search.py` on the baseline above
- issue #103 reachability audit / issue #107 decomposition

## CAL load impact

The research read the field-navigation page and inspected a tiny set of representative field result pages/links. It did not execute all twenty result sets as an automated corpus/query sweep. Production remains one CAL request per explicitly selected field.