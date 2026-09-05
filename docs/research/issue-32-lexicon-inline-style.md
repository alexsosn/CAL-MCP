# Issue #32 research — inline stylesheet contaminates lexicon entry text

Date: 2026-09-05

## Reported live CAL evidence

Issue #32 records bounded live evidence from `cal_entry_web.php?lemma=b+s` on 2026-09-05. CAL now emits an inline `<style>` block in the page `<head>`; the block begins with the `fullentry.css` comment and includes CSS such as `@font-face`. The page still exposes the lexical entry itself, and candidate-list parsing remains correct.

Representative observed corruption in a complete lookup:

- `entry.lemma.headwords == ("CAL: b /*",)`;
- `entry.lemma.part_of_speech == "fullentry.css"`;
- `entry.lemma.gloss` begins with the inline stylesheet comment/content.

The same stylesheet payload was reported for unrelated full entries (`b s`, `w s`, and `yt p`), so this is a shared full-entry parsing defect rather than lemma-specific data.

The live page also carries `<meta name="cal-lemma" content="b+s">`, but switching header sources is explicitly outside this bug fix.

## Current adapter behavior

`src/cal_mcp/lexicon.py` uses `_SemanticHTMLParser` for both browse and full-entry semantic line extraction. `handle_data()` unconditionally appends every HTML data node to `_parts`; there is no suppression for `style` or `script` subtrees.

`parse_lexicon_entry()` then scans the extracted lines for the first value accepted by `_parse_lemma_header(..., require_gloss=True)`. Because CSS tokens can contain dot-bearing ASCII tokens such as `fullentry.css`, the inlined stylesheet can satisfy the generic lemma-header grammar before the real rendered entry header is reached. The parser therefore produces a structurally valid but false `LemmaRef` instead of raising parser drift.

## Existing test gap

The existing reduced fixture `tests/fixtures/cal/entry_br_n.html` was rechecked on 2026-09-04 and contains only rendered semantic entry content. It has no `<head>`, `<style>`, or `<script>` subtree. Existing parser tests therefore cannot detect contamination from newly inlined non-content elements.

## Scope decision

The smallest faithful correction is at semantic HTML extraction:

1. ignore all text inside `style` subtrees;
2. ignore all text inside `script` subtrees;
3. do not change lemma-header heuristics, sense parsing, citation parsing, request behavior, result models, or MCP schemas;
4. retain current fail-closed behavior for genuinely unrecognized entry markup.

Suppressing non-rendered subtrees removes the contamination source instead of filtering CSS-looking strings after extraction.

## Compatibility considerations

The suppression belongs in `_SemanticHTMLParser`, not only in `parse_lexicon_entry`, because `style`/`script` are non-rendered HTML content for every semantic-line consumer. Existing rendered text and link semantics must remain byte-for-byte equivalent after extraction.

Nested or repeated ignored elements must be handled safely; a depth counter is preferable to a single boolean so malformed/nested test input cannot accidentally re-enable data collection early.

## Offline regression evidence required

A reduced 2026-09-05-style fixture should contain:

- a title/meta area;
- inline `<style>` content containing `fullentry.css`, `@font-face`, and dot-bearing CSS tokens;
- an inline `<script>` sentinel;
- a rendered lemma header for `b s` (`b sym. second letter of alphabet`);
- eight minimal complete sense definitions.

Tests must demonstrate that:

- the lemma is parsed from rendered entry content, not CSS/title/script text;
- no returned entry string contains `fullentry.css`, `@font-face`, the CSS comment opener, or the script sentinel;
- eight senses still parse;
- the parsed full-entry lemma agrees with the matching browse candidate on headword/POS/gloss;
- the existing pre-drift fixtures still pass unchanged.

Normal CI remains fully offline and adds no CAL requests.
