# CAL Syriac Studies

CAL-MCP exposes three bounded task-level operations over CAL's current Syriac Studies interfaces. Every public operation performs exactly **one** user-initiated CAL request. Returned text/group navigation, lexicon-entry links, and Peshitta chapter links are metadata for explicit follow-up calls; CAL-MCP never walks categories, opens every text, expands every lexical entry, advances through verses, or builds a local Syriac corpus.

## Which tool to use

| Goal | Tool |
| --- | --- |
| Browse one CAL Syriac text category | `cal_syriac_texts(category)` |
| List one CAL-curated class of Syriac headwords absent from *A Syriac Lexicon* | `cal_syriac_missing_words(category)` |
| Compare one biblical verse in MT and CAL's Peshitta view | `cal_syriac_peshitta_parallel(book, chapter, verse)` |

The CAL Syriac Studies page also links to citations from texts that are not in the online text database. That is the same generic external-citation family tracked by issue #13, so issue #11 deliberately does **not** duplicate it as a Syriac-only tool.

Ordinary Syriac lexicon lookup, text retrieval, token analysis, concordance, and KWIC likewise stay on the existing general CAL-MCP tools rather than being reimplemented behind specialist names.

## `cal_syriac_texts`

```text
cal_syriac_texts(category: string)
```

`category` is a stable CAL-MCP descriptive slug. The current supported values are:

```text
ot-peshitta
old-syriac-gospels
nt-peshitta
apocryphal-pseudepigraphal
commentaries
metrical-homilies-hymns
dispute-poems
religion
archival
canonical
documents
syro-roman-law-book
canon-law
magic
science-philosophy
history
novels-histories
martyrologies
various
inscriptions
```

Some CAL Syriac categories are static pages; others use CAL's numeric category selector internally. Numeric CAL category values are private adapter details and are never public MCP parameters.

Each item preserves:

- CAL's upstream text/group identifier;
- CAL's rendered label;
- `navigation_kind`, either `text` or `group`;
- an absolute same-origin CAL navigation URL;
- an optional same-origin file-information URL.

A `text` item points directly into CAL's ordinary text browser. A `group` item points to another CAL subtext listing. Neither target is followed automatically. Callers decide whether to use the existing text tools in a later explicit action.

The parser rejects duplicate identifiers, multiple navigation targets in one semantic row, detached or contradictory information links, malformed identifiers, cross-origin links, wrong category headings, and successful-looking pages whose current category-row semantics disappeared.

## `cal_syriac_missing_words`

```text
cal_syriac_missing_words(category: string)
```

This exposes CAL's own curated lists headed as words “not found in *A Syriac Lexicon*” that nevertheless have citations in CAL. The comparison target is therefore **CAL's published *A Syriac Lexicon* surface**. CAL-MCP does not reinterpret the lists as SEDRA coverage, a universal Syriac-dictionary comparison, or an automatically inferred lexical equivalence.

Supported categories are:

```text
adjectives
adverbs
miscellaneous
nomina-agentis
abstracts
verbal-nouns
verbs
masculine-nouns
feminine-nouns
```

Each result preserves:

- `dictionary_label` (`A Syriac Lexicon` from CAL's current interface);
- CAL's rendered heading;
- ordered items;
- canonical CAL `lemma_key`;
- CAL-rendered headword/POS label;
- optional rendered note/gloss text;
- absolute same-origin CAL entry URL;
- provenance.

Returned entry URLs are not followed. Use `cal_lexicon_lookup` in a separate explicit call if the full CAL entry is needed.

The parser fails closed on duplicate lemma keys, malformed or noncanonical lemma links, cross-origin entry targets, missing list semantics, or a page whose dictionary-comparison heading no longer matches the selected surface.

## `cal_syriac_peshitta_parallel`

```text
cal_syriac_peshitta_parallel(
    book: string,
    chapter: integer,
    verse: integer,
)
```

The tool submits one explicit verse to CAL's current MT/Peshitta comparison endpoint and preserves:

- `status`: `found` or `not_found`;
- CAL's exact public book label and current internal book identifier;
- chapter and verse;
- rendered MT Hebrew text when found;
- CAL's Peshitta label;
- rendered Syriac Peshitta text when found;
- CAL's same-origin Peshitta chapter URL when found;
- provenance.

The accepted book labels are CAL's current selector labels:

```text
Gen, Exod, Levit, Numb, Deut, Joshua, Judges,
1 Sam, 2 Sam, 1 Kings, 2 Kings, Isaiah, Jeremiah, Ezekiel,
Hosea, Joel, Amos, Obadiah, Jonah, Micah, Nahum, Hab., Zeph.,
Haggai, Zechariah, Malachi, Psalms, Job, Proverbs, Ruth,
Song of Songs, Qoheleth, Lamentations, Esther,
1 Chronicles, 2 Chronicles
```

`chapter` and `verse` must be positive integers no greater than 999. Invalid public values fail before transport.

CAL currently reports a nonexistent coordinate through an HTTP-200 page containing an explicit `error in coord` / `error in coordinate` marker. CAL-MCP returns `status: "not_found"` only when that marker occurs without a contradictory valid comparison result. Wrong-reference headings, marker/result contradictions, missing Hebrew or Syriac result semantics, unexpected endpoint families, or cross-origin chapter links fail closed as `SyriacParseError`.

The returned Peshitta chapter URL is navigation metadata only. CAL-MCP never follows previous/next verse links or prefetches the chapter.

## Unicode and rendered-text fidelity

CAL's rendered Hebrew and Syriac text is preserved through ordinary HTML text extraction. Script/style content is excluded from semantic parsing and malformed unclosed ignored subtrees fail closed rather than contributing false markers.

CAL-MCP does not add vocalization, transliteration, morphology, emendation, or reconstructed readings to these specialist results.

## Request and traversal bounds

Every public Syriac Studies operation performs exactly one CAL request:

- one selected text-category request;
- one selected missing-word-category request;
- one selected MT/Peshitta verse request.

There is no hidden category enumeration, group traversal, text fetch, dictionary-entry expansion, alphabet walk, verse walking, chapter prefetch, external-citation crawl, background indexing, or local mirror. The shared CAL HTTP client continues to enforce origin, redirect, timeout, concurrency, retry, cache/single-flight, and response-size policy.

Private upstream fields and values such as numeric `category`, `bookname`, `cset`, `file`, `keyword`, and `coord` are adapter implementation details and are not public MCP parameters.

## Provenance

Results include adapter provenance with:

- `source: "CAL"`;
- actual `source_url`;
- timezone-aware `retrieved_at`;
- operation name;
- selected public category or book/chapter/verse;
- CAL's current internal category or book identifier when applicable.

Duplicate-request cache hits retain the original upstream retrieval timestamp and source URL under the shared request-layer provenance contract.

## Fixture-backed contracts

The normal test suite is offline. Reduced semantic fixtures were captured/rechecked during the bounded **2026-09-05** Syriac audit and cover:

- dynamic Metrical Homilies and Hymns category rows with both direct text and grouped navigation plus file-information links;
- static OT Peshitta category rows;
- a current missing-verbs page with canonical CAL lemma links and notes;
- Gen 1:1 MT/Peshitta Unicode output and CAL's Peshitta chapter link;
- CAL's explicit coordinate-not-found response;
- cross-origin, duplicate, contradictory, ambiguous, missing-semantic, noncanonical-link, wrong-heading, and ignored-script/style drift cases.

These fixtures are reduced parser contracts, not archived CAL pages. The live research used **8 bounded CAL requests total** and did not traverse categories, texts, dictionary entries, verses, chapters, or external citations automatically.
