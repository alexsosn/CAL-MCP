# Getting started

CAL-MCP works best when each tool call corresponds to one explicit research step. Start with the narrowest operation that answers the immediate question, then pass CAL-returned identifiers into a second tool only when you actually need the next layer of context.

For setup, see [Installation](installation.md). For identifier semantics, see [CAL identifiers](concepts/cal-identifiers.md).

## Look up an Aramaic form

Use `cal_lexicon_lookup` when you already have an Aramaic form/root/headword or a canonical CAL lemma key.

```text
cal_lexicon_lookup(query="br")
```

If CAL returns several lemma choices, choose one returned `lemma_key` explicitly rather than guessing a preferred analysis. A follow-up exact lookup may then use that key.

See [Lexicon](tools/lexicon.md) and [Input and transliteration](concepts/input-and-transliteration.md).

## Start from an English concept

Use `cal_gloss_search` to discover CAL lemmas by an English gloss. If the question concerns English words inside CAL's lexical citations rather than lexical glosses, use `cal_citation_text_search` instead.

```text
cal_gloss_search(query="camel#")
```

Returned lemma keys are reusable in `cal_lexicon_lookup`, concordance tools, or bibliography lookup. CAL-MCP does not fetch all matching entries automatically.

See [English search](tools/search.md) and [Lexical research](guides/lexical-research.md).

## Read a CAL text and inspect one token

Use one explicit discovery step, then one page request. The current reduced text fixtures include a `Tel Dan` search result with CAL file `13250`:

```text
cal_text_search(query="Tel Dan")
cal_text_page(file_id="13250")
```

A text page preserves CAL machine coordinates and token positions. A separate token-analysis fixture uses machine coordinate `7102601002203`, zero-based token index `0`, and returns two ordered analyses:

```text
cal_token_analysis(coordinate="7102601002203", word_index=0)
```

CAL-MCP never analyses every token on a page automatically.

See [Texts](tools/texts.md), [Token analysis](tools/token-analysis.md), and [Corpus context](guides/corpus-context.md).

## Find attestations with concordance/KWIC

Use the smallest concordance scope you know:

- `cal_text_concordance` — frequency index for one explicit CAL text;
- `cal_kwic_texts` — one lemma across an explicit set of text IDs;
- `cal_kwic_dialects` — discover current dialect-level counts for one lemma;
- `cal_kwic_dialect` — retrieve one selected dialect's KWIC hits.

Returned lemma/text/dialect identifiers should come from CAL-MCP results where possible. Detailed context remains a separate text-page operation rather than a hidden fetch.

See [Concordance and KWIC](tools/concordance.md).

## Find bibliography

Choose the workflow that matches the identifier you have:

- discover/select an author with `cal_bibliography_authors` then `cal_bibliography_author`;
- search one exact CAL text/subject tag with `cal_bibliography_keyword`;
- search one exact CAL lemma key with `cal_bibliography_lemma`.

CAL's separate recent-years bibliography snapshot is not part of the v0.1 tool contract; it is deferred to issue #39.

See [Bibliography](tools/bibliography.md).

## Work with cited sources that are not online CAL texts

Use the staged external-citation workflow. Current reduced fixtures include dialect ID `6` (`Syriac`) and source abbreviation `1CorH`:

```text
cal_external_citation_dialects()
cal_external_citation_sources(dialect_id="6")
cal_external_citations(source_abbrev="1CorH")
```

Each stage is explicit. A returned external-source abbreviation is not an online CAL `file_id`, and CAL-MCP does not reconstruct the missing source text.

See [External citations](tools/external-citations.md).

## Compare Targums or study Hebrew reflexes

For one biblical verse across current CAL Targum readings, use `cal_targum_parallel`. For a Targum-specific lemma count, use `cal_targum_concordance`.

The MT-Hebrew reflex workflow is deliberately two-step; current fixtures include selector ID `1751` under Onqelos:

```text
cal_targum_hebrew_lemmas(initial="mem", targum="onqelos")
cal_targum_hebrew_reflexes(targum="onqelos", mt_lemma_id="1751")
```

Use a returned opaque `mt_lemma_id`; do not infer its meaning. Single-source Targum chapter reading composes through the ordinary text tools instead of a duplicate browser.

See [Targum Studies](tools/targum.md).

## Work with Syriac Studies

CAL-MCP exposes:

- `cal_syriac_texts` for one current Syriac text category;
- `cal_syriac_missing_words` for CAL's curated comparison against *A Syriac Lexicon*;
- `cal_syriac_peshitta_parallel` for one MT/Peshitta verse.

Syriac citations from sources not available as full CAL texts use the same [external-citation workflow](tools/external-citations.md) rather than a duplicate Syriac-only tool.

See [Syriac Studies](tools/syriac.md).

## Collate one dictionary page

Use `cal_dictionary_collation` when the research question begins from a page reference in one of CAL's supported dictionaries. The fixture-backed Jastrow example uses page `705`:

```text
cal_dictionary_collation(source="jastrow", page="705")
```

The result preserves the difference between CAL's rendered dictionary spelling and its linked canonical lemma key. Following those lemma keys is a separate explicit lexicon operation.

See [Dictionary spelling collation](tools/dictionary-collation.md).

## Read results reproducibly

Every successful CAL-backed result includes CAL provenance, including the actual upstream source URL and retrieval timestamp. CAL is a live scholarly database, so keep those fields with results you quote or analyze.

See [Provenance and citation](concepts/provenance-and-citation.md), [Reproducible citations](guides/reproducible-citations.md), and [Errors and upstream drift](concepts/errors-and-upstream-drift.md).