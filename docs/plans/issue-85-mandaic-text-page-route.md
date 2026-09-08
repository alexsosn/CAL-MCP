# Issue #85 plan — restore bounded Mandaic text-page retrieval

Date: 2026-09-08
Research prerequisite: `docs/research/issue-85-mandaic-text-page-route.md`

## Goal

Make the existing `cal_text_page(file_id="74410", page=1)` operation retrieve Ginza Rabba Right Side through CAL's current Mandaic route and return line/token metadata, while preserving the one-request public contract and ordinary text behavior.

## Gate 1 — test-only RED

Add one focused offline regression module and a reduced Mandaic HTML fixture before production edits.

Freeze these behaviors:

1. `TextService.page("74410", page=1)` makes exactly one request:
   `GET get_a_chapter.php` with ordered params `cset=M`, `file=74410`, `sub=001`.
2. The returned page is `found`, reports public page `1`, and preserves the Ginza file label.
3. At least the first two fixture lines preserve display coordinates, rendered text, machine coordinates, zero-based token positions, and absolute `getlex.php` lexical URLs.
4. Conversion of public page 2 uses `sub=002` without a discovery request.
5. If a specialized next-page link is present, it is accepted only for the same `cset=M`/file and adjacent `sub`; absence of total-count metadata does not invent `page_count`.
6. Existing ordinary `file/page` request shape remains frozen by current tests.

Accept RED only if dependency installation, Ruff, formatting and mypy are green and pytest failures are limited to the new Mandaic expectations.

## Gate 2 — minimal implementation

Keep the public MCP schema unchanged.

In `src/cal_mcp/texts.py`:

- introduce a private/internal page-route distinction; do not expose it in result schemas;
- select the Mandaic route only for current CAL collection-74 file identifiers (`file_id.startswith("74")`) when caller `subtext_id` is `None`;
- Mandaic request params: `(("cset", "M"), ("file", file_id), ("sub", f"{page:03d}"))`;
- ordinary request construction remains byte-for-byte equivalent for all existing cases;
- parser receives a private hint that the requested page came from the Mandaic `sub` selector;
- in that mode only, if CAL omits ordinary `Page N of M` metadata, use the explicit requested public page as the page number;
- recognize `getlex.php` token links with the same coordinate/word validation as `bablex.php`, preserving the actual endpoint in `lexical_url`;
- if Mandaic previous/next links use `cset=M` plus `sub=NNN`, validate same file/cset and adjacency, but leave `page_count=None` unless CAL provides a total count;
- do not weaken ordinary-route navigation validation.

Do not add a route-discovery request.

## Gate 3 — focused and full GREEN

First require focused tests for:

- new Mandaic route/token regression;
- existing text service/parser suite;
- token-analysis tests if shared token URL assumptions are touched.

Then require full permanent CI in both matrices:

- deterministic constrained dependency environment;
- latest-compatible dependency resolution;
- `pip check` / exact environment verification as configured;
- Ruff lint + format;
- strict mypy;
- full pytest.

Normal CI remains offline.

## Gate 4 — documentation

Update `docs/tools/texts.md` without expanding the public tool surface:

- explain that `cal_text_page` internally adapts CAL's ordinary and Mandaic page routes;
- public `page` remains one-based in both cases;
- Mandaic pages may have adjacent navigation without a rendered total page count;
- token `lexical_url` preserves whichever CAL lexical endpoint the page supplies (`bablex.php` or `getlex.php`);
- one public call still makes exactly one CAL request.

If wording changes, add a small docs-contract regression only if independent review finds the guarantee otherwise fragile.

## Gate 5 — logically independent adversarial exact-head review

Review the complete final diff from scratch on the exact GREEN head. Challenge at least:

- why collection-74 routing is justified and not a title-specific hack;
- no extra CAL request or recursive discovery;
- ordinary file/page/subtext request shape unchanged;
- caller `subtext_id` does not get silently reinterpreted as Mandaic page number;
- page 1 -> `001`, page 2 -> `002` and large positive pages are not truncated;
- malformed/foreign specialized navigation still fails closed;
- absent page count is not invented;
- `getlex.php` links cannot bypass decimal coordinate/word-index validation;
- lexical URL preserves source endpoint;
- response page/provenance remains consistent with the caller's one-based page;
- no change to public tool count/release surface;
- no temporary helper/workflow in final diff;
- no live CAL traffic in normal CI.

Any blocker requires a test-first review-regression RED, minimal fix, full exact-head GREEN, and fresh review.

## Merge gate

Immediately before merge:

1. refetch `main` and PR head;
2. if main advanced, synchronize non-destructively and rerun full CI/review;
3. ensure final PR body records primary RED, final GREEN, and exact-head review;
4. mark ready only after PASS;
5. merge only with `expected_head_sha` equal to the reviewed head.

## Follow-up boundary

After merge, close research tracker #86 as absorbed if not already closed. Reassess #79/#80/#78 only from their own reproductions; do not claim they are fixed merely because this route changed.