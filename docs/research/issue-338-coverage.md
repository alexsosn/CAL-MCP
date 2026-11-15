# Issue #338 — exact installed-wheel smoke coverage matrix

**Source inspected:** `6e472808dc82c06dbfe5e3f8cf3942933a4242a4`, prior to this issue's tests/documentation-only branch commits. The actual executable registry is defined by `src/cal_mcp/release_surface.py`, and the opt-in release smoke cases by `src/cal_mcp/stdio_live_smoke.py`. Source version: `0.2.0.dev0` (unreleased). Captured on 2026-11-15.

**Coverage distinction:** 37 public MCP tools, **13** fixed release smoke cases testing **12** distinct tool identities; **25** tools have no individual fixed-case live proof. This is **not 37/37** user-facing live coverage. The first 12 cases derive from the published v0.1.0 manifest, plus the v0.2 recent-bibliography probe. Passing these cases cannot justify treating an untested tool as live-verified. All registered tools have offline parser/service/MCP tests elsewhere; those tests are separate evidence, not a live CAL run.

## Existing current release smoke identities

| Case | Public MCP tool |
| --- | --- |
| `conversion` | `cal_convert_to_code` |
| `lexicon_noun` | `cal_lexicon_lookup` |
| `lexicon_verb` | `cal_lexicon_lookup` |
| `gloss` | `cal_gloss_search` |
| `text_search` | `cal_text_search` |
| `text_page_followup` | `cal_text_page` |
| `text_concordance` | `cal_text_concordance` |
| `bibliography` | `cal_bibliography_lemma` |
| `dictionary` | `cal_dictionary_collation` |
| `external_citations` | `cal_external_citation_dialects` |
| `targum` | `cal_targum_parallel` |
| `peshitta` | `cal_syriac_peshitta_parallel` |
| `recent_bibliography` | `cal_bibliography_recent` |

## Tools with **no** distinct current live release probe (25)

- `cal_bibliography_author`
- `cal_bibliography_authors`
- `cal_bibliography_keyword`
- `cal_citation_text_search`
- `cal_external_citation_sources`
- `cal_external_citations`
- `cal_gloss_field`
- `cal_kwic_dialect`
- `cal_kwic_dialects`
- `cal_kwic_full_context`
- `cal_kwic_texts`
- `cal_lexicon_browse`
- `cal_lexicon_citation_context`
- `cal_syriac_group`
- `cal_syriac_missing_words`
- `cal_syriac_texts`
- `cal_targum_concordance`
- `cal_targum_concordance_examples`
- `cal_targum_hebrew_lemmas`
- `cal_targum_hebrew_reflexes`
- `cal_targum_reflex_examples`
- `cal_text_catalogue`
- `cal_text_information`
- `cal_text_line_comments`
- `cal_token_analysis`

## Bounded live-test constraints and reporting

The pre-v0.2 existing installed-wheel smoke has a strict maximum of **25 actual CAL transport starts**, no retries, single concurrency, 60-second completion-based spacing between CAL-backed cases, preflight of required MCP schemas, fail-closed drift, and a hard stop on HTTP 429/transport failure. Its 13-case success criteria include all cases and a minimum of 12 actual CAL transport starts. It cannot certify the 25 unprobed tool paths.

Live results are separately recorded in this research area only **after** a GitHub Actions run actually completes. A passing CI fixture test is not live evidence; record exact commit, wheel version, run link, 13 outcomes, counted transport attempts, and any failures. Do not publish v0.2.0 on the mere existence of this document.

Future safe coverage for the 25 excluded tools should use studied selectors, deterministic TDD, installed stdio, explicit hard per-batch transport accounting, and representative content assertions; no automatic traversal, corpus extraction, or bulk mirrors. Stop the session on 429, and classify blocked network as unavailable. Avoid inventing a universal all-features success condition from the subset.
