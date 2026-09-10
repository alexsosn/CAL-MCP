# Issue #113 plan — typed KWIC full-context follow-up

**Plan date:** 2026-09-10  
**Research:** `docs/research/issue-113-kwic-full-context.md`  
**Baseline:** `main` at `8281d436498f40bfa01aba4000d65100b3a37d04`

Sequence: research → plan → deterministic RED → minimal implementation → docs/release sync → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen public contract

Add one explicit concordance-family operation:

```text
cal_kwic_full_context(
    file_id: string,
    target_coordinate: string,
    charset: string,
    subtext_id: string | null = null,
)
```

Allowed `charset` values are exactly the CAL values already returned by `KwicHit`: `R`, `H`, `S`.

Do not accept `full_context_url`, arbitrary CAL URLs, endpoint names, `variants`, or script-switch parameters.

Public result:

```text
{
  status: "found" | "not_found",
  file_id: string,
  subtext_id: string | null,
  target_coordinate: string,
  charset: "R" | "H" | "S",
  lines: [
    {
      coordinate: string,
      display_coordinate: string | null,
      text: string,
      tokens: [
        {
          coordinate: string,
          word_index: integer,
          text: string,
          lexical_url: string
        }
      ],
      comment_url: string | null
    }
  ],
  provenance: <existing ConcordanceProvenance serialization>
}
```

For `not_found`, `lines` is empty. Existing KWIC result fields and `full_context_url` remain unchanged.

## Request contract

Validate locally before transport:

- `file_id`: decimal CAL identifier;
- `target_coordinate`: decimal CAL coordinate;
- `subtext_id`: optional decimal CAL identifier;
- `charset`: exactly `R`, `H`, or `S`.

One cache-miss call submits exactly:

```text
GET get_a_kwicchapter.php
file=<file_id>
sub=<subtext_id or empty string>
cset=<charset>
target=<target_coordinate>
```

Keep this parameter order in deterministic request tests. Use a distinct cache namespace such as `kwic-full-context-v1`.

No context is prefetched by parent KWIC operations. No links returned by the full-context page are followed.

## Models and module boundary

Implement in `src/cal_mcp/concordance.py` because this route is selected by fields returned from `KwicHit` and is semantically a KWIC follow-up.

Import and reuse `TextLine` and `TextToken` from `cal_mcp.texts`. This import does not create a cycle because `texts.py` does not import `concordance.py`.

Add concordance-local models, for example:

```python
class KwicFullContextStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class KwicFullContextPage:
    status: KwicFullContextStatus
    lines: tuple[TextLine, ...]


@dataclass(frozen=True, slots=True)
class KwicFullContextResult:
    status: KwicFullContextStatus
    file_id: str
    subtext_id: str | None
    target_coordinate: str
    charset: str
    lines: tuple[TextLine, ...]
    provenance: ConcordanceProvenance
```

The page/result split is optional if a smaller equivalent design preserves parser/service separation. Do not change the existing `TextLine` / `TextToken` public shapes.

## Full-context parser

Use the existing concordance `_TableHTMLParser` because current `get_a_kwicchapter.php` rows are two-cell `<tr>` structures. Do not pass the page through ordinary `texts._parse_text_line()`: the shared semantic parser splits `<td>` cells, which would detach display-coordinate/comment metadata from the token cell.

### Response identity

Before accepting semantic content, require the response URL to have:

- scheme `https`;
- netloc `cal.huc.edu`;
- path exactly `/get_a_kwicchapter.php`;
- no fragment;
- exactly one `file`, `sub`, `cset`, `target` query value;
- no unexpected request-control query keys on the canonical service response;
- values matching the requested selectors (`sub=` means public `None`).

A selector mismatch, repeated/missing value, unknown charset, foreign origin, wrong path, or unexpected control is `ConcordanceParseError`.

### File identity

Require one unique file-information link to `get_file_info.php?coord=<file_id>` with a rendered label beginning with the requested decimal file ID. A different/repeated/malformed file identity is parser drift.

### Not-found state

Recognize only the exact semantic form:

```text
Target coordinate <requested target> not found.
```

Return `NOT_FOUND` only when that marker is unique and no recognized full-context text rows are present.

Reject:

- marker for another coordinate;
- repeated/conflicting not-found markers;
- not-found marker mixed with recognized context rows;
- successful-looking page with neither rows nor the exact marker.

### Found rows

For each recognized text row:

- require the expected two semantic cells: coordinate/comment metadata and text/tokens;
- require one `comment.php?coord=<row coordinate>` link when a rendered coordinate link is present, and preserve its label as `display_coordinate`;
- parse only `getlex.php` lexical anchors from the text cell;
- require decimal `coord` and `word`, same coordinate for all retained tokens in the row;
- preserve rendered token text and absolute same-origin lexical URL;
- require at least one visible retained token;
- preserve CAL row order;
- reject repeated/conflicting comment links, cross-origin links, malformed identifiers, detached labels, or mixed token coordinates.

Rendered `text` is the current cell text after ordinary whitespace normalization; do not reconstruct it by joining token values because current Hebrew rendering includes CAL presentation separators.

### Current Hebrew terminal empty-anchor artifact

For requested `charset == "H"` only, permit and discard exactly one terminal empty `getlex.php` anchor in a recognized row after validating:

- it is the final lexical anchor;
- its coordinate equals the row coordinate;
- its numeric word index is greater than and immediately follows the final preceding lexical word index;
- no other empty lexical anchor occurs in the row.

For `R` and `S`, any empty lexical anchor is drift. For `H`, missing terminal empty anchors are acceptable so the adapter does not turn a CAL cleanup into breakage; multiple, nonterminal, coordinate-mismatched, or non-successor empty anchors remain drift.

This tolerance stays local to the KWIC full-context parser. The ordinary text-page parser remains unchanged and strict.

### Target invariant

For `FOUND`, the requested `target_coordinate` must occur in exactly one returned `TextLine`. Zero or multiple target rows are drift. Other context coordinates remain CAL-provided and are not required to form a locally inferred numeric window.

## Service and provenance

Add `ConcordanceService.kwic_full_context(...)`.

On success, propagate the typed request fields directly into `KwicFullContextResult` and use existing `ConcordanceProvenance`:

```text
source = "CAL"
operation = "kwic_full_context"
text_id = file_id
source_url / retrieved_at = shared client result
```

Do not add target/subtext/charset nullable fields to every existing concordance provenance payload; those values are already explicit top-level fields of this result.

## Server and release surface

Add one MCP tool in `src/cal_mcp/server.py` named `cal_kwic_full_context`, with a docstring that says it consumes selectors returned by a KWIC hit and performs one explicit request.

Update server-level instructions to mention the explicit KWIC-hit → full-context composition and preserve the no-hidden-traversal statement.

Add `cal_kwic_full_context` to `src/cal_mcp/release_surface.py`.

The pre-release public surface therefore changes from 30 to 31 tools. Update every explicit frozen 30-tool assertion/claim, including:

- `tests/test_release_contract.py` (`len(V01_PUBLIC_TOOLS) == 31` and expected changelog phrases);
- `CHANGELOG.md` (`31 public tools`, `31-tool schema`);
- `docs/index.md` pre-release status count;
- README or other user docs if they contain an explicit 30-tool count.

Do not change live-smoke request budget solely because this new tool exists; the smoke harness samples capability families rather than every public tool.

## Gate 1 — deterministic RED

After this plan is committed, add reduced offline fixtures and tests only. Production remains unchanged.

Suggested fixtures:

- `tests/fixtures/cal/kwic_full_context_tel_dan_roman.html`: reduced current-shaped file marker plus at least rows 02/03/04, with target 1325003;
- `tests/fixtures/cal/kwic_full_context_tel_dan_hebrew.html`: reduced Hebrew row(s) including the researched terminal empty lexical anchor;
- `tests/fixtures/cal/kwic_full_context_not_found.html`: requested file identity plus exact target-not-found marker.

Focused tests must prove:

1. exact one-request service identity and parameter order;
2. found result preserves file/sub/target/charset and line order;
3. target line occurs exactly once;
4. target display coordinate, rendered line text, ordered visible tokens, word indices, absolute lexical URLs, and comment URL are preserved;
5. `H` terminal empty anchor is validated then omitted from `tokens`;
6. malformed/multiple/nonterminal H empty anchors fail;
7. R/S empty lexical anchors fail;
8. explicit matching not-found marker returns `not_found` with empty lines;
9. marker mismatch, marker-plus-lines, no rows/no marker, missing target, and duplicate target fail closed;
10. response URL foreign-origin/wrong-path/query mismatch/repeated/missing/unexpected selectors fail closed;
11. requested file identity mismatch/repetition fails closed;
12. invalid caller identifiers/charset fail locally before transport;
13. existing parent KWIC tests still prove no full-context prefetch;
14. existing ordinary text-page behavior remains unchanged;
15. MCP runtime registry/release manifest expects the new tool and exact schema without arbitrary URL input.

A valid RED requires both CI matrices to pass environment checks, Ruff lint/format, and strict mypy, then fail pytest only in the new expectations caused by the absent implementation/release entry. Record the exact RED SHA before production changes.

## Gate 2 — minimal implementation

Expected production files:

- `src/cal_mcp/concordance.py`;
- `src/cal_mcp/server.py`;
- `src/cal_mcp/release_surface.py`.

Do not modify:

- shared HTTP policy;
- ordinary `TextService.page()` routing/parser semantics;
- existing KWIC hit parsing/request contracts;
- parent KWIC auto-fetch behavior.

Implementation GREEN requires the focused new suite plus existing concordance/text/release-contract suites to pass before documentation is finalized.

## Gate 3 — docs/release synchronization

Update at least:

- `docs/tools/concordance.md`: five operations, explicit full-context workflow, selectors/status/line semantics, H artifact boundary, one-request/no-prefetch distinction;
- `docs/index.md`: 31-tool status and KWIC full-context capability;
- `CHANGELOG.md`: synchronized 31-tool v0.1 surface;
- README/getting-started/corpus-context only where an existing workflow/count statement would otherwise remain materially stale.

Do not claim a fixed context-window size from the Tel Dan example and do not claim full-context pages are ordinary paginated text pages.

## Gate 4 — dual GREEN

On the exact candidate SHA require deterministic and latest-compatible CI matrices to pass:

- dependency/environment checks;
- Ruff lint;
- Ruff format;
- strict mypy;
- complete pytest suite.

Before review, verify changed-file scope contains no research/probe/helper workflows.

## Gate 5 — logically independent adversarial review

Review the exact GREEN head from the issue, committed research/plan, raw diff, and retained reduced fixtures. Challenge at least:

1. arbitrary-URL or arbitrary-query execution leakage;
2. canonical response origin/path and selector consistency;
3. `sub=` ↔ public `None` semantics;
4. target exactly-once invariant;
5. file identity consistency;
6. matching not-found marker and contradiction handling;
7. Hebrew empty-anchor tolerance being confined to current full-context H rows and not ordinary text pages;
8. preservation of rendered cell text rather than reconstruction from token labels;
9. cross-origin lexical/comment URLs;
10. no context prefetch from parent KWIC operations;
11. release manifest/runtime tool-set equality and correct 31-tool docs;
12. cache/request bounds and no hidden traversal;
13. no temporary workflow/helper residue.

Any blocker gets a focused RED regression, minimal fix, dual GREEN, and a new exact-head review.

## Merge gate

Immediately before merge:

- refetch `main`;
- if `main` advanced, synchronize the branch and rerun required CI/review on the synchronized head;
- mark ready only after exact-head GREEN + clean review;
- squash-merge guarded by `expected_head_sha`.

After merge, confirm #113 closes and update the reachability documentation/umbrella issue state only if still open.

## CAL load impact

Research is complete at five fixed requests total across two bounded probes. Normal CI is offline. Production performs at most one new logical CAL request per explicit full-context call; cache/single-flight semantics may reduce duplicate upstream I/O. No batch expansion or automatic context fetch is introduced.