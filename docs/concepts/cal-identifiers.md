# CAL identifiers and coordinates

CAL-MCP exposes upstream identifiers only when they are useful for faithfully composing CAL operations. These values belong to the Comprehensive Aramaic Lexicon, not to CAL-MCP, and the adapter does not claim a stronger stability guarantee than CAL itself provides.

## General rule

Treat every CAL identifier as an **opaque upstream identifier** unless the corresponding tool explicitly documents a positional meaning.

Do not infer chronology, dialect, textual hierarchy, or semantic identity from the digits in an identifier. Preserve the identifier together with CAL provenance and use it only in the CAL operations that returned/documented it.

## Identifier types currently exposed

### `file_id`

A CAL text/file identifier used by the current text catalogue, topic-search, and text-browser surfaces.

CAL-MCP preserves `file_id` as a string of decimal digits. It is not converted to an integer because numeric conversion could erase leading zeroes and would falsely imply arithmetic semantics.

### `subtext_id`

An optional CAL navigation identifier used when one file has explicitly selectable subtexts/sections in the current text interfaces.

It is preserved as an opaque decimal string. CAL-MCP does not infer a subtext identifier from a chapter label or from the file identifier.

### `category_id`

A CAL text-catalogue navigation identifier. It is used only to request one explicit catalogue level returned by CAL.

CAL-MCP does not recursively enumerate category identifiers or assume that they form a stable taxonomy outside the current CAL interface.

### Machine line `coordinate`

The CAL text browser links words and line comments using machine coordinates such as those present in `bablex.php?coord=...` and `comment.php?coord=...` links. CAL-MCP preserves that explicit coordinate as a string.

A machine coordinate is different from the human-readable `display_coordinate`. CAL-MCP does not decode its digits into an undocumented local coordinate scheme and does not synthesize a coordinate when CAL does not render one.

### `display_coordinate`

The human-readable locator CAL renders for a text line, for example a manuscript/page/side/line notation or a short line number. This is scholarly display data, not a CAL-MCP-generated identifier.

Because some CAL lines may not expose the same display form, the field is nullable. Its absence must not be replaced by a guessed locator.

### Token `word_index`

CAL lexical links pair a machine coordinate with a `word` position. CAL-MCP exposes this current positional value as integer `word_index` because it is explicitly used as a zero-based position within CAL's linked line operation.

This is not a corpus-global token number. It is meaningful only together with the corresponding CAL coordinate and provenance.

### Lexicon lemma keys

Lexicon lookup may expose exact CAL lemma keys for explicit homograph selection. Those keys are also CAL-owned identifiers. Their spelling and grammatical suffixes should be preserved exactly rather than reconstructed from an adapter-side lemma model.

## Page numbers are adapter navigation, not CAL identifiers

`cal_text_page` intentionally exposes a one-based `page` parameter because that matches the page number CAL displays to researchers. The current upstream HTML handler uses a zero-based internal page parameter; CAL-MCP translates between them and keeps the upstream parameter private.

A page number is therefore an adapter navigation value, not a persistent identifier. Short CAL texts can be unpaginated; in those cases CAL-MCP does not invent `page_count`, previous, or next values.

## Preservation and validation

For opaque decimal identifiers (`file_id`, `subtext_id`, `category_id`, machine coordinates), CAL-MCP:

- validates only the representation needed for a safe current CAL request;
- preserves the digit string exactly;
- does not cast it to an integer for storage;
- does not normalize leading zeroes away;
- does not derive one identifier from another;
- does not claim an identifier is permanent merely because it is exposed publicly today.

If CAL changes an identifier or navigation scheme, the endpoint adapter and fixture contract must be reviewed. The MCP schema should change only if the scholarly/public semantics have actually changed.

## Provenance is part of identity-sensitive use

For reproducible work, keep identifiers together with:

- `source = "CAL"`;
- the CAL source URL;
- retrieval timestamp;
- the operation/query that produced the identifier where relevant.

This is especially important because CAL describes its data as a live work in progress. An identifier lets a later call address CAL; provenance records when and from which surface the adapter observed it.

## Composition example

A typical bounded workflow is:

1. `cal_text_search("Tel Dan")` returns a CAL `file_id`.
2. `cal_text_page(file_id, page=1)` returns lines with CAL machine coordinates and token `word_index` values.
3. A later token-analysis capability can use the explicit coordinate/index pair without CAL-MCP having inferred either value.

Each step remains a separate user-initiated CAL request. CAL-MCP does not turn the identifiers into a background crawl or local corpus index.
