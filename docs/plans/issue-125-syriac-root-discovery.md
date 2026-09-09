# Issue #125 plan — operation-aware Syriac root discovery

**Plan date:** 2026-09-10  
**Research:** `docs/research/issue-125-syriac-root-discovery.md`  
**Baseline:** `main` at `ee37a443f5d40a688f76ed9943cbf4a9e3f50079`

Sequence: research → plan → deterministic RED → minimal implementation → docs → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen public contract

Keep the existing input tool and tool count:

```text
cal_text_catalogue(category_id: string | null = null)
```

Add one output collection:

```text
specialized_collections: [
  {
    collection_key: string,
    label: string,
    follow_up_tool: string,
    selector_name: string,
    supported_selectors: string[]
  }
]
```

Current root Syriac entry:

```text
collection_key = "syriac"
label = <CAL rendered root label>
follow_up_tool = "cal_syriac_texts"
selector_name = "category"
supported_selectors = <keys of the live service's configured Syriac text categories>
```

These metadata fields are CAL-MCP routing metadata, not CAL identifiers. Existing `categories`, `texts`, and `provenance` remain unchanged.

## Model changes

In `src/cal_mcp/texts.py` add:

```python
@dataclass(frozen=True, slots=True)
class TextSpecializedCollectionRef:
    collection_key: str
    label: str
    follow_up_tool: str
    selector_name: str
    supported_selectors: tuple[str, ...]
```

Add `specialized_collections` to `TextCataloguePage` with an empty tuple default so existing internal constructors remain source-compatible.

Add `specialized_collections` to `TextCatalogueResult` after `provenance`, also with an empty tuple default. Include it in `to_dict()` as a JSON list before provenance.

No existing field changes type or meaning.

## Selector-source change

In `src/cal_mcp/syriac.py` add a read-only helper after `_TEXT_CATEGORIES`:

```python
def syriac_text_category_slugs() -> tuple[str, ...]:
    return tuple(_TEXT_CATEGORIES)
```

`texts.py` imports this helper. Do not copy the 20 slugs into a second production constant.

The helper performs no I/O and returns insertion order, which is the service configuration order already rechecked against current `AvailSyr.html`.

## Root route constants

In `texts.py` add private constants:

```python
_SYRIAC_COLLECTION_KEY = "syriac"
_SYRIAC_ROOT_PATH = "AvailSyr.html"
_SYRIAC_ROOT_LABEL = "Syriac"
_SYRIAC_FOLLOW_UP_TOOL = "cal_syriac_texts"
_SYRIAC_SELECTOR_NAME = "category"
```

## Parser change

Add `_specialized_collection_from_link(link)` and call it from `parse_text_catalogue_page()` before ordinary category/text parsing.

Exact recognized route:

- relative only (`scheme` and `netloc` empty);
- path exactly `AvailSyr.html` or `/AvailSyr.html`;
- no query;
- no fragment;
- nonempty rendered label.

Return one `TextSpecializedCollectionRef` populated with `syriac_text_category_slugs()`.

Fail closed when:

- the exact local `AvailSyr.html` route has query/fragment controls or an empty label;
- a link whose rendered label is exactly `Syriac` points to a changed path, nested suffix lookalike, query-bearing variant, or foreign origin;
- the same `collection_key` appears twice in one catalogue page.

Unrelated links remain ignored by this specialized parser.

`parse_text_catalogue_page()` should succeed when any of categories, texts, or specialized collections is nonempty. It must continue preserving each collection's own CAL order.

## Service/result propagation

`TextService.catalogue()` does not change request dispatch for root, category 51, category 74, or ordinary categories.

Propagate `result.value.specialized_collections` into `TextCatalogueResult`.

Therefore root remains exactly one `GET newtextmenu.html` logical request on a cache miss. No `AvailSyr.html` prefetch is added.

## Gate 1 — deterministic RED

Create `tests/test_syriac_root_discovery.py` after research/plan commits.

RED expectations:

1. root fixture containing ordinary category 3, category-51 route, exact `AvailSyr.html`, and Mandaic category-74 route preserves the existing three decimal categories and separately returns one Syriac specialized collection;
2. specialized item fields exactly name collection `syriac`, follow-up `cal_syriac_texts`, selector `category`, and `supported_selectors == syriac_text_category_slugs()`;
3. selector list includes the current 20 configured slugs in stable order and contains no synthetic decimal category id;
4. exact route preserves a changed nonempty rendered label;
5. `Syriac` label with wrong path, nested path, query, fragment, or foreign absolute route fails closed;
6. exact route with empty rendered label fails closed;
7. duplicate exact Syriac routes fail closed;
8. a root service call with a recording transport emits only `GET newtextmenu.html`; no `AvailSyr.html` request occurs;
9. non-root ordinary catalogue result has `specialized_collections == ()` / serialized `[]`;
10. existing category-51/category-74 dispatch tests remain unchanged and pass;
11. normal CI remains offline.

Accepted RED must be Ruff-format/lint and strict-mypy clean in both matrices; pytest failures must be limited to the absent specialized-collection behavior.

## Gate 2 — minimal implementation

Expected production changes:

- `src/cal_mcp/syriac.py`
- `src/cal_mcp/texts.py`

No changes to:

- server tool signatures;
- shared HTTP client;
- Syriac category/group parsers or routing;
- Mandaic/Onkelos routing;
- release tool count/surface.

## Gate 3 — documentation

Update:

- `docs/tools/texts.md`: explain `specialized_collections`, root Syriac reference, one-request bound, and that selector values are local supported follow-up selectors rather than fake CAL category IDs;
- `docs/tools/syriac.md`: show root `specialized_collections` → explicit `cal_syriac_texts(category=...)` workflow;
- `docs/index.md`: correct the capability/reachability matrix so Syriac root discovery is no longer described/implied as silently absent once behavior lands.

Do not claim that root discovery fetched or enumerated `AvailSyr.html`.

## Gate 4 — GREEN

Require deterministic and latest-compatible matrices to pass dependency checks, Ruff lint, Ruff format, strict mypy, and full pytest on the exact candidate SHA.

Freeze changed-file scope before review.

## Gate 5 — logically independent adversarial review

Review the exact GREEN head from current CAL evidence, issue, research, and raw diff. Challenge:

1. synthetic CAL ID leakage;
2. whether selectors truly come from the same config consumed by `SyriacService.texts`;
3. exact root route/origin/query/fragment fail-closed semantics;
4. duplicate specialized references;
5. backward compatibility of existing catalogue fields/constructors/serialization;
6. root one-request/no-prefetch behavior;
7. preservation of category 51 and 74 semantics;
8. actionable selector/follow-up metadata without arbitrary URL execution;
9. docs distinguishing CAL-rendered label from CAL-MCP routing metadata;
10. no release-surface/tool-count drift;
11. normal CI offline hygiene.

Any blocker receives focused regression coverage, a minimal correction, dual GREEN, and a fresh exact-head review.

## Merge / umbrella gate

Before merge refetch `main`; synchronize if it advanced; require GREEN + clean review on synchronized head; mark ready and squash-merge guarded by exact head SHA.

After merge:

- confirm #125 closes;
- update #83/#103 with the new classification;
- recheck whether any specialized root Text Browse route remains unrepresented before deciding whether #83 can close.

## CAL load impact

Zero new production requests. Root discovery stays one CAL request; selector enrichment is local deterministic configuration and child Syriac surfaces remain explicit follow-ups.
