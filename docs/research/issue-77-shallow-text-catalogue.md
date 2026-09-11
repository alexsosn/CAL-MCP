# Research: explicit shallow semantics for CAL text catalogue

**Issue:** #77  
**Research date:** 2026-09-10  
**Baseline:** current `main` when branch `issue-77-shallow-catalogue` was created

## Question

How should CAL-MCP make it machine-readable that `cal_text_catalogue()` returns one navigation level rather than an exhaustive corpus list, without introducing recursive traversal or changing CAL request behavior?

## Current executable contract

`TextService.catalogue(category_id=None)` performs one `GET newtextmenu.html`; a category call performs one explicit dedicated or `showsubtexts.php` request. `TextCatalogueResult` currently serializes `categories`, `texts`, `specialized_collections`, and `provenance`.

The user documentation already says that the operation is one-level and non-recursive, but the structured result itself contains no field expressing that boundary. A caller looking only at JSON can therefore read the root's direct `texts` array as if it were the complete text inventory.

The recent specialized-discovery work makes the ambiguity more important: root results deliberately mix direct texts, expandable ordinary categories, and operation-aware specialized collections. Those are three different children of one shallow navigation node, not three exhaustive inventories.

## What the result can know without another CAL request

The adapter can state two facts deterministically from the operation contract:

1. the returned page is a **single catalogue level** (`recursive = false`);
2. whether this particular result exposes explicit unexpanded child navigation (`categories` or `specialized_collections` non-empty).

It cannot safely claim that a leaf-looking page is globally exhaustive merely because no child category was recognized: CAL could add another route family or markup could drift. Therefore a field named `complete` / `is_complete` would invite a stronger claim than the adapter can prove.

## Candidate representations

### `is_shallow: true`

Directly mirrors the issue wording but is a constant property of every current catalogue call. It tells callers that the result is not recursively expanded, but does not make the actionable next step explicit.

### `recursive: false`

Precise, simple, and additive. It describes the traversal performed by this call rather than making an unverifiable statement about corpus completeness. It is meaningful on root and child catalogue calls.

### `has_unexpanded_children: bool`

Useful as an additional derived navigation signal. It can be `true` exactly when `categories` or `specialized_collections` are returned. It should not be used alone: `false` means no explicit child-navigation item was returned on this page, not that the entire CAL corpus has been exhaustively traversed.

### free-form navigation guidance only

Already present in docs and therefore insufficient for machine callers. Repeating a prose warning in every result would also be less stable than typed fields.

## Recommended contract

Add two backward-compatible structured fields to `TextCatalogueResult`:

```text
recursive: false
has_unexpanded_children: boolean
```

Semantics:

- `recursive` is always `false` for the current public operation. It means this response contains only the one CAL catalogue level explicitly requested.
- `has_unexpanded_children` is derived locally as `bool(categories or specialized_collections)` and requires no upstream request.
- Neither field claims global completeness.
- Existing arrays and provenance remain unchanged and ordered.

The root response that motivated #77 will therefore explicitly say that it is non-recursive and has unexpanded children. A leaf-looking child still says `recursive: false`, avoiding an unsupported exhaustive-corpus claim.

## Request/load impact

None. This is response metadata derived from already parsed data. No new endpoint, recursive fetch, prefetch, cache key, retry, or concurrency behavior is required.

## Compatibility and tests

The change is additive at serialization level. Tests should pin:

- root: `recursive is False`, `has_unexpanded_children is True`;
- ordinary nested category with further categories: same;
- a fixture-backed leaf containing only texts: `recursive is False`, `has_unexpanded_children is False`;
- no extra transport request compared with existing catalogue behavior;
- existing category/text/specialized ordering and provenance unchanged;
- docs explicitly say `has_unexpanded_children=false` does not prove corpus-global completeness.

No production code should change until a focused plan is committed and test-only RED is demonstrated.
