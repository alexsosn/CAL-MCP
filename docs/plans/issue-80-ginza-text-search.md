# Issue #80 plan — current Ginza text-search result links

Date: 2026-09-08
Baseline: `main` at `88892f4054d470f2d7fa7e72b647ada13befbd11`
Research: `docs/research/issue-80-ginza-text-search.md`

## Goal

Restore `cal_text_search(query="Ginza")` against CAL's current Mandaic result-link shape without changing the public search contract, request count, ordinary text-search behavior, or catalogue behavior.

## Invariants

- One public search call performs exactly one existing POST to `newsearchtxts.php`.
- Ordinary `get_a_chapter.php?file=...&sub=...` search results keep their current interpretation.
- Current Mandaic search results are accepted only as `showsubtexts.php?subtext=<decimal file id>&cset=M`.
- The Mandaic upstream `subtext` query key maps to public `TextRef.file_id`; public `TextRef.subtext_id` remains `None`.
- CAL order, rendered label, rendered description, original/submitted query provenance, and explicit empty-result handling are preserved.
- No returned `showsubtexts.php` link is fetched automatically.
- Malformed specialized-result identifiers or route-family markers fail closed as parser drift.
- Catalogue interpretation of `showsubtexts.php?subtext=...` remains unchanged; the specialization is scoped to text-search result parsing only.

## TDD sequence

### 1. Offline fixture

Add a deliberately reduced `text_search_ginza.html` fixture containing:

- the normal `CAL search for texts like:` marker;
- two result rows in current CAL order;
- `/showsubtexts.php?subtext=74410&cset=M` and `/showsubtexts.php?subtext=74411&cset=M` links;
- enough row text to prove label/description splitting comes from the rendered row.

No full live response is archived.

### 2. Test-only RED

Add a focused regression module that proves:

- `parse_text_search_page()` returns the two Ginza `TextRef` values in order;
- `file_id` is `74410` / `74411` and `subtext_id is None`;
- rendered labels and descriptions are preserved from the row;
- `TextService.search("Ginza")` performs exactly one POST with `search=Ginza` and no follow-up request;
- repeated, blank, or non-decimal `subtext` fails closed;
- missing, repeated, blank, or non-`M` `cset` fails closed;
- ordinary Tel Dan search behavior remains green.

A valid RED must pass dependency installation, Ruff lint, Ruff format, and strict mypy in both CI matrices, with pytest failures confined to the new Ginza expectations.

### 3. Minimal implementation

Add a search-only helper that interprets a result link as either:

- the existing `_text_ref_from_link()` ordinary route; or
- the current Mandaic `showsubtexts.php` route after strict query validation.

Reuse `_search_label_and_description()` in both branches. Do not widen `_text_ref_from_link()` itself, because catalogue parsing already assigns different semantics to `showsubtexts.php` links.

### 4. GREEN gates

Run the full repository CI in both dependency matrices. Required gates:

- Ruff lint;
- Ruff format check;
- strict mypy;
- full pytest suite.

Do not treat a run stopped before pytest as behavioral GREEN evidence.

### 5. Documentation

Update `docs/tools/texts.md` to state that text search can return specialized Mandaic entries while remaining one-request/non-recursive, and that returned file identifiers can be passed to `cal_text_page` without exposing CAL's private `cset`/`subtext` routing details.

### 6. Independent adversarial review

Review the exact final SHA from scratch, focusing on:

- accidental reinterpretation of catalogue `showsubtexts.php` links;
- accepting arbitrary/foreign `cset` values;
- silently ignoring malformed specialized search rows;
- duplicate-result/order regressions;
- incorrect public `subtext_id` exposure;
- hidden follow-up requests;
- regressions in ordinary Tel Dan search and explicit empty-result semantics.

Post the review directly to the PR. Any blocker returns the branch to implementation/test gates and requires another independent review of the corrected exact SHA.

## Cleanup

Remove the temporary live-research workflow before entering TDD so normal branch/PR CI remains fully offline.

## Non-goals

- No Mandaic catalogue discovery (#78/#83).
- No typed public error envelope (#84).
- No page-route changes; issue #85 already owns those semantics.
- No recursive search-result expansion or link following.
- No additional live CAL requests during TDD, implementation, or review.
