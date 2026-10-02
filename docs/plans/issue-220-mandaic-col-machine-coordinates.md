# Plan — issue #220: machine coordinates for Mandaic 74421/col

**Research:** `docs/research/issue-220-mandaic-col-machine-coordinates.md`  
**Blocks:** final acceptance of #188 / PR #217

## Goal

Make the current child text `74421/col` readable and keep its returned token coordinates
followable through `cal_token_analysis`, without widening the generic CAL coordinate grammar or
changing numeric Mandaic subtexts.

## Evidence-backed identity

Current CAL uses:

```text
file_id      = 74421
subtext_id   = col
info prefix  = 74421col
token coord  = 74421col + non-empty decimal tail
comment coord= 74421col + non-empty decimal tail
```

Numeric control `74421/103` keeps the ordinary decimal form `74421103...`.

## Design

### 1. Exact special-coordinate predicate

Extend the existing Mandaic-special coordinate predicate from #218 with exactly:

```regex
^74421col[0-9]+$
```

Do not change `is_cal_machine_coordinate`.

### 2. Explicit text-page prefix selection

Do **not** rely on `has_subtext_letter_suffix("col")`. That helper means “validated ordinary
subtext id with a lowercase suffix”; `col` is a separate Mandaic selector exception.

In `_parse_text_page`:

- if requested file/subtext is exactly `74421` / `col`, set
  `expected_coordinate_prefix = "74421col"` explicitly;
- otherwise preserve the existing suffix-bearing CPA/Syriac prefix logic;
- preserve the #218 direct-Mandaic exact-file prefixes `74425` and `74429`.

Refactor the later special-coordinate branch to key on an exact prefix set, e.g.
`{"74421col", "74425", "74429"}`, while keeping the direct-file set separately for choosing
direct-page prefix behavior.

### 3. Token-analysis composition

`cal_token_analysis` already accepts the dedicated Mandaic-special predicate. Extending that
predicate makes an exact returned `74421col...` handle followable with no new public parameter.

### 4. Comment / row identity

The current page uses `74421col...` for comment coordinates too. Existing line/comment identity
checks must continue to require the exact selected text prefix; do not add a generic multi-letter
coordinate fallback.

### 5. Structural fixture

Add a reduced current structural fixture for `74421/col`:

- exact file-info `coord=74421col`;
- one linked-token row carrying observed `74421col13614`;
- optionally a comment-linked row using an observed same-prefix coordinate when the current parser
  shape is represented faithfully;
- synthetic scholarly token text.

No bulk CAL text is retained.

## TDD gate

### RED

Before production code:

1. identifier contract:
   - special Mandaic predicate accepts `74421col13614`;
   - generic machine-coordinate predicate still rejects it;
   - reject `74421col`, `74421Col13614`, `74421foo13614`, `74422col13614`,
     punctuation/whitespace, and other multi-letter forms.

2. text-page composition:
   - `TextService.page("74421", subtext_id="col")` sends exactly
     `cset=M&file=74421&sub=col`;
   - returned token coordinate `74421col13614` is preserved verbatim;
   - numeric `74421/103` remains on the existing generic decimal path;
   - wrong-file / wrong-literal / missing-tail coordinates fail closed.

3. token analysis:
   - `TokenAnalysisService.analyze("74421col13614", 0)` issues one exact
     `getlex.php` request;
   - malformed near-misses fail locally before transport.

4. executable MCP documentation:
   - `cal_token_analysis` tool description names the current `74421/col` exception as opaque
     returned coordinate content, so the executable schema cannot lag behind Markdown docs.

Record behavioral RED via draft-PR CI. Formatting/lint failures do not count as the TDD RED.

### GREEN

Implement only:

- the exact `74421col` special predicate;
- explicit `74421/col` expected-prefix selection;
- exact-prefix special parser dispatch;
- executable/tool documentation.

Run deterministic + latest-compatible CI.

## Documentation gate

Update:

- `research.md` with R-058;
- a durable decision: either amend D-020 to cover exact Mandaic file/subtext coordinate families,
  or add D-021 if the literal-subtext identity deserves a separate rule;
- `docs/concepts/cal-identifiers.md`;
- `docs/tools/texts.md`;
- `docs/tools/token-analysis.md`;
- `CHANGELOG.md`;
- fixture provenance.

The documentation must say the coordinate is opaque and exact; it must not imply that arbitrary
multi-letter subtext labels are valid machine coordinates.

## Live acceptance

After offline GREEN, run installed `cal-mcp` over stdio with at most **3 sequential CAL calls**:

1. `cal_text_page("74421", subtext_id="col", page=1)`;
2. `cal_token_analysis` on one exact returned `74421col...` token;
3. optional numeric control `cal_text_page("74421", subtext_id="103", page=1)`.

No pagination or recursive discovery.

## Independent adversarial review

Review the final PR against the base branch, not against implementation history. Challenge:

- accidental reliance on `has_subtext_letter_suffix("col")`;
- global grammar widening;
- prefix confusion between `74421/col` and numeric `74421` subtexts;
- comment and empty-slot coordinate validation;
- token-analysis followability;
- executable schema/documentation sync.

Any must-fix becomes review RED → GREEN before merge.

## Parent #188 acceptance

Squash-merge #220 into `dev/issue-188-mandaic-routing`, then rerun the full #188 installed-stdio
matrix. The existing logical-call budget remains **20**: #220 changes parsing/followability, not
the number of planned operations.
