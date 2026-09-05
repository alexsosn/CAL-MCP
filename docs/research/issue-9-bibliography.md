# Issue #9 research — CAL bibliography surfaces

**Research date:** 2026-09-05

## Question

Issue #9 originally described bibliography lookup as search by **author, keyword, and lemma**. Before implementation, the current CAL bibliography surfaces were rechecked because those labels do not map to one generic search endpoint.

The current CAL bibliography index is:

- <https://cal.huc.edu/bibliography/index.html>

It currently exposes:

1. search by author;
2. search by **text or subject**;
3. search by lexical item.

There is no current generic free-text bibliography "keyword" form on that surface. The implementation should therefore preserve CAL's actual text/subject taxonomy rather than inventing a free-text keyword API.

CAL also warns on the bibliography index that funding shortfalls have made comprehensive maintenance difficult. CAL-MCP must expose current CAL results faithfully, not imply that the bibliography is complete.

## Research method and load bound

Current HTML/forms were inspected with temporary branch-only GitHub Actions probes. The probes were deliberately bounded to a few user-equivalent requests per run and were deleted before implementation work. Normal project CI remains offline.

No result traversal, pagination loop, crawl, mirror, or bulk bibliography acquisition was performed.

## Author workflow

### Prefix selector

Current entry page:

- <https://cal.huc.edu/namesearch.html>

Observed form contract:

- method: `POST`
- action: `/browsenames.php`
- field: `first3`

CAL's current help describes the input as the first few letters of the author's romanized last name. A bounded probe confirmed practical prefixes such as `Gze` and `Kau`.

`POST /browsenames.php` returns an author selector rather than bibliography records directly. The selector contains one target form:

- method: `POST`
- action: `/getbibauthor.php`
- select field: `myauthor`

For `Kau`, the current selector returned, in order:

- `Kaufhold, H.`
- `Kaufman, Stephen A.`
- `Kaukhchishvili, S.`
- `Kautzsch, E.`

The adapter should preserve CAL order and should not fuzzy-rank or deduplicate those choices.

### Author result

`POST /getbibauthor.php` with `myauthor=Kaufman, Stephen A.` returned a positive bibliography page containing many records. Representative records included:

- Kaufman, Stephen A., “Si'gabbar, Priest of Sahr in Nerab.” *JAOS* 90 (1970): 270–71. — indexed under `Nerab Stelae`;
- a Hebrew-title *Leshonenu* 36 (1971–72) article — indexed under `JBA`, `Influences`, `Mandaic`, `)wwr N`, and `)st) N`;
- “The Job Targum from Qumran.” *JAOS* 93 (1973): 317–27. — indexed under `11QtgJob` and `)rw c`.

The result page exposes bibliography records as rendered citation blocks; it does not expose a stable per-record database identifier or a record-detail URL.

A structural probe confirmed the repeated semantic boundary: **each bibliography record is one `<p>` element**. Within a record CAL may include:

- inline citation markup, including custom title elements and emphasis;
- zero or more `/getbibsigla.php?myauthor=...` links for text/subject tags;
- zero or more `/getbiblemma.php?myauthor=...` links for lemma tags.

The positive Kaufman page contained many subject/text and lemma links. Those are indexing/navigation links attached to records, not stable record IDs.

### Author empty result

The author selector may contain a name for which CAL currently stores no bibliography records. For `Gzella, A.H.`, `/getbibauthor.php` returned the explicit HTTP-200 marker:

```text
NO data FOR Gzella, A.H. ARE CURRENTLY STORED
```

Therefore author discovery and author-result existence are distinct states.

## Text/subject workflow

### Root taxonomy

Current entry page:

- <https://cal.huc.edu/allsigs.html>

This is not a free-text form. It is a current CAL-owned hierarchy of links. Root links use two endpoint families:

- `/browsegclass.php?generalclass=...` for a group that has child selections;
- `/browsesigla.php?generalclass=...&subclass=...` for a concrete bibliography selection.

Observed general classes include dialect/text families and `General Topics`. The current taxonomy contains subject leaves such as `Lexicography`, `Grammar`, and `Literature` as well as text-oriented leaves.

CAL-MCP should discover this hierarchy live instead of hard-coding a permanent topic list.

### Group expansion

`/browsegclass.php?generalclass=<value>` is the current child-discovery surface for a broad class. The public API should treat returned identifiers/labels as CAL-owned selectors and require explicit caller follow-up rather than recursively walking the tree.

### Subject/text result

A bounded request to:

```text
/browsesigla.php?generalclass=General%20Topics&subclass=Lexicography
```

returned a large positive result headed:

```text
CAL BIBLIOGRAPHY SELECTIONS FOR General Topics: Lexicography
```

Records are rendered inline using the same bibliography-record family as author results. Links such as `/getbibsigla.php?myauthor=Lexicography` are record tags/navigation, not record identifiers.

No pagination or continuation control was observed on the sampled positive subject page. CAL-MCP should therefore make one bounded request and rely on the shared response-size limit rather than inventing pagination.

### Subject/text empty result

A nonexistent leaf returned HTTP 200 with an explicit marker:

```text
NO CURRENT ENTRIES FOR: NoSuchCALTopicXYZ
```

That marker is a valid empty result. A successful page lacking either recognizable records or the appropriate explicit empty marker should be treated as parser drift.

## Lemma bibliography workflow

Current selector page:

- <https://cal.huc.edu/lemmas_list.html>

Observed form contract:

- method: `POST`
- action: `/getbiblemma.php`
- field: `myauthor`

The historical field name is misleading; the submitted value is a CAL lemma key.

The current UI uses client-side rendering around the selector, so the implementation should **not** depend on scraping the selector's raw `<option>` list. CAL-MCP already has lexicon lookup and canonical lemma identities, so the bibliography tool can accept an explicit CAL lemma key directly.

Current indexed CAL pages confirm bibliography results for canonical keys including homographs, for example `)bwl N` and `sbk#2 N`. The same CAL lemma-key structure used by the concordance capability is therefore applicable here.

A nonexistent lemma request returned HTTP 200 with:

```text
NO data FOR zzzzzz N ARE CURRENTLY STORED
```

This is a valid empty result, distinct from malformed or changed output.

## Record representation

CAL bibliography output is richer and less normalized than a conventional citation database. The adapter should not infer a synthetic DOI, year field, publication type, or stable record ID when CAL does not provide one.

A fidelity-oriented structured record should preserve:

- the complete rendered citation text, normalized only for HTML whitespace;
- ordered CAL indexing tags;
- each tag's kind (`subject`/`text` versus `lemma`), label, and absolute same-origin CAL URL;
- original record order;
- duplicate records/tags if CAL renders them.

The adapter should **not** deduplicate or rerank bibliography records.

## Navigation/link boundary

Lessons from the concordance review apply directly here. Returned bibliography navigation is trustworthy only when:

- it resolves to the same origin as the CAL response;
- the final path segment is exactly the expected endpoint (`getbibsigla.php`, `getbiblemma.php`, `browsegclass.php`, or `browsesigla.php` as appropriate);
- required query values occur exactly once and agree with the rendered label/selection semantics where CAL provides both.

Off-origin links and same-origin endpoint-name lookalikes are parser drift, not data to surface.

## Pagination and boundedness

No pagination/continuation control was observed on the sampled author, subject, or lemma bibliography result pages. The public contract should state this explicitly:

- one CAL request per result operation;
- one CAL request per discovery operation;
- no automatic traversal from author-prefix selection to author results;
- no recursive text/subject taxonomy expansion;
- no synthetic result pagination;
- the existing decoded-response-size limit is the hard per-request bound.

If CAL later adds a paginator, returning an unrepresented partial page must be treated as a contract change and researched before exposing traversal.

## Recommended public capability split

The current surface is best represented by five explicit operations:

1. `cal_bibliography_authors(prefix)` — one author-prefix selector request;
2. `cal_bibliography_author(author)` — one exact-author result request;
3. `cal_bibliography_topics(general_class=None)` — root or one-level CAL text/subject taxonomy discovery;
4. `cal_bibliography_topic(general_class, subclass)` — one concrete text/subject bibliography selection;
5. `cal_bibliography_lemma(lemma_key)` — one explicit lemma bibliography request.

This split keeps every network action caller-controlled and avoids pretending CAL has a generic bibliography keyword endpoint.

## Provenance

Every successful or explicit-empty result should expose:

- `source = "CAL"`;
- final CAL source URL;
- retrieval timestamp;
- operation/mode;
- submitted prefix, author, taxonomy fields, or lemma key as applicable.

## Research conclusion

Issue #9 should be respecified from “author, keyword, and lemma” to **author, current CAL text/subject taxonomy, and lemma**. The adapter should preserve rendered bibliography records and their CAL-owned indexing links rather than normalizing them into a citation schema CAL does not supply.
