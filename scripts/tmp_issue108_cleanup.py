from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        return
    if old_count == 0 and new_count == 1:
        return
    raise SystemExit(f"{path}: unexpected anchor state old={old_count} new={new_count}")


replace_once(
    "src/cal_mcp/server.py",
    '        "explicit source, edition, editorial, and other free-form Text Information metadata "\n'
    '        "for one returned file/subtext identifier. Use cal_token_analysis for every CAL lexical "',
    '        "explicit source, edition, editorial, and other free-form Text Information metadata "\n'
    '        "for one returned file/subtext identifier. Use cal_text_line_comments with one "\n'
    '        "returned TextLine.coordinate for CAL line comments/translations. Use "\n'
    '        "cal_token_analysis for every CAL lexical "',
)

docs = Path("docs/tools/texts.md")
text = docs.read_text(encoding="utf-8")
if "## `cal_text_line_comments`" not in text:
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
        raise SystemExit("unexpected text docs intro anchor")
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
        raise SystemExit("unexpected text docs table anchor")
    text = text.replace(table_old, table_new, 1)

    section = """## `cal_text_line_comments`

```text
cal_text_line_comments(coordinate: string)
```

Use the exact `coordinate` returned on a caller-selected `TextLine` from `cal_text_page`. CAL line coordinates are opaque ASCII-alphanumeric identifiers on this route; CAL-MCP accepts 1–64 ASCII letters/digits and does not accept a `comment_url`, arbitrary CAL path, or arbitrary query selectors.

One explicit call submits at most one new logical CAL request. A completed cache hit performs zero new upstream I/O. Returned lexicon-entry links are validated and preserved as metadata but are never followed automatically.

The result contains `status: "found" | "no_citations"`, the requested coordinate, ordered `records`, and provenance. Each found record preserves CAL's rendered reference, optional source citation text, optional translation/comment text, the opaque returned lemma key, rendered headword, optional part of speech, optional gloss, and validated same-origin entry URL.

CAL's exact `NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED` state maps to `no_citations` with an empty record list. It does **not** map to `not_found`: current CAL returns the same state for a deliberately invalid coordinate, so this endpoint alone cannot prove whether the line exists.

Malformed response identity, contradictory empty-state/content combinations, structurally incomplete records, foreign or malformed entry links, repeated/empty lemma selectors, and unrecognized successful markup fail closed as parser drift. `cal_text_page` does not prefetch comments for any line.

"""
    heading = "## `cal_text_page`\n"
    if text.count(heading) != 1:
        raise SystemExit("unexpected text page heading")
    text = text.replace(heading, section + heading, 1)

    text = text.replace(
        "- `comment_url`: CAL's line-comment URL when CAL renders one.\n",
        "- `comment_url`: CAL's line-comment URL when CAL renders one; use the returned line "
        "`coordinate` with `cal_text_line_comments` for an explicit MCP-native follow-up.\n",
        1,
    )
    text = text.replace(
        "- no automatic text-information lookup from discovery/page results;\n"
        "- no metadata-link traversal;",
        "- no automatic text-information lookup from discovery/page results;\n"
        "- no automatic line-comment lookup from page results;\n"
        "- no metadata-link traversal;",
        1,
    )
    text = text.replace(
        "provenance also records the requested `file_id`, `subtext_id`, `category_id`, one-based "
        "page, or original/submitted search query.",
        "provenance also records the requested `file_id`, `subtext_id`, `category_id`, one-based "
        "page, line coordinate, or original/submitted search query.",
        1,
    )
    docs.write_text(text, encoding="utf-8")
