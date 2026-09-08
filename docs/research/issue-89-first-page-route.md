# Issue #89 research — preserve CAL first-page route fidelity

Date: 2026-09-08
Baseline: `main` at `d704ee5c2b542e22c22a3929771fa466dea0a0f6`
Related user bug: #79
Research support: #87

## Question

Does `TextService.page(..., page=1)` construct a request that differs from CAL's current first-page links, and can the mismatch be fixed without changing parser semantics or request volume?

## Current implementation

`TextService.page()` always appends a zero-based upstream page parameter:

```python
params.append(("page", str(page - 1)))
```

Therefore public `page=1` always becomes `page=0`, regardless of whether CAL's own browser link includes a page selector.

Existing offline tests accidentally freeze that synthetic first-page shape for both paginated and unpaginated fixtures.

## Current CAL evidence

Rechecked 2026-09-08 with tiny source lookups only.

### Unpaginated Tel Dan Stele

CAL's current epigraphic text menu (`https://cal.huc.edu/epig_abbrevs.php`) links `TDanStel (Tel Dan Stele)` / file `13250` to:

`https://cal.huc.edu/get_a_chapter.php?file=13250`

There is no `page` parameter in the source-provided first-page link.

This directly matches issue #79: `cal_text_search` discovers file `13250`, while `cal_text_page(file_id="13250", page=1)` currently constructs `get_a_chapter.php?file=13250&page=0` and fails generically in live use.

### Representative paginated text

CAL's current first page for BT AZ / file `71026` is indexed at:

`https://cal.huc.edu/get_a_chapter.php?file=71026`

The returned page explicitly reports `Page 1 of 50 (2413 lines total)` and exposes a next-page link. Thus omission of `page` is also CAL's normal first-page route for a representative paginated text; it is not a Tel-Dan-only exception.

## Existing parser capability

`parse_text_page()` already supports both shapes:

- paginated pages with a `Page N of M` marker;
- unpaginated pages with no pagination marker, represented as public page 1 with `page_count=None` and `total_lines=None`.

The Tel Dan fixture already proves the parser can return the expected coordinates and lines from an unpaginated response. The defect is therefore request construction, not page parsing.

## Smallest safe change

Preserve CAL's own first-page default instead of inventing `page=0`:

- public `page == 1`: omit the `page` query parameter entirely;
- public `page >= 2`: keep the established zero-based mapping `page=<public-1>`.

Keep `file` and optional `sub` ordering unchanged. This changes no public schema and adds no request.

## Why not special-case Tel Dan

The representative BT AZ check shows the same first-page URL convention on a paginated text. A file-id special case would encode the symptom rather than CAL's route semantics and would leave the misleading `page=0` behavior in the general client.

## Non-goals

- Do not solve specialized Mandaic `cset=M` / subtext routing here (#85/#78/#83).
- Do not change page parsing, navigation validation, text models, token extraction, provenance, caching, or request retry behavior.
- Do not add fallback requests or route probing.
- Do not alter page >= 2 mapping.

## TDD target

Behavior-first offline tests should prove before production modification:

1. public page 1 for unpaginated Tel Dan constructs exactly one request with only `file=13250`;
2. public page 1 for representative paginated BT AZ constructs exactly one request with only `file=71026`;
3. public page 2 continues to send `page=1` (and preserves optional `sub`);
4. returned parser/provenance semantics remain unchanged.

The page-1 request assertions must fail on the baseline specifically because the implementation adds `page=0`; static gates should remain green.

## CAL load

Normal CI remains fully offline. Research used only the two fixed current CAL pages/menu references above; no traversal, pagination, or retry loop.

## Conclusion

Issue #79 is a request-route regression: CAL's current first-page URLs omit `page`, while CAL-MCP synthesizes `page=0`. The narrow fix is to omit the upstream page selector only for public page 1 and retain the existing mapping for later pages.
