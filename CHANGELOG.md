# Changelog

## 0.1.0 — 2026-09-24

First standalone release of CAL-MCP, a read-only MCP adapter over the Comprehensive Aramaic Lexicon (CAL).

### Public MCP surface

v0.1.0 freezes **34 public tools** across these research families:

- deterministic conversion from supported Aramaic-script/Unicode inputs to CAL code (a rejected Hebrew mark or sign is named by code point, and pointed words get an unpointed suggestion);
- lexicon exact/root/full-form lookup, bounded prefix browsing via `cal_lexicon_browse` (ordered typed rows distinguish genuine entries from CAL arrow cross-references; `entries` contains only genuine entries; cross-reference source text and target lemma keys are preserved without fetching the target), and explicit linked-citation full context via `cal_lexicon_citation_context` (exact-entry headers are read from CAL's marked `lemma-header` fields, with `part_of_speech: null` where CAL gives none and no fallback to later prose; including preservation of CAL's literal uncertain POS marker such as `n.f.?`, and Babylonian Talmud texts whose tokens use CAL's `bablex.php` family);
- English gloss search and structured gloss-field extraction (CAL's repeated rows behind a `⟹` redirect are kept, with the redirecting key in `cross_reference_from`; parenthesized secondary-gender POS such as `n.m.(f.)` is preserved; row POS is CAL's marked `<pos>`, so verbs keep their vowel class such as `vb. a/u`, as in lexicon browse rows, and CAL's explicitly empty `<pos>` gives `part_of_speech: null`), and citation-text search (CAL's explicit rejection of a query, such as `god`, is reported as `invalid_input`; current result rows, with a citation CAL renders without its own header returned with `lemma: null`; header `part_of_speech` is CAL's marked `<pos>`, which for verbs includes the vowel class that an earlier parser misreported as `gloss`);
- text catalogue/topic discovery (search matches name the tool that follows them (`follow_up_tool`): `cal_text_page`, or `cal_text_catalogue` with `category_id` for catalogue nodes such as Targum Neofiti and the Peshitta books; including CAL's current Mandaic catalogue composition (subdivided files are followable catalogue nodes whose exact subtext identity is separate from pagination, including current `74421/col`) and Christian Palestinian Aramaic direct/decimal/suffix-bearing routes), one-page retrieval (subtext IDs preserve leading zeroes and CAL's current optional single lowercase suffix; current CPA file routes retain CAL's `cset=C` selector; current two-cell plain/unlemmatized rows are returned with rendered text, empty tokens and nullable line/comment coordinates; CAL's current explicit no-lines state for direct CPA `55002` maps to `not_found` rather than parser drift; paginated texts such as the Babylonian Talmud report page page count and line total; a page beyond the last is an `invalid_input` error; each line keeps CAL's display coordinate and comment link; explicit empty Syriac lexical slots are preserved as `empty_word_indexes` alongside rendered tokens; current Mandaic `74421/col` plus direct `74425` / `74429` preserve their evidence-backed special token coordinates as opaque follow-up handles; six-digit Syriac ids such as `634081`, which CAL splits into file plus subtext, are read under the listed id), explicit text-information metadata, and explicit line comments/translations via `cal_text_line_comments`;
- token-at-coordinate lexical analysis (every `<hr>`-separated lexeme of a current result is returned in order, for example the conjunction and the verb of `w)mr`, with a linked prefix's following personal name kept in `unlinked_summaries`; candidate POS is CAL's marked `<pos>`, so verbs keep their vowel class), including exact follow-up of the current Mandaic `74421/col`, `74425`, and `74429` special coordinate families, current linked Syriac redirects (explicit analysed source key in `analyzed_lemma_key`, linked target in `lemma.lemma_key`), and current linkless Peshitta/CPA success pages preserved as ordered opaque `unlinked_summaries` without invented lemma entries;
- one-text concordance (with CAL's displayed lemma labels, and CAL's own "no data found" rows flagged instead of failing the page), explicit text/dialect KWIC (including Hebrew- and Syriac-script results, whose coordinates CAL renders reversed for right-to-left display; hits keep CAL's highlight as `target_text`, `null` where CAL highlights nothing; one-dialect results report CAL's per-form grouping, including related-form hits and whether CAL lists the requested form at all), and explicit typed KWIC full-context follow-up via `cal_kwic_full_context` (scholarly rows reject loose text/unknown elements and require exact root lexical/comment routes; including hits in subdivided texts under CAL's current file-information coordinate and Babylonian Talmud rows with `bablex.php` token links);
- bibliography author, text/subject-tag, and lemma search (one record per CAL bibliography entry on CAL's current result layout);
- dictionary spelling collation;
- citations from sources that CAL cites but does not expose as full online texts;
- Targum parallel verse (CAL's per-line verse labels are removed from `mt_text`, as in the MT/Peshitta comparison), Targum concordance (current-layout label rows reported as `section_labels` rather than applied to rows), and MT-Hebrew reflex workflows;
- Syriac text-category discovery, explicit grouped-text follow-up (`cal_syriac_group`, including CAL's current card layout, whose children carry `subtext_id`), CAL's missing-from-*A Syriac Lexicon* lists, and MT/Peshitta verse comparison.

The executable MCP schemas remain the technical source of truth. CAL endpoint names and private form fields are not part of the public contract.

### Request and data policy

- CAL data stay remote and live; no CAL corpus or lexicon is bundled in the package.
- Operations are caller-initiated and bounded. Most public calls perform one CAL request; successful exact lexicon lookup uses a bounded two-request browser + selected-entry flow.
- `cal_lexicon_browse` fetches exactly one CAL browse page per call. If CAL exposes a validated NEXT PAGE continuation, the tool returns it as `next_continuation`; following it requires another explicit caller action.
- No background crawl, mirror, cache warming, hidden pagination, link traversal, or automatic source expansion. Lexicon citation context, KWIC full-context, and text-line comments/translations retrieval are separate explicit caller actions over typed selectors/coordinates returned by prior calls.
- `cal_lexicon_citation_context` accepts only the typed positive-decimal `full_coordinate` exposed for canonical linked lexicon citations; it does not accept arbitrary URLs or locally decode the opaque coordinate.
- `cal_text_line_comments` distinguishes `found` from CAL's explicit `no_citations` state; `no_citations` does not claim that the requested coordinate exists as a text line.
- Line-comment parsing excludes non-rendered script/style content from semantic markers, rejects nested semantic result cards, and fails closed on truncated records or unfinished semantic containers instead of returning partial success.
- The shared client enforces finite timeouts, low concurrency, bounded transient-only retries, redirect/origin boundaries, response-size limits, single-flight suppression, and a bounded process-local cache.
- Parsers fail closed on material upstream drift rather than returning plausible partial results.

### Standalone runtime

- Python `>=3.11`.
- Primary v0.1 transport: local stdio.
- Installed command: `cal-mcp`.
- Equivalent module entry point: `python -m cal_mcp`.
- `cal-mcp --version` and `cal-mcp --help` print and exit without starting the server; any other argument is rejected with the usage.
- Agora is not a runtime dependency; optional Agora registration remains the downstream issue #16 after publication.

### Release and drift validation

- Structured `parser_drift` and `content` errors name the CAL page that failed in `source_url` (CAL origin only). Citation-context drift is reported as `parser_drift` rather than as unsafe content.
- The release pipeline builds wheel and sdist once, validates both distributions in fresh virtual environments, launches each installed `cal-mcp` entry point over stdio, and checks version + the frozen 34-tool schema without contacting CAL.
- Deterministic CI and release validation use committed Python 3.11 target/build constraints with exact-environment verification; a separate latest-compatible job checks the broad dependency ranges declared for downstream users.
- Those deterministic constraints are validation inputs only; downstream package metadata retains the reviewed broad runtime dependency ranges.
- A separate live drift smoke is opt-in/scheduled and capped at **9 CAL requests**, concurrency 1, retries 0, cache disabled.
- The live smoke covers eight representative parser/service families and distinguishes parser drift from network/upstream and other content/policy failures.

### Known limitations

- CAL is a live scholarly database and its public HTML/form surfaces are not a versioned machine API; upstream drift can temporarily fail a tool closed until the adapter is updated.
- v0.1 does not bundle CAL data or provide an offline research mode.
- v0.1 is stdio-only; there is no hosted CAL-MCP service.
- CAL's recent-five-years bibliography snapshot is intentionally deferred to #39 and is not part of the frozen v0.1 surface.
- Pseudo-Jonathan Hebrew-reflex research is not exposed because CAL currently marks that upstream workflow under development.

### Upstream and attribution

CAL remains the authority for the returned lexical, textual, citation, bibliography, Targum, Syriac, and dictionary-collation content. CAL-MCP is not affiliated with or endorsed by the Comprehensive Aramaic Lexicon Project or Hebrew Union College.
