# Issue #340 — research inventory for all-tool live acceptance

**Date:** 2026-11-15. **Baseline:** `679d825beb0a250a2db48907f3d34b1b9d73dadf` (main after #336/#337), `0.2.0.dev0`. Sources: `src/cal_mcp/release_surface.py`, `src/cal_mcp/stdio_live_smoke.py`, `docs/tools/*`, `docs/research/issue-262-slow-acceptance.md`, `docs/research/issue-338-coverage.md`, and the reviewed release CI.

The release's 13 fixed cases cover **12 distinct** of 37 tools (one is a local converter); **25 distinct CAL-backed tools** lack a dedicated live case. A passing pre-v0.2 fixed smoke cannot be upgraded to 37/37 live acceptance without testing these paths.

## Candidate one-operation probes: source-backed examples, not yet executed

| Family | Tool | Candidate / dependency from current user docs | Extra network considerations |
| --- | --- | --- | --- |
| Lexicon | `cal_lexicon_browse` | one bounded prefix `br` | one browse page, no pagination |
| Lexicon | `cal_lexicon_citation_context` | pass one **validated** non-null `full_coordinate` from an explicit `cal_lexicon_lookup` result | source lookup has two requests; cannot invent coordinate |
| English search | `cal_gloss_field` | `field="medicine"` | one indexed search request |
| English search | `cal_citation_text_search` | `query="camel"` | one literal short query |
| Texts | `cal_text_catalogue` | root, no `category_id` | one page |
| Texts | `cal_text_information` | `file_id="13250"` (Tel Dan reference) | one info page |
| Texts | `cal_text_line_comments` | one exact CAL line `coordinate` returned by `cal_text_page(file_id="13250")` | one page precursor; do not invent handle |
| Texts | `cal_token_analysis` | one word coordinate+index from a returned `cal_text_page`; or previously reviewed `7102601002203`, index `0` from `docs/getting-started.md` | one token, never whole passage |
| KWIC | `cal_kwic_texts` | one returned canonical lemma key, one CAL `text_id`; candidate Tel Dan `13250` | avoid noncanonical or unrelated lemma |
| KWIC | `cal_kwic_dialects` | one canonical lemma key from CAL lookup | selector only, no traversal |
| KWIC | `cal_kwic_dialect` | choose exactly one returned `dialect_id` | dependent on previous selector |
| KWIC | `cal_kwic_full_context` | exact `file_id`, `target_coordinate`, `charset`, optional `subtext_id` from a single returned hit | requires positive hit; never infer coordinate |
| Bibliography | `cal_bibliography_authors` | one 1–6 character author prefix | lookup choices only |
| Bibliography | `cal_bibliography_author` | choose one returned exact author `value` | depends on author selector |
| Bibliography | `cal_bibliography_keyword` | choose one exact CAL text/subject tag from returned bibliography links | no guessed fuzzy keyword |
| Targum | `cal_targum_concordance` | fixture-backed `lemma_key="klb N"` | one count table |
| Targum | `cal_targum_concordance_examples` | same `klb N` plus one returned `text_ids` group | source-returned IDs only |
| Targum | `cal_targum_hebrew_lemmas` | `initial="mem", targum="onqelos"` | one selector page |
| Targum | `cal_targum_hebrew_reflexes` | `mt_lemma_id` from previous chooser; historical fixture `1751` | one selected lemma |
| Targum | `cal_targum_reflex_examples` | one returned reflex `lemma_key` with same `mt_lemma_id` | no guessed example links |
| External citations | `cal_external_citation_sources` | one returned dialect ID; fixture-backed `6` (Syriac) | one source list |
| External citations | `cal_external_citations` | one returned source abbreviation; fixture-backed `1CorH` | one citation list |
| Syriac | `cal_syriac_texts` | one category, e.g. `metrical-homilies-hymns` | one page |
| Syriac | `cal_syriac_group` | one returned grouped-text `group_id` with `navigation_kind="group"` | requires choice from selected category |
| Syriac | `cal_syriac_missing_words` | one category e.g. `verbs` | one list |

Total untested distinct tool identities: **25**. Dependencies introduce additional CAL calls; it would be unsafe to assert that 25 tools fit within the existing strict **25 actual transport attempt** ceiling. Use separately reviewed **sequential** batches with one server and maximum 25 actual transport starts per batch, no more than eight starts per rolling 60 s, >=60-second completion spacing, zero retry, and immediate terminal 429 handling.

## Acceptance and failure interpretation

Each operation must complete through a freshly installed MCP stdio executable with the published output schema; compare the exact tool name, success/expected status, machine-readable content shape, CAL source origin and timezone-aware retrieved timestamp. Some CAL-backed tools have legitimate zero/no-citation outcomes: an arbitrary empty success cannot replace the studied positive fixture if a nonempty positive is expected. Capture no full text/lexicon/corpus; only tool identities, hashes, sanitized status/provenance checks, counted transport starts, and failure category.

If a chosen dependency selector is missing or an expected positive row disappears, classify DRIFT or BLOCKED with evidence, not SKIPPED-SUCCESS. Do not continue the chain with fabricated selectors. A 429 stops the **whole** current live sequence without new CAL requests; budget exceeded is FAIL. Never run this suite concurrently with issue #338's existing 13-case smoke.

## Release interaction

Issue #338 will report first real installed-wheel fixed smoke on an earlier candidate source SHA. This research does **not** imply any of the 25 probes has run. Because #336/#337 merged after that run began, its final release-candidate evidence must be bound to a subsequent exact SHA as appropriate. Do not tag/publish until all required gates are independently reviewed.


## Measured independent-tool batch A (2026-11-15)

**PASS:** [nonpublishing installed-wheel GitHub Actions run 43734021427](https://github.com/alexsosn/CAL-MCP/actions/runs/43734021427), source/head `222d3edd32906576118a516cb0f2d8972d418ffb`, wheel `cal-mcp 0.2.0.dev0`. A fresh venv installed one built wheel; the runner ran outside the source checkout. The report recorded **13/13 `ok` cases**, **13 actual CAL transport attempts** (absolute cap 25), and `status: passed`. No HTTP 429, parser drift, schema/harness fault or unclassified errors appeared.

Verified distinct tools (13): `cal_lexicon_browse`, `cal_gloss_field`, `cal_citation_text_search`, `cal_text_catalogue`, `cal_text_information`, `cal_token_analysis`, `cal_kwic_texts`, `cal_kwic_dialects`, `cal_bibliography_authors`, `cal_targum_concordance`, `cal_targum_hebrew_lemmas`, `cal_syriac_texts`, `cal_syriac_missing_words`.

Together with the earlier [13-case representative release smoke](https://github.com/alexsosn/CAL-MCP/actions/runs/43724124834) (12 distinct tools; 14 actual starts), this measures **25 distinct tools** across two source-bound nonpublishing runs. The 12 dependent follow-ups listed below still require their own pass before claiming all 37. These two existing successful runs have *different source SHAs*; they do not by themselves certify a future exact tagged release candidate. No CAL lexical/text content is copied into the report.


## Measured dependent-tool batch B — STOPPED on parser drift (2026-11-15)

[Nonpublishing installed-wheel run #43735329113](https://github.com/alexsosn/CAL-MCP/actions/runs/43735329113), exact source SHA `5c5033ce0229044423ea053ba71b8f55eadfd104`, installed wheel `cal-mcp 0.2.0.dev0`. The runner passed all-37 schema preflight in normal tests and obeyed 60-second completion-based pacing, server hard 25-transport-attempt budget, zero retry and single concurrency.

The actual report is **FAILED**, with **5/25** measured CAL transport starts:
- `cal_lexicon_lookup` — `ok`
- `cal_lexicon_citation_context` — `ok` (first new dependent tool verified)
- `cal_text_page` — `ok`
- `cal_text_line_comments` — **`drift`**, sanitized `CAL parser drift`; execution stopped immediately
- The other 17 planned steps were **NOT RUN**, not implicitly successful

The failing comment coordinate was selected from the preceding live `cal_text_page(file_id="13250",page=1)` result; the precise CAL document shape was not captured, so no parser-cause attribution is justified yet. The parser strictly validates an exact title, one summary card, and either a unique empty marker or fully typed comment records. Historical Tel Dan page fixtures expose a comment link, but line-comment positive fixture comes from PJ Gen8:21, so those cannot settle whether this is current Tel Dan-specific CAL drift or a request/selector mismatch. Focused investigation is tracked in [#343](https://github.com/alexsosn/CAL-MCP/issues/343).

**Release decision: BLOCKED.** After successful original release smoke (12 distinct tools) + independent batch A (13 tools) + this positive citation context follow-up (1 additional tool), **26/37 distinct public tool identities** have currently passed *a* real installed-wheel positive case across different source SHAs; 1 failed (`cal_text_line_comments`), 10 are not yet live-verified. Success across source SHAs does not constitute a final exact-tagged v0.2.0 acceptance. Do not repeat the failing route without the focused #343 research/TDD and controlled diagnostic.


## Measured 17-step continuation — STOPPED on empty external citations (2026-11-15)

[Nonpublishing installed-wheel run #43736509616](https://github.com/alexsosn/CAL-MCP/actions/runs/43736509616), source SHA `1bb67d50e2c153e16f326d34a5cb5dc58ae6b261`, made **15/25** actual CAL transport attempts. The first **14/17** steps reported `ok` (KWIC dialect selector and hits, full context, author/keyword, Targum concordance, examples, Hebrew lemmas/reflex examples, external dialects/sources). The fifteenth, `external_citations`, returned a schema-valid *empty* `citations` array, categorized as `drift` by the strict positive-case requirement; `syriac_category` and `syriac_group` were **not run**. This is **not yet proven to be parser drift**: [#345](https://github.com/alexsosn/CAL-MCP/issues/345) tracks whether the historical `1CorH` positive fixture differs from current CAL or whether the source legitimately has zero citations.

Overall **34/37 distinct public tools** now have measured positive live coverage across separate installed-wheel nonpublishing runs; `cal_text_line_comments` failed with `parser_drift` ([#343](https://github.com/alexsosn/CAL-MCP/issues/343)), `cal_external_citations` was empty ([#345](https://github.com/alexsosn/CAL-MCP/issues/345)), and `cal_syriac_group` is still unattempted. Both actual failures stop subsequent calls. **v0.2.0 publication remains blocked**, and all-37 success must still be revalidated on an exact final candidate SHA.


## Standalone Syriac group harness correction (2026-11-15)

A reviewed `--syriac-only` opt-in mode isolates the two unattempted Syriac steps, `cal_syriac_texts(category="metrical-homilies-hymns")` followed by `cal_syriac_group(group_id=<typed ID returned by CAL>)`. First one-off [run #43741181619](https://github.com/alexsosn/CAL-MCP/actions/runs/43741181619) failed **before any upstream CAL traffic** during MCP startup: `server.py::app_lifespan` deliberately requires `CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS=25`, and the initial two-step runner had configured a lower value of 2. This was a *harness error*, not evidence against Syriac. The corrected runner preserves the server's reviewed hard cap 25, but the two-case verifier **will PASS only when the measured count is exactly 2**; the independent step descriptions remain unchanged. A retry is allowed only after current CI passes and no live CAL job is in progress.
