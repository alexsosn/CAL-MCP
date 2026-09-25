# Issue #176 research — dialect KWIC pages that omit the requested form

Date: 2026-09-25. Base: `1b06fa2`.

## Trigger

The 2026-09-25 user-level MCP end-to-end run (#15) found that `cal_kwic_dialect("n)qh N", "71")` (Babylonian Talmud) fails with `parser_drift` "CAL dialect KWIC lacks the requested form summary". The per-form model of D-014 (#149) requires the requested form's summary to appear exactly once.

## Live-current evidence

Four bounded requests through the production `CalHttpClient` (project User-Agent, sequential), all for `n)qh N` via `show1dialectKWIC.php`, in dialects 71 (captured in the end-to-end run), 51, 53 and 3.

| Dialect | CAL's per-form summaries |
| --- | --- |
| 6 (#149 fixture) | `n)qh N` 0, `nqh N` 1 |
| 51, 53, 3 | `n)qh N` 0, `nqh N` 0 |
| **71** | **`n)qt) N` 1, `nqh N` 0**, and no summary for `n)qh N` |

Dialect 71's page:

```html
<div …>Looking for <b>n)qh N</b> in 71<br></div>
… <a href="/get_a_kwicchapter.php?file=71002&sub=01051&cset=H&target=7100201051217" …>7100201051217</a> "מאי נאקה בחטם"; <b><span class="red">נאקתא</span></b> …
<div dir="ltr" …><b>1</b> example found for <b>n)qt) N</b> in dialect 71</div>
<div dir="ltr" …>No examples found for <b>nqh N</b> in dialect 71</div>
```

In dialect 71, CAL answers the request with the forms it groups with `n)qh N` there, including JBA's own spelling `n)qt) N`. It renders no summary for the requested spelling at all. That is CAL's own grouping. Nothing on the page contradicts itself: the counts, positions and dialect all agree.

## Consequences (D-014 amendment)

- A per-form page may omit the requested form. It is then accepted, and the result states this explicitly with a new additive field `requested_form_listed: false`. The field is `true` when CAL lists the requested form, and `null` where CAL renders no per-form summaries (text-scoped KWIC and the earlier dialect layout).
- Every hit keeps CAL's own `form_lemma_key`. A hit is never attributed to the requested key, and CAL-MCP does not invent a zero-count summary for the omitted form.
- `total` is still the sum of CAL's per-form counts. `empty_scope_ids` still names the dialect only when every listed form has zero examples.
- All other cross-checks are unchanged: counts against rendered hits, positions, dialect, canonical keys, uniqueness and the grand total. A page with no summaries on the per-form layout still fails closed.
- Request counts are unchanged.
