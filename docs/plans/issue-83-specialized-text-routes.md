# Issue #83 plan — expose CAL specialized text collections through existing text discovery

**Plan date:** 2026-09-08

This ticket follows research → plan → test-only RED → minimal implementation → full GREEN → user-documentation correction → exact-head logically independent adversarial review → guarded merge.

The research gate is satisfied by `docs/research/issue-83-specialized-text-routes.md`.

## Problem to solve

The current `cal_text_catalogue` parser accepts a root page as successful once it sees any ordinary `showsubtexts.php` or `get_a_chapter.php` links. Current CAL's root also contains three semantically important dedicated collection links that the parser silently drops:

- Targums Onkelos/Jonathan -> `targum_onkelos_jonathan.html`;
- Syriac -> `AvailSyr.html`;
- Mandaic -> `show_Mandaic.php?R1=74`.

In addition, `TextService.catalogue(category_id=...)` always dispatches to `showsubtexts.php?subtext=<id>`, so the Mandaic collection (`74`) cannot be opened faithfully and the current Onkelos/Jonathan collection page has no generic-text catalogue route.

## Contract decision

Do **not** add a new MCP tool. This is a release-blocking correctness/discoverability repair to the existing text-discovery contract.

Extend `cal_text_catalogue` results with an explicit `collections` list while preserving the existing `categories`, `texts`, and `provenance` fields.

Each collection record is adapter-level navigation metadata derived from CAL's current root page, not a copied corpus index. It should contain:

- a stable adapter `collection_id`;
- CAL's current display `label`;
- the public CAL-MCP `follow_up_tool`;
- an optional `category_id` when the collection is intentionally bridged into `cal_text_catalogue`.

Initial current collection mapping, grounded by the research artifact:

| `collection_id` | CAL root route | `follow_up_tool` | `category_id` |
| --- | --- | --- | --- |
| `targum-onkelos-jonathan` | `targum_onkelos_jonathan.html` | `cal_text_catalogue` | `51` |
| `syriac` | `AvailSyr.html` | `cal_syriac_texts` | none |
| `mandaic` | `show_Mandaic.php?R1=74` | `cal_text_catalogue` | `74` |

`51` is CAL's current Jewish Literary Aramaic/Onkelos-Jonathan collection code; it is used only as the public bridge selector for this dedicated collection page. `74` is the current Mandaic collection selector already reported in #78.

The public root catalogue remains shallow and bounded. Returning a collection reference does not fetch that collection.

## Private catalogue dispatch

Keep ordinary numeric categories unchanged:

```text
category_id=<ordinary> -> GET showsubtexts.php?subtext=<ordinary>
```

Add only the two researched dedicated dispatches:

```text
category_id=51 -> GET targum_onkelos_jonathan.html
category_id=74 -> GET show_Mandaic.php?R1=74
```

Both are exactly one CAL request and reuse the generic catalogue parser for their child `showsubtexts.php` / `get_a_chapter.php` links.

Do not propagate or invent `cset` parameters as part of this issue. Current CAL places `cset=H` on already-working ordinary direct text links such as Tel Dan, so its mere presence is not evidence that request construction is wrong. Any selector that proves semantically required gets a focused failing regression first.

## Mandaic issue ownership

This PR may close #78 because `category_id=74` becomes a faithful one-request route to the current dedicated Mandaic catalogue and the root collection becomes discoverable. It must **not** absorb #97: mixed direct/subdivided Mandaic text-page routing is a separate page-retrieval defect with different semantics.

## TDD RED gate

Commit tests/fixtures after this plan and before production changes.

### 1. Root specialized-collection discovery

Add a minimal root fixture containing:

- one ordinary `showsubtexts.php` category;
- one ordinary direct `get_a_chapter.php` text;
- `targum_onkelos_jonathan.html`;
- `AvailSyr.html`;
- `show_Mandaic.php?R1=74`.

RED assertion: parsing returns all three collection references in CAL order while preserving ordinary categories/texts. Current code has no collection representation and therefore fails.

### 2. Dedicated catalogue dispatch

Add service-level REDs proving:

- `catalogue(category_id="51")` performs exactly `GET targum_onkelos_jonathan.html`;
- `catalogue(category_id="74")` performs exactly `GET show_Mandaic.php` with `R1=74`;
- an ordinary category such as `3` still performs `GET showsubtexts.php?subtext=3`.

The test transport returns minimal semantic fragments for each route. Current service dispatch fails the first two tests.

### 3. Drift/malformed specialized route

Add a parser regression for the known Mandaic route family with a mismatched/malformed selector, e.g. `show_Mandaic.php?R1=75`. The parser must raise `TextParseError` rather than silently accepting a page while losing a known-specialized link.

Do not fail on arbitrary unrelated links merely because they are not text routes; CAL pages can contain reference/navigation links outside this contract.

### 4. Public serialization contract

Assert `TextCatalogueResult.to_dict()` exposes `collections` with stable field names and keeps the pre-existing keys. This guards MCP structured output without creating a new tool.

A valid RED commit changes only tests/fixtures and must fail for the intended missing behavior.

## Minimal GREEN implementation

In `src/cal_mcp/texts.py`:

1. add a frozen `TextCollectionRef` model;
2. add `collections` to `TextCataloguePage` and `TextCatalogueResult`;
3. serialize collection records deterministically;
4. recognize only the three researched root specialized routes;
5. validate the known Mandaic `R1=74` selector rather than accepting arbitrary `show_Mandaic.php` queries;
6. add explicit private dispatch for category `51` and `74`;
7. preserve ordinary catalogue parsing and routing byte-for-byte where practical.

No recursive fetch, child prefetch, background discovery, new cache layer, or arbitrary-URL execution is introduced.

## Public/server surface

Keep the public function signature:

```text
cal_text_catalogue(category_id: str | None = None)
```

Update its description/instructions so callers understand:

- root output may contain ordinary `categories`, direct `texts`, and specialized `collections`;
- a collection's `follow_up_tool` is explicit;
- only collection records with `category_id` should be passed back to `cal_text_catalogue`;
- Syriac discovery intentionally points to `cal_syriac_texts` rather than duplicating the Syriac parser.

Tool count remains unchanged.

## Documentation corrections

Update in the same PR:

- `docs/tools/texts.md` — root collection records, bounded follow-up examples, dedicated category 51/74 dispatch semantics;
- `docs/index.md` capability matrix — correct the overly broad statement that single-Targum browsing is already fully discoverable through ordinary text tools; after this fix, document the explicit collection bridge;
- `docs/tools/targum.md` if it repeats the old discovery claim;
- `docs/concepts/cal-identifiers.md` if it currently implies every category ID maps to `showsubtexts.php`;
- `README.md`/server instructions only where needed for truthful discovery guidance;
- append a dated correction note to `docs/research/issue-10-targum.md` rather than rewriting historical evidence invisibly.

No version/tool-count bump is required.

## Verification/GREEN gate

Run at minimum:

```text
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
pytest
```

If the repository CI tests both dependency matrices, require both exact-head CI jobs green before review/merge.

Normal tests remain offline.

A tiny opt-in live verification may perform at most:

1. root Text Browse;
2. category 51 dedicated collection;
3. category 74 dedicated collection.

It must not follow child categories/texts automatically.

## Independent adversarial review gate

Freeze the exact final SHA and review from the issue/research artifacts, not from implementation intent.

The reviewer must challenge at least:

- Did the root parser still silently lose any current dedicated collection link from the researched root?
- Can arbitrary/malformed `show_Mandaic.php` selectors be mistaken for the supported Mandaic collection?
- Does category 51/74 dispatch perform exactly one request and preserve provenance?
- Did ordinary category routing change unintentionally?
- Does `collections` leak raw CAL URLs or HTML/form details into the public contract unnecessarily?
- Does Syriac point to the existing dedicated tool instead of duplicating it?
- Are Targum docs now truthful about source discovery?
- Did the implementation make any unproven `cset` assumption?
- Does the PR accidentally overlap #97's Mandaic page-routing scope?
- Are tests reduced semantic fixtures rather than captured corpus pages?

Any review-discovered behavior defect gets a review-regression RED before the production fix. Re-run the full gates and review the new exact head.

## Merge/handoff

After approval and green exact-head CI:

- merge #83;
- close #78 as completed by the dedicated Mandaic catalogue bridge if its acceptance criteria are fully met;
- leave #97 open for mixed Mandaic page routing;
- file a focused follow-up only if live/independent review proves an additional route selector is required.

## CAL load impact

Production root discovery remains one CAL request. Opening category 51 or 74 remains one explicit caller-requested CAL request. No operation automatically traverses from root -> collection -> text -> chapter.
