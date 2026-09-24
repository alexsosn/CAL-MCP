# Issue #149 research — concordance/KWIC live drift

Date: 2026-09-24. Base: `9e0a2dc6ed7324307e3f7d59b7a62f81839816ef`.

## Trigger

A user-level MCP end-to-end run on 2026-09-24 (installed `cal_mcp-0.1.0` wheel, stdio MCP client, live CAL) found all three concordance entry points failing with `parser_drift`:

| MCP call | Error |
| --- | --- |
| `cal_text_concordance("13250")` | CAL concordance lemma link text differs from its key |
| `cal_kwic_texts("mlk N", ["13250"])`, `cal_kwic_texts("by N", ["13250"])` | CAL KWIC total does not match parsed target hits |
| `cal_kwic_dialect("n)qh N", "6")` | CAL dialect KWIC total contradicts the request |

The fixed `live_smoke` release gate also fails at `text_concordance`. The last green live validation was 2026-09-08.

## Live-current evidence

Six bounded research requests were made through the production `CalHttpClient` (project User-Agent, sequential, one attempt each). Bodies were kept only in a local scratch area; the committed fixtures are reduced fragments:

| # | Request | Status | Bytes |
| --- | --- | --- | --- |
| 1 | `GET newconcord.php?text=13250&cset=S` | 200 | 6,183 |
| 2 | `POST showdialectKWIC.php` `lemma=by&pos=N&texts=13250&charset=R` | 200 | 2,734 |
| 3 | `GET show1dialectKWIC.php?lemma=n)qh&pos=N&texts=6` | 200 | 3,861 |
| 4 | `GET show1dialectKWIC.php?lemma=)ryk#2&pos=A&texts=3` | 200 | 4,462 |
| 5 | `GET show1dialectKWIC.php?lemma=n)qh&pos=N&texts=51` | 200 | 2,516 |
| 6 | `POST showdialectKWIC.php` `lemma=mlk&pos=N&texts=12250 13250&charset=R` | 200 | 4,417 |

### 1. One-text concordance: link text is now a display label

The `Frequencies of lemmas in text 13250` marker, the inline BR-delimited rows (R-022) and the `showKWIC.php?lemma=…&charset=S&texts=13250` link semantics are unchanged. The **link text** changed from the canonical lemma key to CAL's display label for most rows:

```text
4:....<a href="/showKWIC.php?lemma=%29b+N&charset=S&texts=13250">ˀb, ˀbˀ n.m.</a>: father
1:....<a href="/showKWIC.php?lemma=%29x%29b+PN&charset=S&texts=13250">)x)b PN</a>: proper noun
```

Proper-noun rows still show the key. The label is a CAL presentation string (headwords plus POS abbreviation) that cannot be derived deterministically from the key, so equality with the key is no longer a valid consistency check. The key remains available, validated, in the link's `lemma` parameter.

### 2. KWIC hits are BR-delimited lines, not table rows

Both `showdialectKWIC.php` (text scope) and `show1dialectKWIC.php` (dialect scope) now render each hit as three `<br>`-delimited lines inside a `mono` span or a `<p>`: a context-before line (`coordinate text`), the **target line** (`<a href="/get_a_kwicchapter.php?file=…&sub=…&cset=…&target=…">coordinate</a> text …` with the target token in `<b>`), and a context-after line. Hits are separated by an empty spacer span. No hit is inside a `<table>`, so the table-row hit parser finds zero hits while CAL's total is positive.

The text-scope markers are unchanged: the heading `Looking for mlk N in dialect 12250 13250`, per-text `12250:` headers, `no examples found in 12250`, and `total examples: 6` (6 target links, including the duplicated target `1325006` for two occurrences in one line).

In the dialect page the target anchor contains a `span` with a `title` reference (for example `Ezra 4:14; Biblical Aramaic: Ezra`). Its visible text is the target coordinate, which matches the link's `target` parameter.

Because a hit's neighbouring lines are not structurally delimited from other hits' lines or from per-text headers (a first-line target has no before-line, and spacer spans may render as nothing), attaching before/after lines to a hit cannot be done unambiguously. The unambiguous per-hit context is CAL's rendered **target line**, excluding its coordinate. Neighbouring lines remain available through `cal_kwic_full_context`.

### 3. Dialect KWIC now reports results per lemma form, with a new charset

`show1dialectKWIC.php` groups results by **form**, where CAL includes related spellings of the requested lemma:

```text
Looking for n)qh N in 6
No examples found for n)qh N in dialect 6
[hit lines]
1 example found for nqh N in dialect 6
Grand total: 1 example across all forms
```

- Each form has exactly one summary line: `N example(s) found for <key> in dialect <id>` placed **after** that form's hit lines, or `No examples found for <key> in dialect <id>` with no hit lines.
- A form summary can precede the explanatory "Click on the target line…" line.
- `Grand total: N example(s) across all forms` appeared when two forms were reported and one had hits (request 3). It was absent when there was only one form (request 4) and when both forms had zero hits (request 5: `No examples found for n)qh N …` and `No examples found for nqh N in dialect 51`).
- The requested form appeared exactly once in every capture.
- The Syriac hit link uses `cset=U`, a charset outside the previously accepted `R`/`H`/`S`. Request 3's link is `get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323`.

The old parser read the single `found for` line as the dialect total and rejected it because its key (`nqh N`) differed from the requested key (`n)qh N`). Returning such hits as if they were `n)qh N` hits would misrepresent CAL. Dropping them would discard CAL output. The faithful representation keeps every hit, labels it with CAL's form key, and exposes the per-form counts.

## Consequences (decided 2026-09-24 with the maintainer)

- `ConcordanceLemma` gains `label`: CAL's displayed link text. `lemma_key` is still taken only from the validated link.
- KWIC hit parsing gains a BR-line mode used when no table-row hits exist. The table parser remains a strict compatibility fallback for the earlier layout (as in R-022). In line mode a hit line must carry exactly one full-context link whose text equals the `target` parameter and which starts the line, and it must have non-empty rendered text after the coordinate.
- `cal_kwic_dialect` results gain `forms` (ordered `{lemma_key, total}` per CAL form summary), and each hit gains `form_lemma_key`. Validation:
  - every summary names the requested dialect;
  - every form key is canonical;
  - forms are unique;
  - the requested form appears exactly once;
  - hits lie between the previous summary and their own form's `found` summary, and their number equals that summary's count;
  - a `No examples` form owns no hits;
  - no hit follows the last summary;
  - an optional single `Grand total` must equal the sum.
  
  `total` is the sum over forms. An all-zero page is a valid empty result with `empty_scope_ids = [dialect_id]`.
- Text-scoped results return `forms: []` and `form_lemma_key: null`, because CAL does not report forms there.
- `U` is accepted as a CAL KWIC hit charset and as a `cal_kwic_full_context` charset.
- Public schema changes are additive only. Request counts, caching and bounds are unchanged.

## Not changed / follow-ups

- The dialect hit `title` reference (for example `Ezra 4:14; …`) is not exposed. It is presentation metadata, and CAL identity is already carried by `file_id`/`subtext_id`/`target_coordinate`. It can be proposed separately.
- `response_too_large` for large lemma/dialect pages (for example `br N` in dialect 6) is the 2 MiB policy working as designed; it is documented as a limitation.

## Live verification of the fix (2026-09-24)

A wheel built from this branch was installed and driven over stdio through MCP against live CAL (6 requests, sequential):

- `cal_text_concordance("13250")`: found, with rows such as `)b N` / label `ˀb, ˀbˀ n.m.`;
- `cal_kwic_texts("by N", ["13250"])`: total 1, target `1325009`;
- `cal_kwic_texts("mlk N", ["12250", "13250"])`: total 6, `empty_scope_ids == ["12250"]`;
- `cal_kwic_dialect("n)qh N", "6")`: total 1; forms `n)qh N`/0 and `nqh N`/1; the hit has `form_lemma_key: "nqh N"`, `charset: "U"`;
- `cal_kwic_full_context` succeeded for an `R` hit (`13250`/`1325009`) and a `U` hit (`60301`/`53`/`603015323`).

`python -m cal_mcp.live_smoke` then completed all eight cases using exactly 9/9 CAL requests.

## Review amendment (2026-09-24)

An independent review of the first candidate raised these points; the resolutions are:

- **Target token.** Each current target line highlights exactly one token in `<b>` (verified on a full 421-hit capture of `br N` in text `51001`: 421 target links, 421 highlighted tokens plus one `<b>51001:</b>` header). Without it, two occurrences on one line (`1325006`, `mlky` and `ml?[kN`) become identical hits. Hits now carry an additive `target_text`, and a BR-line target line without exactly one highlighted token fails closed.
- **Line structure.** A structural pass checks that nothing precedes the target link on its line, and that each text-scoped hit sits under its own `<b>NNNN:</b>` section header. The header stays the plain file ID for texts with subtexts (`51001:` for hits with `sub=03` … `sub=50`). A missing `<br>` that merges the following line into a target line is not detected: the only signal would be a digit-run heuristic that could reject legitimate text.
- **`U` full context.** A reduced live capture of `get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323` is now an offline fixture. It parses without the Hebrew-only empty-anchor accommodation.
- **Documentation and decisions.** The MCP tool descriptions now describe forms and `target_text`. `wiki/decisions.md` D-014 records the per-form `total` semantics, and the fixture README lists the new fixtures.

Two additional research requests were made for this amendment: `POST showdialectKWIC.php` (`br N`, text `51001`, 210 KB) and the `U` full-context page (24 KB). The `klb N`/`51001` probe (no examples) confirmed the header format for an empty Targum text.

## Second review amendment (2026-09-24)

An independent subagent review of `d666743` found no parser correctness defects against the full raw captures, and asked for:

- **Negative tests for every new fail-closed branch.** Each guard now has a test pinned with `match=`. A mutation pass that disables each guard in turn (16 guards) makes the tests fail every time. The empty-label check is reachable only on the table layout, so it is tested there.
- **Line merge on dialect pages.** Dialect before/after lines start with a `span.mono` coordinate. Such a span after the target link now fails closed ("runs into another line"). Text-scope pages have no such marker, so the digit-run limitation noted above still applies there.
- **Docs.** The dialect `total` is described as the per-form sum (CAL's grand total when rendered), and the old-layout `forms: []` case is documented.

Accepted, not changed: the summary-hint guard (`found for` / `grand total`) is applied to all page lines, including KWIC context lines, so an English context line containing those words would fail closed rather than parse. Every observed context line is Aramaic/Syriac/Hebrew text or transliteration, and failing closed is the safe direction. Thousands separators in counts were not observed; a count such as `1,000` would fail closed.

The reviewer's CHANGELOG concern assumed `v0.1.0` had been released. It has not: the only `v0.1.0` tag was a local leftover from a refused push, and it has been deleted. The 0.1.0 entry describes the release that will include this fix.
