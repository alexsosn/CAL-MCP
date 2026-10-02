# Plan — issue #218: current Mandaic alphanumeric machine coordinates

**Depends on:** #188 branch state  
**Research:** `docs/research/issue-218-mandaic-machine-coordinates.md`

## Goal

Make the current direct Mandaic texts `74425` and `74429` readable without weakening unrelated CAL coordinate contracts, and keep every returned token coordinate followable through `cal_token_analysis`.

## Non-goals

- no attempt to decode the semantic meaning of coordinate letters;
- no general “ASCII alphanumeric coordinate” grammar;
- no changes to Mandaic subtext/page routing from #188;
- no hidden page traversal or corpus scan;
- no relaxation of ordinary/CPA/Syriac same-text coordinate checks.

## Design

### 1. Evidence-backed identifier helper

Add a dedicated identifier predicate for the two observed direct Mandaic coordinate families:

- `74425`: `74425` + decimal digits + optional 1–2 lowercase ASCII letters;
- `74429`: `74429` + either:
  - decimal digits + optional one lowercase ASCII letter; or
  - uppercase `A` + decimal digits.

The existing generic `is_cal_machine_coordinate` remains unchanged.

### 2. Text-page parsing

When `_parse_text_page` is parsing direct Mandaic file `74425` or `74429`, set the token-coordinate identity boundary to the exact requested file id.

`_parse_text_machine_coordinate` recognizes the dedicated Mandaic predicate only when that expected prefix is one of those exact file ids. All existing suffix-bearing subtext and split-Syriac behavior remains on the current generic path.

This keeps foreign-file token coordinates and unsupported letter shapes fail-closed.

### 3. Token-analysis follow-up

`cal_token_analysis` accepts a coordinate when either:

- the existing generic CAL machine-coordinate predicate accepts it; or
- the new exact-prefix Mandaic predicate accepts it.

The public schema remains the same string + non-negative word index. No corpus selector is added.

### 4. Fixtures

Add two reduced **structural** fixtures with synthetic scholarly token text:

- direct `74425` row(s) carrying observed coordinate shapes `7442500a` and `74425231aa`;
- direct `74429` row carrying observed uppercase-series coordinate `74429A01`.

Retain exact route/file-info/coordinate shapes; do not copy bulk CAL text.

## TDD gate

### RED

Before production code:

1. identifier tests:
   - accept `7442500a`, `74425231aa`, `74429000a`, `74429A01`;
   - reject near-misses such as three trailing lowercase letters, `74429B01`, missing numeric tail, whitespace/punctuation, and foreign prefixes.

2. text-page tests:
   - `TextService.page("74425")` parses both one- and two-lowercase-suffix token coordinates;
   - `TextService.page("74429")` parses `74429A01`;
   - altered special coordinates for another direct file or unsupported shape fail closed.

3. token-analysis tests:
   - `74425231aa` and `74429A01` pass local validation and issue one exact `getlex.php` request;
   - malformed near-misses fail before transport.

Run draft-PR CI and record the expected RED failures.

### GREEN

Implement only the dedicated predicate + the two call-site integrations. Run full deterministic and latest-compatible CI.

## Documentation gate

Update:

- `research.md` with a concise durable research entry;
- `wiki/decisions.md` only if the file-scoped opaque-coordinate rule is durable enough to constrain future parsers;
- `docs/tools/texts.md` and token-analysis docs with the fact that returned token coordinates are opaque and may contain evidence-backed letters;
- fixture provenance README;
- changelog if #218 is merged into the release-blocking #188 work.

## Review gate

Before merging into `dev/issue-188-mandaic-routing`:

1. perform a logically independent adversarial review grounded in the diff, current code, fixtures, research runs, and existing coordinate contracts;
2. specifically challenge over-broad validation, prefix ambiguity, comment-coordinate interaction, empty-token slots, and public token-analysis validation;
3. resolve all must-fix findings and rerun CI.

## Acceptance after merge into #188

Re-run installed `cal-mcp` over stdio with bounded live requests. The #188 matrix must now pass `74425` and `74429` page 1, and at least one returned special coordinate must be accepted by `cal_token_analysis`.
