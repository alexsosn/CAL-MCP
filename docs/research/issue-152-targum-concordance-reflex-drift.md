# Issue #152 research — Targum concordance and Hebrew-reflex page drift

Date: 2026-09-24. Base: `2a9a2c5e00c18e441b2fb79ec666dad2aba72bd7`.

## Trigger

The 2026-09-24 user-level MCP end-to-end run (#15) found both documented Targum examples failing with `parser_drift`:

- `cal_targum_concordance("klb N")`: "CAL Targum concordance heading does not match the submitted lemma";
- `cal_targum_hebrew_reflexes(targum="onqelos", mt_lemma_id="1751")`, with the ID returned by the working chooser: "CAL Targum reflex page lacks a complete source/result heading".

## Live-current evidence

Two bounded POSTs were made through the production `CalHttpClient` (project User-Agent, sequential):

| Request | Status | Bytes |
| --- | --- | --- |
| `POST showtargumKWIC.php` `lemma=klb&pos=N` | 200 | 7,402 |
| `POST getOmtlemma.php` `R1=1751` | 200 | 2,348 |

### Targum concordance (`showtargumKWIC.php`)

The page now uses CAL's modern layout:

- The identifying heading `CAL: Targum KWIC counts for klb N` is now only the document `<title>`. The body has **no `<h1>`**. It opens with `<h3>The lemma "klb N" is attested in the following number of verses in the targumic texts. Click the name of the targum to view the examples.</h3>`.
- The column header row is still `<th>Targum</th><th>Occurrences</th>`.
- The **section row** is now two `<td>` cells, `Torah` and `&nbsp;`, instead of one `<th colspan="2">`. Only `Torah` is rendered as a section. Former/Writing Prophets and the other groups are now ordinary linked rows.
- Result rows keep one `show1dialectKWIC.php` link plus a count. Both are now wrapped in `<div>` elements.
- The total `total examples: 59` is now a **single-cell row inside the table** instead of a paragraph after it. The row counts still sum to 59.
- One upstream example link ends with a truncated text selector (`texts=… 51019 5102`, "Writing Prophets"). It is CAL's own link and is passed through unchanged.

### Hebrew reflexes (`getOmtlemma.php`)

The semantics are unchanged; only markup changed:

- The heading `Onkelos correspondences to מַעֲקֶה` is now an `<h3>` (followed by `<h3>Click on the lemma to see the examples</h3>`) instead of an `<h1>`.
- The header row is now `<td>CAL lemma</td><td>frequency</td>` instead of `<th>` cells.
- The correspondence row is unchanged: `<a href="/getOMT.php?MT=1751&cal=tyq%232 N">תיק #2 N</a>` with frequency `2`. The `cal` value now contains a literal space instead of `+`, which parses to the same key.

## Consequences

- Result headings are collected from `<h1>` and `<h3>`. For the Targum concordance, CAL's current request-identifying heading is the page `<title>`, which is accepted as that heading. The body statement `The lemma "<key>" is attested …`, when present, must name the submitted key.
- A two-`<td>` row with a non-empty unlinked first cell and CAL's literal `&nbsp;` filler as its second cell is a label row (superseded detail: the first candidate accepted any empty second cell; see the review amendment). The earlier `<th colspan>` form remains accepted.
- A single-cell row whose text is `total examples: N` is the total. The one-total and row-sum checks are unchanged.
- The reflex header row may be `<th>` or `<td>`.
- Request counts and existing link/selector validation (#142/#144/#146) are unchanged. The public schema gains an additive `section_labels` field (review amendment, D-015; this supersedes the first candidate's "schema unchanged").

## Verification (2026-09-24)

- Offline, the full live captures parse: the concordance gives 21 rows summing to the total 59; the Onqelos reflex gives `tyq#2 N` / 2. A mutation pass that disables each new guard in turn (the statement key, section-row link, same-kind header row, and the title heading source) makes the tests fail every time.
- Live over MCP (a wheel built from this branch, stdio, 4 sequential requests):
  - `cal_targum_concordance("klb N")` → total 59, 21 rows;
  - `cal_targum_hebrew_lemmas("mem", "onqelos")` → 366 candidates;
  - `cal_targum_hebrew_reflexes("onqelos", "1751")` → `Onkelos`, `מַעֲקֶה`, `tyq#2 N` / 2;
  - `cal_targum_hebrew_reflexes("neofiti", "1751")` → `Neofiti`, `gypwp N` / 1, `syyg N` / 1.

## Review amendment (2026-09-24)

An independent review requested changes:

1. **Section attribution.** Carrying the current page's single `Torah` label forward attributed every later row to `Torah`, including Former and Writing Prophets, Psalms and Chronicles. This is an inference CAL does not make, and the docs wrongly denied it. As decided with the maintainer, current-layout label rows are no longer applied to rows (`section: null`). The result gains an additive `section_labels` list (`{label, row_index}`). The earlier `<th colspan>` layout still groups rows as before.
2. **Duplicate identical headings.** A repeated `<title>` (CAL's reflex page really repeats `<TITLE>`) or a `<title>` plus a matching body heading no longer fails; every identifying heading must name the submitted key.
3. **Damaged result rows.** A current-layout label row now requires CAL's literal `&nbsp;` filler in its second cell, so a result row that lost its link and count is still rejected ("row lacks required semantics") instead of becoming a label row.
4. **Total row.** A test now pins the exact `total examples: N` single-cell form.

A mutation pass over the new logic (the `&nbsp;` filler, heading dedupe, exact total row, labels not carried, labels recorded) failed the tests for each of those mutations. A second review then found three untested paths: the service's `section_labels` hand-off, `row_index` values other than 0, and accepting a page with no identifying heading. Each now has a test that fails when that path is disabled. On the full live capture, all 21 rows have `section: null` and `section_labels` is `[{"label": "Torah", "row_index": 0}]`.

### `section_labels` semantics

`row_index` is the index in `rows` of the first result row after the label. A label that follows the last row has `row_index == len(rows)`, and consecutive labels share one `row_index`.
