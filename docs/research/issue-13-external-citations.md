# Issue #13 research — citations from texts outside the online CAL corpus

**Research date:** 2026-09-05

## Question

Issue #13 covers CAL's public research surface for lexical citations whose source texts are **not** present in CAL's online text database. The research goal is to establish the current caller-visible workflow, request bounds, semantic result structure, and explicit empty states before choosing an MCP contract.

This surface is distinct from both:

- CAL-MCP's `cal_citation_text_search`, which searches English words inside rendered CAL citations; and
- CAL's ordinary online text browser, whose `file_id`/subtext/page coordinates identify text that CAL can actually display.

The external-citation workflow must not imply that an absent source is retrievable as an online CAL passage.

## Current public workflow

CAL's search page links a separate **Citation Finder** for texts not in the online database. The current workflow is explicitly staged:

1. choose a dialect;
2. receive CAL's ordered list of source abbreviations/descriptions for that dialect where lexical citations exist but full text is not online;
3. choose one exact source abbreviation;
4. receive CAL's ordered lexical citations for that source.

Each stage is already an explicit researcher action in CAL's UI. CAL-MCP should preserve that caller-controlled composition rather than hiding the discovery steps behind a crawl.

### 1. Dialect discovery

Public page:

- `https://cal.huc.edu/citfinder.html`

Current semantic marker:

- `Choose a Dialect`

A bounded 2026-09-05 probe found **19** ordered dialect links. Representative labels include `Old Aramaic`, `Imperial/Official Aramaic`, `Qumran`, `Syriac`, `Babylonian Talmudic`, and `Mandaic`.

Current links target the citation-source-list surface and carry an opaque numeric dialect identifier. Representative raw structure:

```html
<div class="section-title">Choose a Dialect</div>
<div class="card">
  <a href="display.notext.abbrevs.php?dial1=6&amp;dial=1">Old Aramaic</a>
  <a href="display.notext.abbrevs.php?dial1=6&amp;dial=2">Imperial/Official Aramaic</a>
  ...
</div>
```

`dial1=6` is a current CAL UI/form detail. It is not a scholarly identifier and must remain private to the adapter. The returned `dial` value is an opaque CAL dialect identifier suitable for an explicit follow-up operation, analogous to the already implemented KWIC dialect-discovery workflow.

### 2. Source abbreviations for one dialect

Current result family:

- `https://cal.huc.edu/display.notext.abbrevs.php?...`

The current page identifies itself as `Texts With Citations, No Full Text Yet` and tells the researcher that the listed texts have citations in the database and that the abbreviation link opens them.

For the representative Syriac dialect (`dial=6`), the bounded probe returned one response of about **317 KB** containing **703** ordered source rows. There was no observed next-page/continuation control.

Representative raw structure:

```html
<div class="cit-row" ...>
  <a class="cit-abbrev" href="displaycits.abbrev.php?abbrev=1CorH">1CorH</a>
  <span class="cit-defined">
    1Corinthians in the Harklean version, for which see ...
  </span>
</div>
```

The source abbreviation is CAL's navigation key. The description is CAL-rendered bibliographic/source metadata and must be preserved as such rather than parsed into locally inferred author/title/year fields.

An unknown dialect currently returns HTTP 200 with the explicit semantic empty marker:

```text
No extra citations for that dialect are currently found.
```

Therefore an explicit marker is a valid empty source list. A successful-looking page with neither recognized rows nor the empty marker is parser drift.

### 3. Citations for one exact source abbreviation

Current result family:

- `https://cal.huc.edu/displaycits.abbrev.php?abbrev=<exact CAL abbreviation>`

Representative source `1CorH` currently returns **3 citations**. The page tells the researcher to select a lexical link to see the citation in the full context of an entry. That lexical-entry context is a separate CAL action; it does **not** make the absent source text available through the ordinary text browser.

Current semantic structure includes:

```html
<span class="result-count">3 citations</span>
<div class="cit-entry">
  <div class="cit-top">
    <div class="cit-left">
      <a class="cit-lemma"
         href="oneentry.php?lemma=...&amp;cits=all">...</a>
      <span class="cit-pos">...</span>
    </div>
    <span class="cit-coord">1CorH 12:28</span>
  </div>
  <div class="cit-mid">
    <span class="cit-gloss">...</span>
    <span class="cit-text">...</span>
  </div>
  <div class="cit-xlation">...</div>
</div>
```

The bounded raw probe observed three same-origin `oneentry.php` lexical links carrying canonical CAL lemma keys and `cits=all`. The citation record can therefore preserve:

- canonical CAL lemma key from the lexical link;
- CAL-rendered lemma label;
- rendered part-of-speech label when present;
- rendered external-source citation/reference such as `1CorH 12:28`;
- CAL lexical gloss when present;
- source-language citation text when present;
- English translation when present;
- the same-origin CAL lexical-entry URL as explicit follow-up metadata.

The current representative page demonstrates that optional rendered fields cannot be assumed to be populated for every row. The source text and translation in particular must remain nullable rather than being fabricated.

An unknown source abbreviation currently returns HTTP 200 with the explicit marker:

```text
No citations for "Qqqqqq" are currently stored.
```

Therefore this is a valid empty citation result. A page with neither recognized citation entries nor the explicit no-citations marker is parser drift. If a rendered result count is present, silently returning a different number of parsed records would be misleading and should fail closed.

## Semantics and identifiers

This workflow exposes **external/non-online-text citation references**, not online passage coordinates.

Consequences:

- a source abbreviation such as `1CorH` is not an online CAL `file_id`;
- a rendered citation such as `1CorH 12:28` is preserved as a CAL citation/reference string, not converted to a `Passage` or guessed machine coordinate;
- CAL's lexical `oneentry.php` link is explicit follow-up metadata and is never opened automatically;
- the adapter must not fetch, reconstruct, or substitute the absent source text from another corpus;
- source descriptions and citation glosses/translations remain CAL-rendered metadata/data rather than adapter inference.

## Request and pagination bounds

The current UI requires one request per explicit step:

- one request to discover dialects;
- one request to list sources for one chosen dialect;
- one request to list citations for one chosen source abbreviation.

No pagination/continuation control was observed on the representative current pages. CAL-MCP must therefore **not invent pagination**. The source list can be large (the Syriac example is about 317 KB) but remains bounded by the shared CAL HTTP response-size ceiling. If CAL later introduces continuation controls, that is a new upstream contract requiring research/tests before public pagination is exposed.

No operation should automatically enumerate dialects, source lists, source abbreviations, lexical entries, or external texts.

## Error/drift boundary

The parsers should distinguish:

- invalid caller-provided public identifiers, rejected before transport;
- CAL/network/upstream HTTP failures from the shared client;
- the two explicit semantic empty markers above;
- parser drift for structurally successful pages whose expected semantic rows/links/markers disappeared or became contradictory.

Returned lexical-entry links must stay on CAL's origin and use the recognized entry family. A malformed returned lemma key is upstream parser drift, not invalid caller input.

## Public-contract implication

The smallest faithful agent-facing surface is a three-step explicit workflow:

```text
cal_external_citation_dialects()
cal_external_citation_sources(dialect_id)
cal_external_citations(source_abbrev)
```

This keeps CAL's current discovery semantics while hiding private endpoint/form details (`dial`, `dial1`, `abbrev`, `cits`, PHP filenames). It also makes the distinction from `cal_citation_text_search` explicit: the latter searches English words *inside* citations, while these operations discover absent source texts and retrieve citations for one exact CAL source abbreviation.

## Sources and research load

Public CAL surfaces inspected:

- `https://cal.huc.edu/searching/CAL_search_page.html`
- `https://cal.huc.edu/citfinder.html`
- `https://cal.huc.edu/display.notext.abbrevs.php?dial=6&dial1=6`
- `https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH`

Branch-only raw probes made **seven bounded CAL GET requests total across three runs**: three fixed structural pages; two fixed negative pages; then the same two negative pages once more solely because the first local output extractor printed stylesheet text instead of visible semantic text. All requests had hard connect/total-time and response-size caps. No loop, source enumeration, citation traversal, lexical-entry follow-up, or corpus extraction occurred. The temporary probe workflows were deleted before planning/implementation.
