# Issue #101 plan — discover and browse the Onkelos/Jonathan collection

**Plan date:** 2026-09-08
**Research:** `docs/research/issue-101-onkelos-jonathan-catalogue.md`

Sequence: research → plan → test-only RED → minimal implementation → full GREEN → docs → exact-head independent adversarial review → guarded merge.

## Frozen behavior

Use the existing `cal_text_catalogue` public contract. Do not add another MCP tool or a generic URL/route selector.

Represent CAL's dedicated Onkelos/Jonathan root link as an ordinary public text category bridge:

```text
TextCategoryRef(category_id="51", label=<CAL rendered label>)
```

Private routing becomes:

```text
cal_text_catalogue() -> GET newtextmenu.html
cal_text_catalogue(category_id="51") -> GET targum_onkelos_jonathan.html
cal_text_catalogue(category_id=<other decimal>) -> existing GET showsubtexts.php?subtext=<id>
```

The dedicated page's existing `showsubtexts.php` children stay categories and its existing `get_a_chapter.php` children stay direct texts. No recursive fetch occurs.

Do not add `cset=H`: bounded research confirmed the representative child catalogue/text semantics are the same without it.

## TDD RED gate

Add a focused offline test module/fixture before production changes.

### Root discovery RED

A reduced root fragment contains:

- one ordinary `showsubtexts.php` category;
- the current `targum_onkelos_jonathan.html` link with its rendered label.

Expect both categories in CAL order, with the specialized branch represented as `category_id="51"`. Current code drops it, so this is RED.

### Dedicated dispatch RED

A recording transport calls:

```text
TextService.catalogue(category_id="51")
```

Expect exactly:

```text
GET targum_onkelos_jonathan.html
```

Current code requests `showsubtexts.php?subtext=51`, so this is RED.

### Child-shape RED

A reduced dedicated-page fixture contains, in order:

```text
showsubtexts.php?cset=H&subtext=51001 -> 51001 TgO Gn
get_a_chapter.php?cset=H&file=51400 -> 51400 MegTan (Megillat Taanit)
```

Expect the first in `categories` and the second in `texts`. This pins the intended reuse of the generic parser and prevents an implementation that flattens both shapes into one type.

### Drift RED

A root fragment still rendering an Onkelos/Jonathan label but pointing to an unrecognized changed route must raise `TextParseError` rather than silently omit the collection while returning other ordinary categories.

Unrelated links remain ignorable.

A valid RED must have install, Ruff lint, Ruff format, and mypy green in both CI matrices, with pytest failing only on the new missing behavior.

## Minimal implementation

In `src/cal_mcp/texts.py`:

1. add a small constant for category `51` and the current dedicated path;
2. extend catalogue-category link interpretation to recognize the exact dedicated path and return `TextCategoryRef("51", label)`;
3. detect the recognizable Onkelos/Jonathan root label on a changed/unknown path and fail closed;
4. special-case only normalized category `51` in `TextService.catalogue()` request construction;
5. leave ordinary category parsing/routing and text-search specialization untouched.

Do not add new result fields, persistent mappings, background refresh, or child traversal.

## Documentation

Update:

- `docs/tools/texts.md`: root discovery includes the category-51 bridge; one follow-up opens the dedicated collection; direct/subdivided children remain distinct;
- `docs/tools/targum.md` if it states single-source discovery is already universally available without qualification;
- `docs/index.md` capability matrix if needed;
- append a dated correction note to `docs/research/issue-10-targum.md` explaining the discovery gap and #101 repair without rewriting the historical research record.

Tool count and public function signature remain unchanged.

## GREEN gate

Require exact-head success for both CI jobs:

```text
ruff check .
ruff format --check .
mypy
pytest
```

Normal tests remain offline.

No further live CAL requests are required after the committed research unless implementation behavior cannot be resolved from current evidence.

## Independent adversarial review

Freeze the final SHA and review the whole PR from the issue/research contract. Challenge:

- root specialized link can no longer disappear silently;
- changed specialized route fails closed without making unrelated links fatal;
- category 51 performs exactly one request to the dedicated page;
- ordinary categories still use `showsubtexts.php` unchanged;
- 51001 remains a category and 51400 remains a direct text;
- no unproven `cset=H` propagation was introduced;
- no Targum parallel/concordance/reflex behavior changed;
- docs describe discovery truthfully and do not imply hidden traversal.

Any blocker gets a regression RED and another exact-head review.

## Merge

After exact-head dual-matrix GREEN and independent approval, merge with `Closes #101`. #83 remains open for cross-collection discovery; #78/#97 remain separate Mandaic tickets.

## Execution record

- Original test-only RED: `55ae3c50a372083398c227740a90a279b6c7058c`; both static/type matrices green and pytest failed only on the three missing #101 behaviors.
- Initial implementation and documentation reached GREEN, then exact-head adversarial review found a label-drift completeness blocker: recognition depended on the current rendered label before the dedicated route.
- Review-regression RED: `6ef1597bd04837f8663828234742ed4b95525bbd`; both matrices passed install, Ruff, formatting, and mypy, with deterministic pytest **692 passed / exactly 1 intended failure**.
- The minimal correction now recognizes the exact dedicated route first, preserves any nonempty rendered label, and retains the old/current label as a fail-closed sentinel if it points to an unknown route.
- Temporary write-enabled implementation/sync helpers were removed from the final diff.
- The branch was non-destructively synchronized with current `main` at `381fb95725322640ed81302f8ca5bfa092920d4d` before the final CI/review gate.
