# Issue #77 plan — machine-readable shallow catalogue semantics

**Plan date:** 2026-09-10  
**Research:** `docs/research/issue-77-shallow-text-catalogue.md`

Sequence: research → plan → test-only RED → minimal implementation → dual GREEN → logically independent adversarial review → guarded merge.

## Goal

Prevent callers from treating the direct `texts` in `cal_text_catalogue()` as an exhaustive CAL corpus listing. Preserve the current one-request, non-recursive operation and all existing ordered result arrays.

## Frozen public contract

Add two fields to serialized `TextCatalogueResult`:

```text
recursive: boolean
has_unexpanded_children: boolean
```

For the current `cal_text_catalogue` operation:

- `recursive` is always `false`;
- `has_unexpanded_children` is `true` iff the returned level contains at least one ordinary `category` or `specialized_collection` navigation item;
- `has_unexpanded_children=false` means only that this returned level exposes no recognized child catalogue/specialized navigation. It MUST NOT be documented or modeled as proof that CAL as a whole has been exhaustively enumerated.

Do not add `complete`, `is_complete`, `exhaustive`, total-text counts, recursive expansion, or auto-pagination.

The fields are additive; `categories`, `texts`, `specialized_collections`, and `provenance` retain their current names, ordering, and semantics.

## Model design

Keep the metadata on `TextCatalogueResult`, not `TextCataloguePage` unless implementation requires a mechanical helper. The facts describe the public operation/traversal boundary and are derived after the current parser has already classified the returned level.

Recommended implementation:

```python
@dataclass(frozen=True, slots=True)
class TextCatalogueResult:
    categories: tuple[TextCategoryRef, ...]
    texts: tuple[TextRef, ...]
    provenance: TextProvenance
    specialized_collections: tuple[TextSpecializedCollectionRef, ...] = ()
    recursive: bool = False

    @property
    def has_unexpanded_children(self) -> bool:
        return bool(self.categories or self.specialized_collections)
```

Serialization should emit both values explicitly. An equivalent immutable implementation is acceptable if it avoids duplicated state that could become inconsistent.

Do not let callers set `recursive=True`; there is no recursive public operation. No new MCP input is added and the public tool count does not change.

## Gate 1 — TDD RED

After this plan is committed, tests only:

1. root catalogue serialization contains `recursive is False` and `has_unexpanded_children is True`;
2. a nested catalogue response containing an ordinary child category reports `has_unexpanded_children is True`;
3. a catalogue level containing only text entries reports `has_unexpanded_children is False`;
4. a root containing only a specialized collection still reports `has_unexpanded_children is True`;
5. the service sends exactly the same single request as before and performs no child fetch;
6. existing category/text/specialized ordering and provenance remain byte-for-byte/structurally unchanged apart from the two additive keys;
7. MCP input schema for `cal_text_catalogue` remains unchanged (`category_id` only); no `recursive` input appears;
8. release manifest/tool count remains unchanged;
9. docs contract requires explicit warning that `has_unexpanded_children=false` is not corpus-global completeness.

A valid RED requires both CI matrices to pass environment setup, Ruff lint/format, and strict mypy, then fail pytest only on these new response/docs expectations. Production remains unchanged at the RED SHA.

## Gate 2 — minimal implementation

Expected production scope: `src/cal_mcp/texts.py` only. No parser route, HTTP client, server registration, release manifest, cache namespace, or CAL request shape should need to change.

Implementation must derive `has_unexpanded_children` from already-returned typed navigation arrays and must not perform a request to determine it.

## Gate 3 — documentation

Update `docs/tools/texts.md` and any concise root capability example so machine and human callers receive the same semantics:

- every catalogue call is one level / `recursive=false`;
- root direct texts are not an exhaustive corpus list when child navigation exists;
- `has_unexpanded_children=true` means explicit follow-up navigation is present;
- `false` does not assert global completeness.

No release tool-count change is needed.

## Gate 4 — dual GREEN

On the exact final candidate require both deterministic and latest-compatible matrices to pass dependency checks, Ruff lint/format, strict mypy, and the complete pytest suite.

## Gate 5 — logically independent adversarial review

Review the exact GREEN SHA from scratch and challenge at least:

- whether either field overclaims global completeness;
- whether specialized collections count as unexpanded navigation;
- whether a text-only leaf falsely becomes a recursive/exhaustive claim;
- whether any input schema or request behavior changed;
- whether another CAL request/prefetch was introduced;
- whether existing serialized keys/order/provenance were disturbed;
- whether docs and executable semantics agree.

Any blocker gets its own regression RED, minimal fix, fresh dual GREEN, and a new exact-head review.

## Merge gate

Before merge, refetch `main`. If it advanced, synchronize and rerun required CI/review. Merge only the exact reviewed head using `expected_head_sha`.

## CAL load impact

Zero additional CAL requests. The feature is local response metadata over the existing one-level catalogue result.

## Execution evidence

- Test-only RED head `e4e614d73396802307c202bae1293a63a20f13a2` was validated in both CI matrices on 2026-09-11: dependency/setup, Ruff lint/format, and strict mypy passed; pytest reported **903 passed / exactly 5 failed**, all from `tests/test_shallow_text_catalogue_contract.py` and all attributable to the missing `recursive` / `has_unexpanded_children` response fields or their documentation.
- Minimal implementation changes only `TextCatalogueResult` serialization/derived metadata in `src/cal_mcp/texts.py`; documentation changes only `docs/tools/texts.md`. No CAL route, request shape, public input schema, tool count, release manifest, or automatic traversal behavior was changed.
- The next authoritative checkpoint is the human-authored head carrying this execution record; it must pass both CI matrices before independent review.
