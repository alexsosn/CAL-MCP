# Issue #188 research — Mandaic subdivisions are subtexts; page is a separate axis

Date: 2026-10-01. Base: current `main` after #172.

## Trigger

Issue #188 was opened after the Mandaic catalogue → text path showed two visible failures:

- current direct Mandaic texts such as `74501` are paginated, while the adapter allowed only
  `page=1`;
- some subdivided files use unpadded `sub` selectors, while the adapter synthesized
  `sub=f"{page:03d}"`.

The issue inherited an older architecture from #85/#97: for allowlisted subdivided Mandaic files,
public `page=N` was assumed to mean upstream `sub=NNN`.

The current bounded audit shows that assumption is false.

## Bounded current CAL audit

All research was done through fixed GETs in temporary read-only GitHub Actions workflows. No token,
comment, or returned navigation link was recursively followed.

### 1. Current top-level Mandaic catalogue — run 36833045405

`show_Mandaic.php?R1=74` currently exposes exactly 20 routed texts.

Direct `get_a_chapter.php` routes:

```text
74420 74424 74425 74426 74427 74429 74431 74501
```

Subdivided `showsubtexts.php` routes:

```text
74401 74402 74410 74411 74421 74422
74423 74428 74430 74432 74701 74923
```

The current top-level catalogue uses `cset=R`; that selector is a rendering choice, not the
subdivision identity.

### 2. Current child-selector audit — runs 36833179202 and 36833408756

The 12 current subdivided files expose real CAL `sub` identifiers whose format varies by file:

| file | current child selectors |
| --- | --- |
| 74401 | `11, 12, 23, 24, 25, 26, 27` |
| 74402 | `001..281` |
| 74410 | `001..395` |
| 74411 | `001..138` |
| 74421 | `000..103`, then `col` |
| 74422 | `106..170` |
| 74423 | `001..137` |
| 74428 | `1..5` |
| 74430 | `1..5` |
| 74432 | `170..178` |
| 74701 | `001..094` |
| 74923 | `1..5` |

This rules out a per-file zero-padding fix as the public abstraction:

- selectors can be sparse (`74401`);
- selectors can start far above one (`74422`, `74432`);
- one current selector is non-decimal (`74421/col`).

### 3. `sub` and `page` are independent axes — runs 36833777031 and 36834697908

A page requested as:

```text
get_a_chapter.php?cset=M&file=74401&sub=12&page=1
```

is explicitly **Page 2 of 20** for subtext `12`. Its previous/next links preserve
`file=74401&sub=12&cset=M` and change the private zero-based `page` selector:

- previous: `page=0&clen=5`;
- next: `page=2&clen=5`.

The file-information coordinate is `7440112` and the label is
`74401: ATS book 1 part 2`.

Thus `sub=12` is a subtext identity; `page` is pagination *inside that subtext*.

The same audit requested direct `74501` with `page=1`. CAL returned **Page 2 of 11** with:

- file-information coordinate `74501`;
- previous/next links whose `sub` is empty;
- private zero-based `page=0/2`;
- `clen=5`.

Direct Mandaic pagination therefore uses the ordinary page axis, not a fabricated subtext.

### 4. Subtext discovery is already available — run 36834697908

A bounded GET of:

```text
showsubtexts.php?subtext=74401
```

with no private script selector returns the seven real children as
`get_a_chapter.php?file=74401&sub=<id>&cset=J`, with labels such as:

- `11` — ATS book 1 part 1;
- `12` — ATS book 1 part 2;
- `23` — ATS book 2 part 3.

Their information coordinates are the composed file+sub identities (`7440111`, `7440112`,
`7440123`, ...).

So CAL-MCP can expose the upstream subdivision explicitly through its existing
`cal_text_catalogue(category_id=...)` surface. No runtime route-probing request is needed before
`cal_text_page`.

### 5. Legacy hidden Mandaic routes — run 36833702928

Four IDs remain in the adapter's private subdivided allowlist but are absent from the current
top-level 20-row catalogue. They must not all be deleted:

- `74700`: still exposes `001..289`;
- `74702`: still exposes `01..20`;
- `74714`: still exposes `01..05`;
- `74711`: HTTP 200 child catalogue but currently zero child routes.

Legacy direct `74717` remains directly reachable and currently exposes no pagination.

The allowlist remains useful as route-kind compatibility metadata, but it must no longer mean
“synthesize a page-number sub selector.”

## Superseded earlier assumptions

The following earlier claims are superseded by the 2026-10-01 live evidence:

- #85 / `docs/research/issue-85-mandaic-text-page-route.md`: “Mandaic `sub=NNN` is the displayed
  page selector”;
- #97 / `docs/research/issue-97-mandaic-route-scope.md`: public `page=1` → `sub=001` for an
  allowlisted subdivided Mandaic file.

Those implementations restored specific Ginza routes but collapsed two upstream axes.

The route-kind result from #97 remains valid: a file cannot be classified as direct/subdivided by
the `74` prefix alone, so the evidence-backed private allowlist remains appropriate.

## Correct public composition

### Top-level Mandaic catalogue

`cal_text_catalogue("74")` should distinguish:

- current direct routes → `texts` / `TextRef`;
- current `showsubtexts.php` routes → `categories` / `TextCategoryRef`.

A caller follows a returned Mandaic category with the existing
`cal_text_catalogue(category_id=<file>)` operation.

### Mandaic child catalogue

A Mandaic child route becomes a `TextRef` whose:

- `file_id` is the parent file;
- `subtext_id` is CAL's exact returned `sub`, including leading zeroes or the current literal
  `col`;
- label is CAL's rendered child label.

The Mandaic-only grammar may accept `col`; the global/CPA subtext grammar must remain unchanged.

### Subdivided Mandaic page

A known subdivided Mandaic file requires an explicit `subtext_id`.

- page 1: `cset=M&file=<file>&sub=<exact sub>`;
- page N>1: same selectors plus zero-based `page=N-1`.

Returned previous/next links must preserve the exact file, subtext and `cset=M`. The current
private paginated form may carry `clen=5`. Ordinary page markers provide the real one-based page
number/count; no page number is synthesized from `sub`.

### Direct Mandaic page

All eight current direct top-level files support page 1 with the evidence-backed direct request
`cset=M&file=<file>`. Public `page>1` is enabled only for files whose pagination semantics have
been independently observed. Current evidence supports exactly `74501`:

- `74501` page N>1 adds zero-based `page=N-1`;
- its current pagination links preserve the file, `cset=M`, empty `sub`, and may carry `clen=5`;
- `74420`, `74424`, `74425`, `74426`, `74427`, `74429`, and `74431` remain
  page-1-only until new file-specific evidence is researched.

Legacy/unknown direct collection-74 files are likewise not assumed paginated merely from their
prefix. Current hidden `74717` remains page-1-only until live evidence says otherwise.

## TDD boundary

RED should cover at minimum:

1. top-level current Mandaic catalogue returns 12 categories and 8 direct texts, not 20 flattened
   text refs;
2. a Mandaic text-search `showsubtexts.php` result follows `cal_text_catalogue`, not
   `cal_text_page`;
3. child catalogue preserves sparse/offset/unpadded selectors and accepts only the Mandaic-specific
   `col` extension;
4. known subdivided Mandaic text without `subtext_id` fails locally;
5. `74401/12` and `74430/1` send the exact `sub`;
6. page 2 of a selected subtext sends `page=1` while keeping `sub`;
7. direct `74501` page 2 sends `page=1` and parses current navigation;
8. legacy hidden `74700`, `74702`, `74714`, and empty-child `74711` stay classified as
   subdivided, never silently reclassified as direct;
9. CPA and ordinary non-Mandaic subtext validation is unchanged.

## Request/data impact

A single explicit `cal_text_page` remains exactly one logical CAL request. The correction moves
subtext discovery into an explicit catalogue call chosen by the caller; page retrieval does not
probe the catalogue first and no recursion/prefetch is introduced.

## Final installed-stdio acceptance after #218 and #220 integration

Run `37066477577` rebuilt and installed the combined candidate and completed exactly **20**
sequential public MCP calls:

- category `74` returned the current 12 subdivided categories and 8 direct texts;
- page 1 opened for all eight current direct texts;
- direct `74501` page 2 opened successfully;
- child-catalogue → page round-trips succeeded for `74401/12`, `74422/106`,
  `74430/1`, and `74421/col`;
- the merged `74421/col` page preserved an exact `74421col<decimal-tail>` token coordinate;
- `cal_text_information("74421", subtext_id="col")` preserved that text identity;
- `cal_token_analysis` followed the returned direct-Mandaic coordinate `7442500a/0`.

Every upstream request returned HTTP 200. No recursive catalogue expansion, hidden pagination,
neighbor-token analysis, or result expansion was performed.

This acceptance validates the full current catalogue → selected child/page composition. A separate
adversarial-review check still audits which individual direct files have evidence for `page>1`;
page-1 readability alone is not treated as proof of pagination.

## Adversarial direct-page audit — only 74501 has current pagination evidence

Run `37066672702` (2026-10-02) installed the candidate and made exactly one
`cal_text_page(file_id=<id>, page=2)` call for each of the eight current direct Mandaic files.

Observed adapter results from current CAL:

| file | page-2 result |
| --- | --- |
| `74420` | found, 46 lines; no page count, total, previous, or next |
| `74424` | parser drift |
| `74425` | found, 654 lines; no pagination metadata/navigation |
| `74426` | found, 596 lines; no pagination metadata/navigation |
| `74427` | parser drift |
| `74429` | found, 412 lines; no pagination metadata/navigation |
| `74431` | found, 1008 lines; no pagination metadata/navigation |
| `74501` | genuine Page 2 of 11; total 246 lines; previous 1; next 3 |

The five metadata-free `found` results do **not** establish pagination. Production had set
`page_number=requested_page` for a Mandaic route whenever CAL rendered no page-count marker,
which can relabel an ignored/repeated unpaginated response as the caller's requested page.

**Revised implication:** current catalogue membership proves only that a direct text is readable
on page 1. Public `page>1` is enabled only for direct files with independently observed CAL
pagination semantics. Current evidence supports exactly `74501`; the other seven current direct
files are page-1-only until new evidence is researched. Subdivided texts retain their independently
validated page axis inside an explicit subtext.

## Post-review acceptance after evidence-scoped direct pagination

After the adversarial direct-page finding was repaired, installed-stdio run `37068256656`
repeated the same bounded **20-call** acceptance matrix on the corrected branch.

The run again returned:

- 12 current subdivided categories and 8 current direct texts from category 74;
- successful page 1 for every current direct text;
- genuine `74501` page 2;
- successful selected child pages `74401/12`, `74422/106`, `74430/1`, and `74421/col`;
- `74421/col` text information and the merged special-coordinate semantics;
- token-analysis follow-up of returned `7442500a/0`.

All 20 upstream requests returned HTTP 200. The seven non-`74501` direct page-2 cases are no
longer part of the live matrix because their corrected behavior is a local pre-transport rejection,
covered by the review RED regression test.

