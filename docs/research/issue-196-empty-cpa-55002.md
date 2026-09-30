# Issue #196 research — current CPA 55002 explicit no-lines state

Date: 2026-09-29. Base: `3c788e0f`.

## Trigger

Current category-55 catalogue still exposes direct Christian Palestinian Aramaic file `55002`
as “CCR NT Stuff” via the exact route:

```text
get_a_chapter.php?file=55002&cset=C
```

During #185, its text page no longer reproduced the earlier linkless-content observation. The
current `text-display` shell contains no scholarly text. Issue #196 separated that state from
plain/unlemmatized rows so the adapter would not manufacture an empty text line.

## Bounded live research

All probes used fixed URLs with hard response caps, no crawl, no token/comment traversal and no
corpus retention beyond parser-relevant labels/selectors.

### Upstream state — run 36593879932

Five fixed GETs checked the category, metadata, and page variants:

- `showsubtexts.php?subtext=55` still contains
  `get_a_chapter.php?file=55002&cset=C`, label “CCR NT Stuff”;
- `get_a_chapter.php?file=55002&cset=C`;
- the same route with `page=0`;
- the same route with `page=1`;
- `get_file_info.php?coord=55002`.

All three page forms return HTTP 200 and explicitly render:

```text
NO LINES FOR 55002 ARE CURRENTLY STORED
```

No page form contains non-empty scholarly text or lexical token links. File information remains
available. Thus the current upstream semantics are explicit “no lines stored”, not a successful
empty text and not an alternate page selector.

### Public MCP control — run 36594031060

An installed-wheel stdio call:

```text
cal_text_page(file_id="55002", page=1)
```

reached the correct current route and HTTP 200 but failed with:

```text
parser_drift: CAL text page contains no recognizable coordinate/token rows
```

So the existing intended no-lines → `not_found` mapping is not recognizing the current markup.

### Production semantic-line probe — run 36594232550

The shared production `_parse_lines` returned nine semantic lines. The relevant current line is:

```text
Hide manuscript variantsNO LINES FOR 55002 ARE CURRENTLY STORED
```

The current generic regex

```text
\bNO LINES FOR\b.*\bARE CURRENTLY STORED\b
```

does not match because `NO` is immediately adjacent to the preceding link label
`variants`, so there is no word boundary.

### Exact inline link shape — run 36594358989

The same semantic line contains exactly one link before the marker:

- rendered text: `Hide manuscript variants`;
- path: `get_a_chapter.php`;
- exact selectors: `cset,file,sub,variants`;
- values:
  - `cset=C`;
  - `file=55002`;
  - `sub=` (empty);
  - `variants=0`.

The marker itself is unlinked.

## Existing compatibility evidence

The repository already has `tests/fixtures/cal/text_page_missing.html`, captured 2026-09-04,
whose exact no-lines text is:

```text
NO LINES FOR 13250 999 ARE CURRENTLY STORED
```

That older shape currently maps to `TextPageStatus.NOT_FOUND` and must stay green.

Therefore the marker grammar must continue to allow CAL's optional second decimal selector after
the file id, while the current CPA form has only the file id.

## Parser design

Do **not** loosen the marker regex to allow arbitrary prefix text.

Instead inspect each semantic line independently:

1. derive a residue by removing each rendered link text from `line.text` exactly once, then
   normalize whitespace;
2. recognize only an exact no-lines residue of the form:

```text
NO LINES FOR <decimal file_id> [<decimal selector>] ARE CURRENTLY STORED
```

3. require at most one recognized no-lines marker line;
4. require the marker's `file_id` to equal the requested file;
5. when a requested/submitted decimal subtext is present and the marker includes a selector, require
   semantic agreement rather than silently accepting another subtext;
6. any malformed near-marker remains normal parser drift rather than being treated as
   `not_found`.

Link removal is structural normalization only. The presence of an arbitrary link does not itself
prove a no-lines state; the exact residual marker does.

For current `55002`, the existing manuscript-variant toggle disappears from the residue and the
exact marker becomes visible.

## Representation

No new public result type is needed. Current explicit no-lines pages use the already-established
contract:

```json
{"status": "not_found", "page": null}
```

The text remains discoverable in the catalogue because CAL itself lists it; retrieval truthfully
reports that CAL currently stores no lines.

## TDD boundary

RED should cover:

- current CPA inline-toggle + `NO LINES FOR 55002 ARE CURRENTLY STORED` → parser returns
  `None` / service returns `not_found`;
- legacy `NO LINES FOR 13250 999...` remains `not_found`;
- wrong file id in an otherwise exact marker fails closed;
- arbitrary prefix text not represented by links fails closed;
- malformed/repeated marker lines fail closed;
- a normal found page remains unchanged.

## Request/data impact

No production request changes. One explicit `cal_text_page` call remains one logical CAL request.
No links are followed automatically.

## Final installed-stdio acceptance

Run `36715432418` rebuilt and installed the integrated candidate and made exactly one public MCP
call:

```text
cal_text_page(file_id="55002", page=1)
```

The installed server made one HTTP 200 request to
`get_a_chapter.php?file=55002&cset=C&page=0` and returned structured
`status=not_found`, `page=null`. No text, token, comment, metadata, or navigation link was
followed. The temporary workflow was removed immediately after the successful run.

