# Lexical research workflow

CAL-MCP keeps lexical discovery, entry retrieval, attestations, and bibliography as separate explicit operations. This avoids turning one question into hidden corpus traversal and preserves CAL's own ambiguity/order.

## Start from an Aramaic form

Use `cal_lexicon_lookup` directly:

```text
cal_lexicon_lookup(query="br")
```

If CAL returns multiple candidates, retain their order and select a returned canonical `lemma_key` explicitly before a precise follow-up. Do not construct a preferred lemma from an English gloss or local linguistic guess.

See [Lexicon](../tools/lexicon.md) and [Input and transliteration](../concepts/input-and-transliteration.md).

## Start from English

Use `cal_gloss_search` when English describes the lexical meaning you are looking for:

```text
cal_gloss_search(query="camel#")
```

Use `cal_citation_text_search` instead when you need English words occurring in the translations/text of CAL lexical citations.

A search result is discovery metadata, not an automatically expanded lexicon entry. Pass a selected returned `lemma_key` to `cal_lexicon_lookup` in a second explicit call when full lexical detail is needed.

See [English search](../tools/search.md).

## Move from a lemma to attestations

Choose the smallest concordance scope that matches the research question:

- one known text → `cal_text_concordance`;
- one lemma over explicit text IDs → `cal_kwic_texts`;
- discover dialect-level counts → `cal_kwic_dialects`;
- inspect one chosen dialect → `cal_kwic_dialect`.

Detailed source context remains a separate `cal_text_page` request. CAL-MCP does not follow every KWIC/citation link automatically.

See [Concordance and KWIC](../tools/concordance.md) and [Corpus context](corpus-context.md).

## Move from a lemma to bibliography

For a canonical lemma key returned by CAL-MCP, use `cal_bibliography_lemma`. The bibliography fixture contract includes keys such as `cly V`:

```text
cal_bibliography_lemma(lemma_key="cly V")
```

For bibliography organized by author, first discover the exact author choice with `cal_bibliography_authors`, then call `cal_bibliography_author`. Use `cal_bibliography_keyword` for one exact CAL text/subject tag.

The recent-years bibliography snapshot is not part of the frozen v0.1 contract and is tracked in issue #39 rather than silently queried as a background update feed.

See [Bibliography](../tools/bibliography.md).

## Dictionary spelling collation

When your starting evidence is a page in one of CAL's supported dictionaries, use `cal_dictionary_collation`:

```text
cal_dictionary_collation(source="jastrow", page="705")
```

Each returned row keeps both CAL's displayed dictionary spelling and the linked canonical `target_lemma_key`. If those differ, preserve the distinction; following the target into `cal_lexicon_lookup` is another explicit action.

See [Dictionary spelling collation](../tools/dictionary-collation.md).

## External citations

Some lexical citations belong to sources cited by CAL but not available as complete online CAL texts. Discover them through the explicit dialect → source → citations sequence, then optionally follow a returned lemma into the lexicon.

Do not pass an external source abbreviation to `cal_text_page` as though it were an online CAL `file_id`.

See [External citations](../tools/external-citations.md).

## Targum/Syriac lexical workflows

Targum-specific lemma counts use `cal_targum_concordance`. MT-Hebrew reflex research uses the two-step `cal_targum_hebrew_lemmas` → `cal_targum_hebrew_reflexes` workflow so the caller explicitly selects CAL's opaque Hebrew lemma ID.

CAL's curated Syriac comparison against *A Syriac Lexicon* is exposed by `cal_syriac_missing_words`; it is CAL's research surface, not an adapter-inferred dictionary comparison.

See [Targum Studies](../tools/targum.md) and [Syriac Studies](../tools/syriac.md).

## Preserve provenance

For every step that contributes evidence, retain its `source_url`, `retrieved_at`, and relevant CAL identifiers. A later step may be retrieved at a different time, so do not replace the provenance of earlier results with the final call's timestamp.

See [Provenance and citation](../concepts/provenance-and-citation.md).