# Issue #224 research — current exact entries mark every header field in `div.lemma-header`

**Date:** 2026-10-09  
**Base:** `main` at `c1106aa` (after #227's narrow guard, #156 and #232's research)

## Bounded current CAL evidence

Six GETs of `cal_entry_web.php` were made with the production client, one per header shape. No links
were followed.

| Label | `lemma` | Bytes | Rendered `div.lemma-header` |
| --- | --- | --- | --- |
| noun | `mlk N` | 74317 | `lemma-formal` "mlk, mlkˀ" · `lemma-vocalized` "(mleḵ, malkā)" · `lemma-pos` "n.m." · `lemma-gloss` "king" |
| verb | `)mr V` | 111386 | "ˀmr" · "(a/a)" · "vb." · "to say" |
| adjective | `(hr A` | 31254 | "ˁhr" · "(ˁāhar)" · "adj." · "lustful" |
| verbal noun | `tly N` | 42408 | "tly, tlyˀ" · "(tlāy, tlāyā)" · "v.n." · "suspension" |
| uncertain POS | `$lh N` | 26273 | "šlh" · no vocalized span · "n.f.?" · "watering(?)" |
| no POS | `$yp#2 N` | 26338 | "šyp, šypˀ" · no vocalized span · **no `lemma-pos` span** · "a type of marsh reed" |

In every page there is exactly one `div.lemma-header`, and its only children are those `span`s
separated by whitespace:

- `lemma-formal` and `lemma-gloss` are always present;
- `lemma-vocalized` is optional and always one parenthesized group;
- `lemma-pos` is optional, missing only for `$yp#2 N`.

## Current CAL-MCP behaviour

`parse_lexicon_entry` flattens the page to lines. Since #227, when a `lemma-header` block exists it
parses only that block's line, through the shared POS-token grammar, and fails closed if that does
not work. Consequences:

- the five POS-bearing headers parse correctly, with the same values the structural fields give;
- `$yp#2 N` fails closed, because the grammar requires a POS token, although CAL plainly marks the
  header as having none;
- the grammar can also misread a header if, for example, a headword or gloss token looks like a POS.
  The structural fields cannot be confused that way;
- pages without the block (the older layout seen only in historical reduced fixtures) still use
  the unbounded scan. It can take later prose such as `See DNWSI 17 for other suggestions.` as a
  header (R-061), which is #224's original failure mode.

## Implications

1. When `div.lemma-header` is present, read the fields from its spans:
   - headwords from `lemma-formal`;
   - pronunciation from `lemma-vocalized`, inside its single pair of parentheses;
   - `part_of_speech` from `lemma-pos`, or `null` when that span is absent;
   - gloss from `lemma-gloss`.

   An unknown span or stray text, a duplicate or missing required span, an empty `lemma-pos`, an
   unparenthesized vocalization, or an empty field fails closed.
2. For the older layout without the block, bound the fallback: the header must be the first rendered
   content line. A page whose first line is not a header fails closed instead of scanning on to later
   prose.
3. There is no public schema change: `part_of_speech` is already nullable (#227). Request load is
   unchanged.
