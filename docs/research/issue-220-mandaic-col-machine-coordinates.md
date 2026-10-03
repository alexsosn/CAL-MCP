# Research — issue #220: machine coordinates for Mandaic 74421/col

**Issue:** #220  
**Rechecked:** 2026-10-02  
**Scope:** the exact machine-coordinate identity used by the current `74421/col` text page.

## Trigger

Final installed-stdio acceptance for #188 successfully discovered `74421/col` through the
current child catalogue and sent the correct page request:

```text
GET get_a_chapter.php?cset=M&file=74421&sub=col
```

CAL returned HTTP 200, but CAL-MCP failed closed with `CAL returned an invalid machine
coordinate`. That separates this issue from #188's selector-routing repair.

## Bounded live probe

GitHub Actions run: `37062928691` (2026-10-02).

The probe used exactly **3 sequential GETs**:

1. `74421/col` page 1;
2. numeric control `74421/103` page 1;
3. one token-analysis follow-up using a coordinate returned by the `col` page.

No pagination, recursive catalogue traversal, or result expansion was performed.

### 74421/col

Current page identity:

- file-information coordinate: `74421col`;
- 1,102 token links;
- 147 unique token machine coordinates;
- all 147 unique coordinates have the exact shape
  **`74421col` + non-empty decimal tail**;
- examples: `74421col13614`, `74421col13615`, …;
- current comment coordinates use the same literal prefix, e.g.
  `74421col13830`, `74421col13835`.

The observed coordinate character set contains only decimal digits plus the literal letters
`c`, `o`, `l`.

### Numeric control 74421/103

The control page keeps the ordinary composition:

- file-information coordinate: `74421103`;
- sampled token coordinates such as `7442110313604`;
- all sampled unique token coordinates satisfy the existing generic decimal grammar.

Thus the special shape belongs to the literal `col` subtext identity, not to file `74421`
as a whole.

### Token-analysis follow-up

The probe followed the first non-generic returned token exactly:

```text
GET getlex.php?coord=74421col13614&word=0
```

CAL returned HTTP 200 with its normal analysis marker and a linked lemma route. The literal
`col` segment is therefore part of CAL's actual opaque machine-coordinate handle and must be
preserved for follow-up.

## Current implementation mismatch

The #188 page-routing work already accepts `subtext_id="col"` only for known subdivided
Mandaic files and composes the correct request.

During parsing, `has_subtext_letter_suffix("col")` causes the exact expected coordinate prefix
to become `74421col`, which is desirable. The failure occurs one layer later:
`_parse_text_machine_coordinate` applies the shared generic machine-coordinate predicate, which
supports decimal coordinates and the researched single embedded-lowercase-letter CPA/Syriac
shape but not a literal three-letter segment.

The #218 special-Mandaic predicate already provides a deliberately non-generic extension point
for exact observed Mandaic coordinate families. Extending that predicate with
`^74421col[0-9]+$` is narrower than widening the shared generic grammar.

## Narrow compatibility boundary

Evidence supports exactly:

```text
74421col + one or more decimal digits
```

for text/token/comment machine coordinates on `74421/col`.

Do not accept:

- `74421col` without a decimal tail;
- another literal word/suffix;
- `col` coordinates under another file id;
- uppercase/mixed-case variants;
- punctuation or whitespace;
- a generic arbitrary multi-letter coordinate grammar.

Numeric `74421` subtexts continue through the existing generic coordinate rules.

For text-page parsing, the special branch should key on the exact expected coordinate prefix
`74421col`, while the existing #218 exact direct-file prefixes `74425` and `74429` remain
unchanged. For `cal_token_analysis`, the same special Mandaic predicate can recognize the exact
`74421col` family from the coordinate alone.

## Request accounting

Research used exactly 3 bounded GETs. The preceding #188 acceptance stopped on this page after
18 sequential logical calls; it did not continue to text-information or token-analysis once the
parser failed.

## Final installed-stdio acceptance

Run `37066174460` rebuilt and installed the candidate, then exercised exactly three sequential
public MCP calls:

1. `cal_text_page(file_id="74421", subtext_id="col", page=1)` returned current CAL page data and
   preserved token coordinate `74421col13614`;
2. `cal_token_analysis(coordinate="74421col13614", word_index=0)` followed that exact returned
   handle and CAL returned a recognized analysis result;
3. `cal_text_page(file_id="74421", subtext_id="103", page=1)` remained on the ordinary decimal
   machine-coordinate path.

All three upstream requests returned HTTP 200. No pagination, recursive catalogue traversal,
neighbor-token analysis, or additional result expansion occurred.

