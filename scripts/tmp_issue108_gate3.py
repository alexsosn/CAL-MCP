from pathlib import Path

server = Path("src/cal_mcp/server.py")
text = server.read_text(encoding="utf-8")
old = (
    '        "explicit source, edition, editorial, and other free-form Text Information metadata "\n'
    '        "for one returned file/subtext identifier. Use cal_token_analysis for every CAL lexical "\n'
)
new = (
    '        "explicit source, edition, editorial, and other free-form Text Information metadata "\n'
    '        "for one returned file/subtext identifier. Use cal_text_line_comments with one returned "\n'
    '        "TextLine.coordinate to retrieve CAL\'s explicit line citations/comments/translations "\n'
    '        "without following returned lexicon links. Use cal_token_analysis for every CAL lexical "\n'
)
if text.count(old) != 1:
    raise SystemExit(f"unexpected server instructions anchor count: {text.count(old)}")
server.write_text(text.replace(old, new, 1), encoding="utf-8")

docs = Path("docs/tools/texts.md")
text = docs.read_text(encoding="utf-8")
intro_old = (
    "CAL-MCP exposes four bounded tools for discovering CAL texts, retrieving CAL's explicit "
    "text-information metadata, and reading one rendered text page at a time."
)
intro_new = (
    "CAL-MCP exposes five bounded tools for discovering CAL texts, retrieving CAL's explicit "
    "text-information metadata, reading one rendered text page at a time, and explicitly "
    "retrieving CAL line comments/translations."
)
if text.count(intro_old) != 1:
    raise SystemExit(f"unexpected intro anchor count: {text.count(intro_old)}")
text = text.replace(intro_old, intro_new, 1)

table_old = (
    "| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | "
    "`cal_text_information(file_id, subtext_id=None)` |\n"
    "| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |"
)
table_new = (
    "| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | "
    "`cal_text_information(file_id, subtext_id=None)` |\n"
    "| Retrieve CAL citations/comments/translations for one returned line coordinate | "
    "`cal_text_line_comments(coordinate)` |\n"
    "| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |"
)
if text.count(table_old) != 1:
    raise SystemExit(f"unexpected tool-table anchor count: {text.count(table_old)}")
text = text.replace(table_old, table_new, 1)

page_heading = "## `cal_text_page`\n"
if text.count(page_heading) != 1:
    raise SystemExit(f"unexpected page heading count: {text.count(page_heading)}")
section = """## `cal_text_line_comments`

```text
cal_text_line_comments(coordinate: string)
```

Use the exact `coordinate` returned on a caller-selected `TextLine` from `cal_text_page`. CAL line coordinates are opaque ASCII-alphanumeric identifiers on this route; CAL-MCP does not accept a `comment_url`, arbitrary CAL path, or arbitrary query selectors.

One explicit call submits at most one new logical CAL request to `comment.php?coord=<coordinate>`. A completed cache hit performs zero new upstream I/O. Returned lexicon-entry links are validated and preserved as metadata but are never followed automatically.

The result contains `status: "found" | "no_citations"`, the requested coordinate, ordered `records`, and text provenance. Each found record preserves CAL's rendered reference, source citation text, optional translation/comment text, lemma key, headword, optional part of speech, optional gloss, and validated absolute entry URL. CAL's exact `NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED` state maps to `no_citations` with an empty record list. It does **not** map to `not_found`, because current CAL uses the same state for a deliberately invalid coordinate and this endpoint alone cannot prove whether the line exists.

Malformed response identity, contradictory empty-state/content combinations, structurally incomplete records, foreign or malformed entry links, and unrecognized successful markup fail closed as parser drift. The parent `cal_text_page` remains non-prefetching: reading a page does not retrieve comments for any line.

"""
text = text.replace(page_heading, section + page_heading, 1)

request_old = (
    "- no automatic text-information lookup from discovery/page results;\n"
    "- no metadata-link traversal;"
)
request_new = (
    "- no automatic text-information lookup from discovery/page results;\n"
    "- no automatic line-comment lookup from page results;\n"
    "- no metadata-link traversal;"
)
if text.count(request_old) != 1:
    raise SystemExit(f"unexpected request-bounds anchor count: {text.count(request_old)}")
text = text.replace(request_old, request_new, 1)

fixture_old = (
    "- a text-information lookup preserving Ephrem source/edition/editorial/quality notes in CAL order, "
    "plus CAL's explicit `No information on record for this text.` missing state;"
)
fixture_new = (
    fixture_old
    + "\n- a line-comments lookup preserving ordered CAL citation/comment records, nullable translation "
    "text, validated lexicon-entry metadata, and the explicit no-citations state;"
)
if text.count(fixture_old) != 1:
    raise SystemExit(f"unexpected fixture anchor count: {text.count(fixture_old)}")
text = text.replace(fixture_old, fixture_new, 1)
docs.write_text(text, encoding="utf-8")
