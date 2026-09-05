# Corpus context workflow

CAL-MCP separates text discovery, page reading, token analysis, and lexical/concordance follow-up. This preserves CAL's coordinates and keeps every network step explicit.

## Discover a text

Use `cal_text_search` when you have a topic/name:

```text
cal_text_search(query="Tel Dan")
```

Use `cal_text_catalogue` when you want one explicit level of CAL's current text catalogue/category navigation.

Returned `file_id`, category/subtext identifiers, and labels are CAL-owned navigation identifiers. Preserve them exactly rather than decoding their digits into a local taxonomy.

See [Texts](../tools/texts.md) and [CAL identifiers](../concepts/cal-identifiers.md).

## Read one bounded page

Pass a chosen `file_id` to `cal_text_page`:

```text
cal_text_page(file_id="13250")
```

Where CAL provides pagination, CAL-MCP exposes the researched bounded page semantics and keeps CAL's internal representation private. It does not expose CAL's unbounded `show all` option or automatically fetch the next page.

Some valid CAL texts are not paginated; page metadata can therefore be absent rather than fabricated.

## Inspect one token

Text rows may contain machine lexical-analysis coordinates and token positions. Use them in a separate explicit call:

```text
cal_token_analysis(coordinate="...", word_index=0)
```

`word_index` is the zero-based token position expected by the current CAL lexical-analysis surface. The result preserves all CAL analyses in returned order when a token is ambiguous.

CAL-MCP does not automatically analyse every token on a page or choose a preferred analysis.

See [Token analysis](../tools/token-analysis.md).

## Follow a token into the lexicon

A token analysis can return reusable CAL lemma keys. Select one explicitly and pass it to `cal_lexicon_lookup` if the research question needs the full lexical entry.

This second request has its own provenance and retrieval timestamp. Do not treat token analysis and lexicon retrieval as one hidden transaction.

See [Lexicon](../tools/lexicon.md).

## Add concordance context

For frequency/KWIC work, reuse a returned lemma key and choose the narrowest scope:

- one text: `cal_text_concordance`;
- explicit text set: `cal_kwic_texts`;
- dialect discovery: `cal_kwic_dialects`;
- one dialect's hits: `cal_kwic_dialect`.

Returned KWIC/context navigation is not automatically expanded into full text pages.

See [Concordance and KWIC](../tools/concordance.md).

## Online text versus external citation source

`cal_text_page` is for CAL's online text corpus. Source abbreviations from `cal_external_citation_sources` identify cited-but-not-online sources and must not be treated as online `file_id` values.

Use [External citations](../tools/external-citations.md) for that separate data family.

## Targum and Syriac composition

CAL's single-Targum reading links use the ordinary text browser, so CAL-MCP deliberately reuses `cal_text_page` rather than adding a duplicate Targum text reader. Word-level analysis then uses `cal_token_analysis` explicitly.

`cal_syriac_texts` similarly returns one category's current text/group navigation. Opening a returned group/text remains another explicit step through the general text tools where applicable.

See [Targum Studies](../tools/targum.md) and [Syriac Studies](../tools/syriac.md).

## Reproducibility

For a passage-level analysis, retain:

- text/file/subtext/page identifiers;
- CAL machine/display coordinates as returned;
- token index when token analysis was used;
- each call's `source_url` and `retrieved_at`;
- selected lemma keys used in follow-up calls.

See [Reproducible citations](reproducible-citations.md).