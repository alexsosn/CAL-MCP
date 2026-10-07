# Issue #155 research — CAL repeats verse labels inside MT script spans

**Date:** 2026-10-08  
**Base:** `main` after #175 (`f0e87571`)  
**Release impact:** blocks v0.1 issue #15 because the current parsers return silently corrupted
`mt_text`.

## Trigger

The public Targum and Peshitta parallel tools collect every rendered data node inside CAL's Hebrew
script span and normalize the result to one string. Current CAL repeats the biblical coordinate at
the end of each displayed MT line *inside that same Hebrew span*. The coordinate therefore becomes
part of `mt_text`; where a `<br>` separates two lines, the Targum parser can also glue the first
coordinate directly to the next Hebrew word because it does not preserve the break.

This is upstream presentation metadata, not Hebrew MT content.

## Current evidence

### Fresh public CAL recheck — 2026-10-08

Current indexed CAL pages still expose the same visible convention:

- `https://cal.huc.edu/showpesh.php` for Gen 1:1 renders two MT lines and appends `Gen 1:1`
  after each line.
- current `showtargum.php?Peshitta=ON&Sam=ON&bookname=08&chapter=01&verse=10` renders two MT
  lines and appends `Sam1 1:10` after each line.
- a current Babylonian-pointing Targum page for Gen 1:2 uses the same repeated-coordinate
  convention on every MT display line.

These pages were rechecked through CAL's current public web surface/search index. No result links,
chapters, neighboring verses, or corpus pages were followed.

### Retained current-markup fixtures

The repository already contains reduced current fixtures captured from CAL on 2026-09-25:

- `tests/fixtures/cal/targum_parallel_ps_23_1_current.html`;
- `tests/fixtures/cal/syriac_peshitta_ps_23_1_current.html`.

They show the structural boundary that the rendered current pages alone do not expose:

```html
<span class="heb">... MT words ... Ps 23:1<br></span>
```

The existing Gen 1:1 Peshitta fixture additionally preserves a multi-line current shape:

```html
<span class="heb">
  ... first MT line ... Gen 1:1<br>
  ... second MT line ... Gen 1:1<br>
</span>
```

Thus the coordinate text is inside the semantic Hebrew span, but each display line ends at a
`<br>`.

### Historical clean compatibility shape

The older reduced Targum Gen 1:1 fixture has a Hebrew MT span with no repeated coordinate and no
embedded line label. That shape is already part of the offline compatibility contract and should
remain valid unless contrary current evidence appears.

## Current implementation cause

### Targum

`_ParallelParser` appends all data inside `span.heb` / `span.syr` to
`_ParallelBlock.text_parts`, but it does not record `<br>` while inside the script span.
`parse_targum_parallel_page` then computes:

```python
mt_text = _clean_text("".join(mt_block.text_parts))
```

Consequences:

- repeated coordinate labels remain in `mt_text`;
- a line break contributes no whitespace, so `Gen 1:1<br>ו...` can become
  `Gen 1:1ו...` before whitespace normalization.

### Peshitta

`_PeshittaParser` does notice `<br>` inside a script span, but converts it immediately to one
ordinary space. `parse_syriac_peshitta_page` then joins all Hebrew parts and cannot distinguish
verse labels from text.

## Evidence-backed semantic boundary

The safe discriminator is not a global `Gen 1:1` regex and not deletion of arbitrary Latin text.

For a successful requested parallel page:

1. the page already supplies one identifying heading;
2. that heading is already validated against the requested book/chapter/verse using
   `cal_biblical_heading_matches`;
3. the suffix after the route-specific heading prefix is CAL's own displayed coordinate label
   (for example `Gen 1:1`, `Ps 23:1`, or `Sam1 1:10`);
4. current labeled MT display lines end with exactly that validated coordinate;
5. `<br>` is the current line boundary.

Therefore the parser can preserve script-span line boundaries internally and remove only an exact
validated heading-coordinate suffix at the end of a complete MT display line.

Fail closed when coordinate-like presentation metadata is contradictory or only partly removable:
mixed labeled/unlabeled current lines, a different trailing coordinate, or coordinate text embedded
inside a line must not be silently concatenated into MT.

## Public-model decision

Do **not** add a public `mt_lines` field in this ticket.

The observed `<br>` segments all identify the same requested verse and serve as display wrapping;
CAL does not expose separate verse identities or other line-level scholarly metadata here. The
existing public semantic value is the verse's MT text, so the faithful backward-compatible repair
is to return that text without the repeated display coordinate.

The line segmentation remains an internal parser boundary used to distinguish MT content from CAL
presentation metadata.

## Compatibility and scope

- Keep current clean/legacy MT spans valid when they contain no coordinate-like suffixes.
- Preserve Hebrew text exactly apart from the repository's existing whitespace normalization.
- Do not normalize vocalization, punctuation, word spelling, or script.
- Do not change Targum source readings, Peshitta Syriac text, chapter links, request parameters, or
  public schemas.
- No extra CAL request is required in production.

## Request-load note

The fresh evidence above came from current public CAL pages/indexed renderings; no navigation was
followed. A branch-only GitHub Actions probe was also queued for the same two fixed endpoints but
had not obtained a runner while this research record was prepared. It is not required for the
design because the current public renderings and retained DOM fixtures agree on the same boundary.
