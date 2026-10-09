# Architecture decisions

This file records durable project decisions. New evidence belongs first in `research.md`; a decision belongs here when it constrains future implementation.

## D-001 — CAL-MCP is a thin live adapter

**Status:** accepted — 2026-09-03

CAL-MCP will issue bounded live requests to CAL for explicit user/MCP operations. It will not reconstruct, mirror, pre-index, or bulk-download the CAL database.

Consequences:

- package contains software, not CAL data;
- no background corpus crawl or cache warming;
- result limits/pagination must remain bounded;
- caching exists only to suppress duplicate requests and is size/TTL bounded;
- offline functionality is not a goal for CAL-backed queries.

## D-002 — CAL is the scholarly authority

**Status:** accepted — 2026-09-03

CAL-MCP preserves CAL's analyses, labels, senses, citations, and text data. It does not silently fix or enrich CAL results.

Consequences:

- no LLM-generated morphology/lexicography is presented as CAL;
- potential CAL scholarly errors are reported upstream or documented as upstream limitations;
- adapter tests check fidelity, not linguistic truth.

## D-003 — Standalone operation is primary; Agora is optional downstream integration

**Status:** accepted — 2026-09-03

A released CAL-MCP package must install and run without Agora. Agora may discover, install, launch, and describe a released version but does not own CAL-specific behavior.

Consequences:

- CAL-specific parsers, tools, docs, examples, and skills remain in CAL-MCP;
- a stable package/entry point is published before Agora registration;
- Agora integration pins a release and performs smoke-level verification only;
- CAL-MCP source must not import Agora runtime code.

## D-004 — Public MCP schemas are separated from upstream HTML/forms

**Status:** accepted — 2026-09-03

CAL's current PHP handlers and HTML layout are undocumented implementation details. Public MCP models expose scholarly concepts instead of DOM/form structure.

Consequences:

- endpoint-specific parsers live behind services;
- markup-only changes should normally be absorbed without MCP schema changes;
- material semantic fields cannot be silently discarded;
- parser drift produces explicit errors when fidelity is uncertain.

## D-005 — Input normalization is deterministic

**Status:** accepted — 2026-09-03

Normalization/query encoding uses explicit deterministic rules and CAL-supported representations. It does not use an LLM to infer spellings, roots, or analyses.

Consequences:

- preserve original input;
- expose normalized query/strategy when useful for reproducibility;
- ambiguous/lossy conversions are explicit;
- prefer sending a script/representation directly when CAL supports it faithfully.

## D-006 — Provenance is part of the public result contract

**Status:** accepted — 2026-09-03

Successful CAL-backed results expose at least a CAL source URL and retrieval timestamp. CAL identifiers/coordinates and original/normalized query metadata are preserved when available/applicable.

Rationale: CAL is a live work in progress and explicitly asks scholarly users to cite retrieval dates.

## D-007 — Normal CI is offline; live tests only detect drift

**Status:** accepted — 2026-09-03

Deterministic tests use minimal fixtures and mocked HTTP. Live CAL tests are opt-in/scheduled/release smoke checks with strict request caps.

Consequences:

- CI is not coupled to CAL uptime;
- tests cannot accidentally create sustained automated load;
- live tests prove integration compatibility, not scholarly correctness.

## D-008 — Conservative request behavior until CAL publishes explicit machine guidance

**Status:** accepted — 2026-09-03; amended 2026-09-03

No CAL-specific automated-access/API policy was found in the initial research snapshot. CAL-MCP therefore defaults to low concurrency, bounded retries, finite timeouts, bounded caching, and no prefetching.

For v0.1, caching is deliberately **process-local and in-memory only**. Its purpose is duplicate-request suppression during one CAL-MCP process/session, not offline access or accumulation of a CAL dataset.

Consequences:

- use a bounded LRU cache with finite TTL and size limits;
- cache keys represent the complete normalized upstream request identity;
- cache only successful, parseable CAL results/responses; optional short negative caching is allowed only for clean semantic not-found results with dedicated tests;
- never cache network failures, maintenance/error pages, parser failures, or other uncertain upstream states;
- preserve the original CAL retrieval timestamp across cache hits, with separate adapter cache-hit/age metadata if useful;
- expose a complete cache-disable mode for reproducibility/debugging;
- no disk/database persistence, cache warming, background refresh, or prefetch in v0.1.

This decision is operational caution, not a legal interpretation of CAL's terms.

Any persistent cache, background refresh, or material increase in automated request volume requires a new/updated decision citing current CAL guidance or concrete operational evidence.

## D-009 — stdio is the required v0.1 transport

**Status:** accepted — 2026-09-03

The first release will be a local MCP process with stdio support. A hosted/network transport is not required for v0.1.

Consequences:

- CAL-MCP avoids hosting/auth/abuse/rate-sharing complexity;
- clients and Agora can launch the same local package;
- application/core layers remain transport-agnostic so another MCP transport can be added later without rewriting CAL services.

## D-010 — Documentation is split by audience and ships with behavior

**Status:** accepted — 2026-09-03

- root docs provide project state and entry points;
- `wiki/` stores maintainer/agent architecture, testing, decisions, and process;
- `docs/` stores versioned user-facing documentation and is added incrementally with implemented capabilities;
- executable tool schemas remain the technical source of truth.

Consequences:

- feature PRs update user docs in the same change;
- no empty aspirational tool pages;
- diagrams use Mermaid in Markdown and change with architecture;
- examples should be test-backed.

## D-011 — Do not prematurely choose a static documentation generator

**Status:** accepted — 2026-09-03

The bootstrap uses repository Markdown and GitHub Mermaid rendering. A static documentation generator will be selected only when enough `docs/` content exists to justify it, using criteria in `documentation.md`.

Rationale: this avoids creating framework maintenance work before there is a stable public API to document.

## D-012 — Related CAL/Aramaic projects are prior art, not compatibility targets

**Status:** accepted — 2026-09-03

Projects such as PSHAT and Peshitta MCP may inform edge cases and agent-facing ergonomics, but CAL-MCP will not inherit their data models/interfaces by default.

Any copied/reused code requires an issue that verifies license compatibility and demonstrates that reuse is preferable to a small native implementation.


## D-013 — Anticipated CAL-MCP failures use structured MCP errors

**Status:** accepted — 2026-09-11

Known caller-validation, CAL network/HTTP, response-size/content-policy, and parser-drift failures cross the public MCP boundary as `isError=true` results with a stable machine-readable `error` object. Unexpected programming failures and unknown SDK/protocol errors remain on the MCP SDK's generic sanitized error path.

Consequences:

- public callers can distinguish correction/retry/drift actions without parsing human error strings;
- `upstream_reached` is false only for known local rejection, true only after a response is known, and null for ambiguous network receipt;
- retryability follows the existing bounded request policy rather than inventing a second retry taxonomy;
- URLs/status codes are exposed only from explicitly typed metadata, never scraped from arbitrary exception text;
- public diagnostics are one-line and bounded, and response bodies/HTML/tracebacks are never part of the error contract;
- successful empty/not-found states remain normal success results;
- adding a new public error class requires an explicit allowlist/classifier decision and contract coverage rather than a catch-all serializer.


## D-014 — Dialect KWIC reports CAL's per-form grouping instead of attributing hits to the requested key

**Status:** accepted — 2026-09-24 (issue #149; research R-028)

CAL's one-dialect KWIC now answers a lemma-key request per lemma form, and may include forms it groups with the requested key (for example `nqh N` hits for `n)qh N`). CAL-MCP keeps every hit CAL returns and labels it with CAL's own form key (`form_lemma_key`), exposes CAL's ordered per-form counts (`forms`), and reports `total` as their sum (CAL's grand total when rendered). An all-zero page reports the requested dialect in `empty_scope_ids`, derived from CAL's explicit per-form "No examples found" summaries.

Consequences:

- CAL-MCP neither decides which forms are related nor drops CAL's related-form hits; it never presents a related-form hit as a hit for the requested key;
- `total` for a requested key can count hits under other CAL forms, and callers filter by `form_lemma_key` if they need only the requested form;
- per-form counts, positions, dialect identity, canonical keys, requested-form presence, and any grand total are cross-checked, and disagreement fails closed as parser drift;
- the schema change is additive (`forms`, `form_lemma_key`, and the related `target_text` and concordance `label` fields); request counts and bounds are unchanged.

**Amendment (2026-09-25, issue #176, R-043):** CAL may omit the requested form's summary altogether and list only the forms it groups with it in that dialect. For example, `n)qh N` in dialect 71 lists `n)qt) N` and `nqh N`. Such a page is accepted, and the result says so with the additive `requested_form_listed: false`: `true` when CAL lists the requested form, `null` where CAL renders no per-form summaries. CAL-MCP does not invent a zero summary for the omitted form, and it never attributes the related-form hits to the requested key.


## D-015 — Targum concordance label rows are reported, not applied as groupings

**Status:** accepted — 2026-09-24 (issue #152; research R-031)

CAL's current Targum concordance page renders a single label row (`Torah`, with an `&nbsp;` filler cell) and then every Targum as a plain row, including Former and Writing Prophets, Psalms and Chronicles. Carrying that label forward would attribute rows to a grouping CAL does not apply. As chosen by the maintainer, CAL-MCP sets `section` only from CAL's explicit earlier-layout section headers (`<th colspan>`). Current-layout label rows are reported in an additive `section_labels` list of `{label, row_index}`.

Consequences:

- no row is attributed to a label CAL does not apply as a grouping; callers can see where CAL placed each label;
- the schema change is additive (`section_labels`); row, count and total semantics and request counts are unchanged;
- a label row must carry CAL's literal `&nbsp;` filler, so a damaged result row cannot be misread as a label.

## D-016 — Subtext IDs use a dedicated researched grammar

**Status:** accepted — 2026-09-26 (issue #170; research R-039)

CAL's current Christian Palestinian Aramaic catalogue disproves the earlier implicit assumption
that every subtext selector is decimal: CPA uses values such as `01001a`. For v0.1,
`subtext_id` therefore has its own shared grammar: one or more decimal digits followed by at most
one lowercase ASCII letter.

Consequences:

- preserve leading zeroes and any lowercase suffix exactly;
- use the same grammar for text catalogue/page/information and KWIC/full-context subtext fields;
- do not widen generic file IDs, category IDs, text IDs, or KWIC target coordinates;
- current text/token machine coordinates may be decimal or use CAL's observed digits + one
  lowercase ASCII letter + decimal-tail form; suffix-bearing text pages additionally require the
  exact requested `file_id + subtext_id` prefix;
- `cal_token_analysis` accepts that same machine-coordinate grammar at its input boundary, so a
  coordinate returned by `cal_text_page` is not rejected locally; current linked and linkless
  CPA token-analysis response shapes are handled under the evidence-backed token-analysis
  contracts in R-040/R-041;
- current CPA text-page routing is selected by evidence-backed subdivided/direct file sets: all
  current CPA routes retain `cset=C`, including decimal and suffix-bearing subtexts and four
  direct texts; known direct files reject a caller-supplied subtext and known subdivided files
  require one; current paginated direct `55430` navigation may additionally carry the exact
  private `sub=&clen=5` returned-link variant, while subdivided routes remain strict; suffix
  presence and the generic `55` prefix are not treated as route classifiers; contradictory routes
  fail closed rather than being normalized;
- values with leading letters, multiple-letter suffixes, uppercase letters, punctuation,
  whitespace, or arbitrary strings remain invalid;
- future CAL evidence requiring a wider or corpus-specific subtext grammar requires a new research
  amendment rather than silently broadening this rule.

## D-017 — Linkless token-analysis success stays opaque and separate from linked candidates

**Status:** accepted — 2026-09-27 (issue #193; research R-041)

Current CAL can return a successful token-analysis result marker followed by one or more rendered
analysis-summary lines without any result table or lemma-entry link. The adapter cannot validate a
canonical lemma identity, candidate boundary, or redirect target from that shape.

Consequences:

- existing `candidates` remain reserved for analyses with a validated linked `LemmaRef`;
- linkless success is exposed additively as ordered `unlinked_summaries`;
- `status=found` when either linked candidates or unlinked summaries exist;
- `=`, `-->`, POS-looking text, and gloss-looking text inside unlinked summaries remain opaque
  rendered CAL text;
- no linked lemma key, entry URL, morphology, or redirect relation is synthesized;
- explicit CAL no-data/no-lemma states stay `not_found` with both collections empty;
- a current linkless-looking region that contains links, tables, or mixed linked/unlinked
  structure fails closed rather than falling back to the older loose candidate parser.

## D-018 — Plain text rows do not synthesize token identity

**Status:** accepted — 2026-09-28 (issue #185; research R-042)

Current CAL contains text rows whose scholarly text is rendered directly rather than as lexical
token links. A subset of those rows still has a comment link carrying a line coordinate.

Consequences:

- `TextLine.coordinate` is nullable;
- linked rows keep their validated token/machine coordinate semantics;
- plain rows return rendered `display_coordinate` and `text`, with `tokens=[]` and
  `empty_word_indexes=[]`;
- a plain row with no comment link uses `coordinate=null`;
- a plain row with one exact validated `comment.php?coord=...` link preserves that coordinate and
  `comment_url`; this is line/comment identity, not evidence of tokenization;
- callers use `cal_token_analysis` only from returned token objects carrying both `coordinate`
  and `word_index`;
- current text tables are classified as linked or plain as a whole; an observed mixed table is not
  assumed and therefore fails closed;
- an empty `text-display` shell is not represented as a successful empty line; when CAL also
  supplies its explicit `NO LINES FOR ... ARE CURRENTLY STORED` marker (current direct CPA
  `55002`), text retrieval uses the existing `not_found` / `page=null` semantics rather than
  inventing a line.

## D-019 — Mandaic subtext identity is distinct from pagination

**Status:** accepted — 2026-10-01 (issue #188; research R-056)

For current Mandaic collection 74, a `showsubtexts.php` file is a catalogue node. Its child
`sub` selector identifies a scholarly subtext and is preserved exactly. The public one-based
`page` argument selects a rendered page *within* that explicit subtext; it never synthesizes,
pads, increments, or otherwise derives `sub`.

Consequences:

- category 74 returns current subdivided files as `categories` and direct files as `texts`;
- following a subdivided category with `cal_text_catalogue(category_id=...)` returns child
  `TextRef` values carrying CAL's exact `subtext_id`;
- a known subdivided Mandaic `cal_text_page` call requires that returned `subtext_id`;
- direct Mandaic pagination is enabled per exact file evidence: current `74501` uses the public
  page axis without a public subtext, while every other current/legacy direct file remains
  page-1-only until its pagination semantics are independently observed;
- Mandaic child selectors preserve leading zeroes, sparse numbering, and the observed literal
  `col`; `col` does not widen the ordinary or CPA subtext grammar;
- `cal_text_information` accepts the same evidence-backed Mandaic selector so a returned child is
  followable without inventing a different identifier;
- each explicit catalogue/page/information operation remains bounded and does not perform hidden
  route discovery or prefetch.

## D-020 — Mandaic special machine coordinates are file-scoped

**Status:** accepted — 2026-10-02 (issue #218; research R-057)

CAL machine coordinates remain opaque upstream identifiers. Current direct Mandaic files
`74425` and `74429` expose coordinate forms outside the shared decimal / embedded-lowercase
grammar, and CAL's token-analysis endpoint accepts those exact observed forms.

Consequences:

- the shared generic machine-coordinate grammar is unchanged;
- `74425` additionally accepts its researched file-prefixed decimal tail with at most two
  trailing lowercase ASCII letters;
- `74429` additionally accepts its researched file-prefixed decimal tail with at most one
  trailing lowercase letter, or its uppercase `A` + decimal series;
- text-page parsing enables those rules only for the exact direct file identities `74425`
  and `74429`; foreign prefixes and nearby Mandaic files do not inherit them;
- `cal_token_analysis` accepts the same exact coordinate families so any token returned by
  those text pages remains followable without normalization;
- the adapter does not decode the letter components or infer line/subtext semantics from them;
- any broader coordinate family requires new upstream evidence rather than a generic
  alphanumeric fallback.

## D-021 — Mandaic special machine coordinates may be exact file/subtext families

**Status:** accepted — 2026-10-02 (issue #220; research R-058)

D-020's file-scoped exceptions remain unchanged for direct files `74425` and `74429`.
Current subdivided text `74421/col` adds one separately evidenced family whose opaque machine
coordinate begins with the exact selected file plus literal subtext:

`74421col[0-9]+`.

Consequences:

- the shared generic machine-coordinate grammar remains unchanged;
- the Mandaic-special predicate recognizes only explicitly researched exact families;
- text-page parsing enables `74421col...` only when the requested identity is exactly
  `file_id=74421, subtext_id=col`;
- numeric `74421` subtexts keep the existing decimal coordinate rules;
- `cal_token_analysis` accepts the same exact returned handle so page → token-analysis
  composition is lossless;
- arbitrary multi-letter selectors, other file ids, case variants, punctuation, missing decimal
  tails, and guessed coordinate families remain invalid;
- CAL-MCP preserves these handles verbatim and does not decode `col` or the decimal tail into an
  undocumented local coordinate model.

## D-022 — Installed-stdio release smoke has one hard total CAL transport budget

**Status:** proposed — 2026-10-10 (issue #157; research `docs/research/issue-157-installed-stdio-live-smoke.md`)

The release/scheduled live drift smoke should exercise representative MCP tools through a
freshly installed `cal-mcp` stdio process, validate advertised output schemas and provenance,
and report each case as success, drift, unavailable, or harness failure.

**Proposed CAL load contract (requires independent review before implementation):**

- **25 total CAL transport attempts maximum per scheduled/release invocation**, not 25 calls
  *in addition* to the existing direct-service nine-request suite;
- no concurrent MCP calls; smoke server's CAL concurrency set to one; retries disabled;
- bounded completed-response cache shared across the one process;
- account for every attempted GET/POST at the server's transport boundary, including failures,
  **before** sending it; cached responses cost zero;
- run all fixed independent cases where budget permits, never follow arbitrary returned links
  or pages, and stop immediately rather than exceeding the cap;
- no change to CAL-MCP's default request behavior outside opt-in smoke mode;
- publish only if the exact installed-wheel stdio E2E suite passes; regular CI remains offline.

Do not enable this expanded smoke until the hard budget has deterministic RED/GREEN tests,
representative CAL calls have been trialed below the cap, and this decision is accepted through
an independent review. A failed smoke must not trigger automatic retry loops.

