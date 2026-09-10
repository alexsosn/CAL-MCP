# Issue #108 plan — typed CAL line comments and citation translations

**Plan date:** 2026-09-10  
**Research:** `docs/research/issue-108-line-comments.md`  
**Baseline:** `main` at `b745efad184302925c69e7fbbc796c00c7e2d6c2`

Sequence: research → plan → deterministic RED → minimal implementation → focused GREEN → docs/release sync → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen public contract

Add one explicit text-family operation:

```text
cal_text_line_comments(coordinate: string)
```

The operation consumes the CAL line coordinate already returned by `TextLine.coordinate` / encoded in `TextLine.comment_url`. It does not accept `comment_url`, a path, endpoint name, or arbitrary query values.

### Coordinate contract

Current CAL evidence includes both decimal coordinates and alphanumeric coordinates such as `444015370A04`. The selector is therefore treated as an opaque CAL coordinate rather than a decimal identifier.

Validate locally with a dedicated contract equivalent to:

```python
^[A-Za-z0-9]{1,64}$
```

Do not reuse the decimal `file_id` / `subtext_id` validator and do not broaden those existing contracts. Reject empty strings, whitespace, punctuation/query delimiters, non-ASCII characters, and overlong values before transport.

### Public status and record model

Use statuses exactly:

```text
found
no_citations
```

Do not expose `not_found`: current CAL returns the same explicit no-citations page for a deliberately invalid coordinate, so line existence cannot be inferred from `comment.php` alone.

Represent each ordered current CAL record with a dedicated small model:

```text
{
  reference: string,
  source_text: string | null,
  translation: string | null,
  lemma_key: string,
  headword: string,
  part_of_speech: string | null,
  gloss: string | null,
  entry_url: string
}
```

Result shape:

```text
{
  status: "found" | "no_citations",
  coordinate: string,
  records: [<record>, ...],
  provenance: <existing TextProvenance serialization>
}
```

For `no_citations`, `records` is empty.

The record-specific model is intentional. `LemmaRef` would require browse-result semantics that the comment page does not expose and would not capture the record-local citation/translation relationship.

## Request contract

One cache-miss call submits exactly:

```text
GET comment.php?coord=<coordinate>
```

Use parameter order exactly as above and a distinct cache namespace such as `text-line-comments-v1`.

One explicit public call performs at most one new logical CAL request. A completed cache hit may perform zero new upstream I/O. `cal_text_page` remains non-prefetching and no lexical-entry link returned by this page is followed automatically.

## Response identity

Before accepting semantic content, require the actual response URL to have:

- scheme `https`;
- netloc `cal.huc.edu`;
- path exactly `/comment.php`;
- no fragment;
- exactly one query key, `coord`;
- exactly one non-empty coordinate value equal to the requested coordinate.

Repeated, missing, mismatched, or additional selectors are `TextParseError`. A foreign origin or wrong path is `TextParseError`.

Require exactly one page title whose normalized text is:

```text
CAL: citations and comments for <requested coordinate>
```

A missing, repeated, or mismatched title is parser drift.

## Parser design

Implement a dedicated small `HTMLParser` in `src/cal_mcp/texts.py`. Do not parse the raw HTML with regular expressions. The existing `_parse_lines()` abstraction intentionally flattens spans and therefore cannot reliably preserve the source-text/translation distinction needed here.

Only semantic content inside `div.summary-card` participates in the result. Ignore CAL banner/footer/navigation controls entirely.

### Record structure

For each `<p>` inside the summary card:

1. Preserve document order.
2. Recognize the exact no-citations marker separately.
3. A found record must contain one rendered reference before the lexical-entry link.
4. Current CAL emits two ordered citation spans: source citation followed by Roman/English translation/comment. Preserve their text independently; normalize whitespace-only span content to `None`.
5. Require the semantic phrase `See the entire entry for` before one lexical-entry link.
6. Require exactly one lexical-entry link in the record.
7. Validate that entry link against canonical CAL `oneentry.php` semantics:
   - same CAL HTTPS origin after resolution;
   - path exactly `/oneentry.php`;
   - no fragment;
   - query keys exactly `lemma` and `cits`;
   - one non-empty `lemma` value;
   - exactly `cits=all`.
8. Preserve the decoded CAL `lemma` query value as `lemma_key`.
9. Preserve the rendered headword from the link.
10. Preserve rendered POS text between the entry link and gloss when present; expose absent/empty POS as `None` rather than inventing a value.
11. Preserve the rendered gloss when present; expose absent/empty gloss as `None`.
12. Reject a structurally empty record, detached entry link/headword, multiple/conflicting entry links, or an unrecognized record shape rather than returning a plausible partial record.

The current raw probes emit two spans even when a field is empty. The deterministic fixture will pin this current shape. If future CAL omits a span entirely, that is parser drift until researched rather than a guessed role reassignment.

### Empty state

Recognize only normalized exact marker:

```text
NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED
```

Return `NO_CITATIONS` only when this marker occurs exactly once and there are no recognized found records or other non-empty semantic record paragraphs.

Reject marker + records, repeated markers, or unknown successful summary-card content as `TextParseError`.

## Models and service boundary

Add text-local types, for example:

```python
class TextLineCommentsStatus(StrEnum):
    FOUND = "found"
    NO_CITATIONS = "no_citations"

@dataclass(frozen=True, slots=True)
class TextLineCommentRecord: ...

@dataclass(frozen=True, slots=True)
class TextLineCommentsPage:
    status: TextLineCommentsStatus
    records: tuple[TextLineCommentRecord, ...]

@dataclass(frozen=True, slots=True)
class TextLineCommentsResult:
    status: TextLineCommentsStatus
    coordinate: str
    records: tuple[TextLineCommentRecord, ...]
    provenance: TextProvenance
```

Add `TextService.line_comments(coordinate)`:

- validate coordinate locally;
- issue one `CalRequest(method="GET", path="comment.php", params=(("coord", coordinate),))`;
- parse with a request-aware closure;
- return `TextProvenance(source="CAL", operation="line_comments", upstream_id=coordinate, actual source_url/retrieved_at)`.

Do not alter existing `TextLine`, `TextToken`, `TextPage`, page routing, or decimal file/subtext validation.

## Server and release surface

Add MCP tool `cal_text_line_comments` in `src/cal_mcp/server.py` with one public input, `coordinate`. Its documentation must say it is an explicit caller-controlled follow-up from a text line, not an automatically expanded field.

Server instructions should mention the `cal_text_page` → selected `TextLine.coordinate` → `cal_text_line_comments` composition while retaining the no-hidden-traversal policy.

After focused implementation GREEN, add `cal_text_line_comments` to `V01_PUBLIC_TOOLS`. The pre-release surface changes from 31 to 32 tools. Update all executable release/docs assertions and user-visible count statements from 31 to 32. Do not change the live-smoke request budget solely because the public tool count increased.

## Gate 1 — deterministic RED

After this plan is committed, remove the temporary research workflow and add tests/fixtures only; production and release manifest remain unchanged.

Reduced fixtures:

- `tests/fixtures/cal/text_line_comments_pj_gen8_21.html`: two current-shaped records, including one empty translation and one populated translation;
- `tests/fixtures/cal/text_line_comments_none.html`: exact current no-citations marker.

Tests must prove:

1. found parsing preserves two records in CAL order;
2. reference/source/translation/lemma/headword/POS/gloss/absolute entry URL are preserved;
3. whitespace-only source or translation becomes `None` without collapsing the record;
4. exact no-citations marker returns `no_citations` and no records;
5. marker mixed with a record, repeated marker, no marker/no records, or unknown paragraph content fails closed;
6. response URL rejects foreign origin, wrong path, fragment, missing/repeated/mismatched `coord`, and extra selectors;
7. title rejects missing/repeated/mismatched coordinate;
8. entry URL rejects foreign origin, wrong path, fragment, missing/repeated/empty `lemma`, missing/repeated/wrong `cits`, and extra selectors;
9. an alphanumeric coordinate such as `444015370A04` passes local validation and is sent verbatim;
10. invalid public coordinates fail locally before transport;
11. service performs exactly one request and returns correct provenance;
12. MCP registry exposes `coordinate` only and no URL input;
13. release manifest test expects `cal_text_line_comments` and 32 tools;
14. existing text-page tests remain unchanged and continue to prove page retrieval does not fetch comment links.

A valid RED requires both CI matrices to pass dependency/environment validation, Ruff lint/format, and strict mypy, then fail pytest only in new expectations caused by the absent parser/service/tool/release entry. Record the exact RED SHA before production changes.

## Gate 2 — minimal implementation

Expected production files:

- `src/cal_mcp/texts.py`;
- `src/cal_mcp/server.py`.

Keep `src/cal_mcp/release_surface.py` unchanged until the focused implementation suite is green, so release synchronization remains an explicit later gate.

Focused GREEN must include the new tests plus existing text-page/current-shape/regression suites. Do not change shared HTTP policy or automatically follow returned entry links.

## Gate 3 — release/docs synchronization

Once focused implementation is green:

- add the tool to `V01_PUBLIC_TOOLS`;
- change the v0.1 frozen surface from 31 to 32 in release/docs executable contracts;
- update `README.md`, `CHANGELOG.md`, `docs/index.md`, and `docs/tools/texts.md`;
- remove #108 from the current reachability-gap list and its executable docs contract;
- preserve #82 as a separate interlinear ergonomics request unless this implementation actually satisfies its broader contract.

## Gate 4 — dual GREEN

On the exact candidate SHA require deterministic and latest-compatible matrices to pass:

- dependency/environment checks;
- Ruff lint;
- Ruff format;
- strict mypy;
- complete pytest suite.

Before review, verify no temporary research/implementation workflow remains in the changed-file set.

## Gate 5 — logically independent adversarial review

Review exact GREEN head from the issue, dated research/plan, raw diff, reduced fixtures, and CI. Challenge at least:

1. arbitrary URL/path/query execution leakage;
2. alphanumeric-coordinate support versus injection/over-broad selector acceptance;
3. canonical response origin/path/query and title identity;
4. `no_citations` not being falsely represented as coordinate existence or `not_found`;
5. marker/record contradiction and unknown paragraph fail-closed behavior;
6. lexical-entry same-origin/path/query validation and no auto-follow;
7. record ordering and independent source/translation preservation;
8. nullable POS/gloss not masking structurally malformed records;
9. parent `cal_text_page` remaining non-prefetching and backward compatible;
10. 32-tool runtime/release/docs equality;
11. no temporary workflow/helper residue;
12. one-request/cache bounds.

Any blocker gets a focused RED regression, minimal fix, dual GREEN, and a new exact-head review.

## Merge gate

Immediately before merge:

- refetch `main`;
- if `main` advanced, synchronize the branch and rerun required CI/review on the synchronized exact head;
- mark ready only after exact-head GREEN + clean independent review;
- squash-merge guarded by `expected_head_sha`.

After merge, confirm #108 closes and update reachability documentation/umbrella state only where executable docs do not already cover it.

## CAL load impact

Focused live research is complete at three fixed raw requests plus indexed-page inspection; normal CI is offline. Production performs at most one new logical CAL request per explicit line-comments call. No comment-page link is followed automatically, no corpus enumeration occurs, and no background polling/crawl is introduced.