# Research — issue #218: alphanumeric machine coordinates in current direct Mandaic texts

**Issue:** #218  
**Rechecked:** 2026-10-02  
**Scope:** CAL token machine-coordinate identity on current Mandaic text pages. This research does not change subtext/page routing from #188.

## Trigger

The installed-stdio acceptance for #188 opened current direct Mandaic file `74425` and failed closed:

```text
cal_text_page({"file_id":"74425","page":1})
→ parser_drift: CAL returned a non-decimal coordinate
```

A structural probe showed token links such as `getlex.php?coord=7442500a&word=0`, while the page's file-information coordinate is the ordinary decimal file id `74425` and sampled comment coordinates are decimal.

## Bounded live evidence

All probes were sequential, explicit, and non-recursive. No page navigation or result links were crawled.

### Probe 1 — eight current direct Mandaic files plus one subdivided control

Run: GitHub Actions `37060041291` (2026-10-02).  
Budget used: 10 GETs: eight current direct page-1 requests, one `74401/12` subdivided control, and one explicit token-analysis follow-up.

Observed token-coordinate shapes:

- `74420`: no lexical token links on the current page; plain/comment-linked rows.
- `74424`: decimal tails only.
- `74425`: decimal plus alphanumeric tails; sampled `7442500a`, `7442500b`, `7442500c`; lowercase letters observed through `w`.
- `74426`: decimal tails only.
- `74427`: decimal tails only.
- `74429`: decimal plus alphanumeric tails; sampled `74429000a`, `74429000b`.
- `74431`: decimal tails only.
- `74501`: decimal tails only.
- subdivided control `74401/12`: decimal tails only and exact file+sub prefix `7440112`.

The explicit CAL request `getlex.php?coord=7442500a&word=0` returned HTTP 200 with CAL's normal token-analysis result marker and a lemma route. Therefore the trailing lowercase letter is part of CAL's actual machine coordinate, not decoration that CAL-MCP may strip.

### Probe 2 — residual shapes in 74425 and 74429

Run: GitHub Actions `37060173462`.  
Budget used: 2 GETs, one page-1 request for each file.

Unique coordinate classification:

- **74425:** 654 unique coordinates:
  - 559 decimal tails;
  - 13 tails ending in one lowercase letter;
  - 82 tails ending in two lowercase letters.
  - observed examples include `74425231aa`, `74425231ab`, … `74425231gk`.
- **74429:** 412 unique coordinates:
  - 378 decimal tails;
  - 2 tails ending in one lowercase letter;
  - 32 uppercase-series coordinates `74429A01` through `74429A32`.

No evidence supports interpreting those letters locally as page, subtext, line, or word fields. They are treated as opaque parts of CAL's machine coordinate.

### Probe 3 — edge token-analysis follow-up

Run: GitHub Actions `37060285443`.  
Budget used: 2 GETs.

- `getlex.php?coord=74425231aa&word=0` → HTTP 200, normal analysis marker, linked lemma result.
- `getlex.php?coord=74429A01&word=0` → HTTP 200, normal analysis marker with CAL's explicit current “unrecognizable query or no such lemma found” state and no linked lemma.

Both edge coordinate forms therefore reach CAL's token-analysis surface as valid coordinate selectors. “No lemma” for one token is a scholarly/data result, not evidence that the coordinate syntax is invalid.

## Current implementation mismatch

`src/cal_mcp/identifiers.py` currently defines the shared machine-coordinate grammar as:

```text
decimal
OR
decimal + one lowercase letter + decimal
```

That grammar was researched for existing CPA/Syriac/ordinary cases. It rejects all of the newly observed Mandaic forms:

- decimal + one/two trailing lowercase letters (`7442500a`, `74425231aa`);
- file id + uppercase letter + decimal (`74429A01`).

Two public paths are therefore too narrow:

1. direct Mandaic text-page parsing: with no subtext prefix supplied, linked token coordinates fall through the generic decimal-only branch;
2. `cal_token_analysis`: its input validator delegates to the shared machine-coordinate grammar and rejects a coordinate that `cal_text_page` ought to return.

## Narrow compatibility boundary

Do **not** widen the global machine-coordinate grammar to arbitrary alphanumeric strings.

Evidence supports a corpus/file-scoped extension only for the two current direct Mandaic files:

- **74425:** exact prefix `74425`, followed by one or more decimal digits and optionally **one or two lowercase ASCII letters**;
- **74429:** exact prefix `74429`, followed by either:
  - one or more decimal digits and optionally one lowercase ASCII letter; or
  - uppercase `A` followed by one or more decimal digits.

The coordinate must still be non-empty, same-file, ASCII, and exact; foreign prefixes, punctuation, whitespace, extra/misplaced letters, other uppercase series, and broader arbitrary alphanumerics remain invalid.

Because `cal_token_analysis` receives only the coordinate and word index, it can safely select this special grammar by the exact coordinate prefix `74425` or `74429`. No caller-supplied dialect/corpus switch is required.

## Consequences for #188 acceptance

The original #188 route repair is correct, but its stronger acceptance goal (“every current top-level Mandaic text opens”) uncovered this independent identifier gap. #218 should be merged into the #188 branch before #188 is finalized.

After #218, final live acceptance should verify at minimum:

- `cal_text_page("74425")` returns token coordinates containing the observed special forms without parser drift;
- `cal_text_page("74429")` returns the uppercase-series coordinate without parser drift;
- a returned special coordinate is accepted by `cal_token_analysis`;
- ordinary/CPA/Syriac coordinate validators remain unchanged outside the exact 74425/74429 prefixes.

## Request accounting

Research used 14 bounded GETs total across three probes: 10 + 2 + 2. No hidden pagination, recursion, cache warming, or corpus crawl was performed.
