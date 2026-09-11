from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one replacement anchor, found {count}: {old!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Review-regression hardening.
replace_once(
    "src/cal_mcp/texts.py",
    "from cal_mcp.lexicon import _Line, _Link, _parse_lines\nfrom cal_mcp.syriac import syriac_text_category_slugs\n",
    "from cal_mcp.lemma_key import validate_lemma_key\n"
    "from cal_mcp.lexicon import _Line, _Link, _parse_lines\n"
    "from cal_mcp.syriac import syriac_text_category_slugs\n",
)
replace_once(
    "src/cal_mcp/texts.py",
    """        if tag == \"p\" and self._record is not None:\n            if self._span_parts is not None or self._anchor_parts is not None or self._in_gloss:\n                raise TextParseError(\n                    \"CAL line-comments record closes with unfinished semantic markup\"\n                )\n""",
    """        if tag == \"p\" and self._record is not None:\n            if (\n                self._span_parts is not None\n                or self._anchor_parts is not None\n                or self._in_reference\n                or self._in_gloss\n            ):\n                raise TextParseError(\n                    \"CAL line-comments record closes with unfinished semantic markup\"\n                )\n""",
)
replace_once(
    "src/cal_mcp/texts.py",
    """    if lemma_values is None or len(lemma_values) != 1 or not lemma_values[0]:\n        raise TextParseError(\"CAL line-comments lexical-entry link lacks one lemma selector\")\n    if cits_values != [\"all\"]:\n        raise TextParseError(\"CAL line-comments lexical-entry link must request cits=all\")\n    return resolved, lemma_values[0]\n""",
    """    if lemma_values is None or len(lemma_values) != 1 or not lemma_values[0]:\n        raise TextParseError(\"CAL line-comments lexical-entry link lacks one lemma selector\")\n    if cits_values != [\"all\"]:\n        raise TextParseError(\"CAL line-comments lexical-entry link must request cits=all\")\n\n    raw_lemma_key = lemma_values[0]\n    try:\n        _lemma, _suffix, lemma_key = validate_lemma_key(raw_lemma_key)\n    except ValueError as exc:\n        raise TextParseError(\n            \"CAL line-comments lexical-entry link returned an invalid lemma key\"\n        ) from exc\n    if lemma_key != raw_lemma_key:\n        raise TextParseError(\n            \"CAL line-comments lexical-entry link returned a non-canonical lemma key\"\n        )\n    return resolved, lemma_key\n""",
)

# Remaining task-level documentation sync; release/index/manifest were already synchronized.
replace_once(
    "docs/tools/texts.md",
    "CAL-MCP exposes four bounded tools for discovering CAL texts, retrieving CAL's explicit text-information metadata, and reading one rendered text page at a time.",
    "CAL-MCP exposes five bounded tools for discovering CAL texts, retrieving CAL's explicit text-information metadata, reading one rendered text page at a time, and explicitly retrieving CAL line comments/translations.",
)
replace_once(
    "docs/tools/texts.md",
    "| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | `cal_text_information(file_id, subtext_id=None)` |\n| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |",
    "| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | `cal_text_information(file_id, subtext_id=None)` |\n| Retrieve CAL citations/comments/translations for one returned line coordinate | `cal_text_line_comments(coordinate)` |\n| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |",
)
section = '''## `cal_text_line_comments`

```text
cal_text_line_comments(coordinate: string)
```

Use the exact `coordinate` returned on a caller-selected `TextLine` from `cal_text_page`. CAL line coordinates are opaque ASCII-alphanumeric identifiers on this route; CAL-MCP accepts 1–64 ASCII letters/digits and does not accept a `comment_url`, arbitrary CAL path, or arbitrary query selectors.

One explicit call submits at most one new logical CAL request to the private line-comment route. A completed cache hit performs zero new upstream I/O. Returned lexicon-entry links are validated and preserved as metadata but are never followed automatically.

The result contains `status: "found" | "no_citations"`, the requested coordinate, ordered `records`, and provenance. Each found record preserves CAL's rendered reference, optional source citation text, optional translation/comment text, canonical lemma key, rendered headword, optional part of speech, optional gloss, and validated same-origin entry URL.

CAL's exact `NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED` state maps to `no_citations` with an empty record list. It does **not** map to `not_found`: current CAL returns the same state for a deliberately invalid coordinate, so this endpoint alone cannot prove whether the line exists.

Malformed response identity, contradictory empty-state/content combinations, structurally incomplete records, foreign or malformed entry links, malformed/noncanonical returned lemma keys, and unrecognized successful markup fail closed as parser drift. `cal_text_page` does not prefetch comments for any line.

'''
replace_once("docs/tools/texts.md", "## `cal_text_page`\n", section + "## `cal_text_page`\n")
replace_once(
    "docs/tools/texts.md",
    "- `comment_url`: CAL's line-comment URL when CAL renders one.\n",
    "- `comment_url`: CAL's line-comment URL when CAL renders one; use the returned line `coordinate` with `cal_text_line_comments` for an explicit MCP-native follow-up.\n",
)
replace_once(
    "docs/tools/texts.md",
    "- no automatic text-information lookup from discovery/page results;\n- no metadata-link traversal;",
    "- no automatic text-information lookup from discovery/page results;\n- no automatic line-comment lookup from page results;\n- no metadata-link traversal;",
)
replace_once(
    "docs/tools/texts.md",
    "provenance also records the requested `file_id`, `subtext_id`, `category_id`, one-based page, or original/submitted search query.",
    "provenance also records the requested `file_id`, `subtext_id`, `category_id`, one-based page, line coordinate, or original/submitted search query.",
)
replace_once(
    "docs/tools/texts.md",
    "Offline tests use deliberately reduced semantic excerpts captured/rechecked on 2026-09-04 and 2026-09-08, plus the 2026-09-09 text-information contract.",
    "Offline tests use deliberately reduced semantic excerpts captured/rechecked on 2026-09-04 and 2026-09-08, plus the 2026-09-09 text-information contract and the 2026-09-10 line-comments contract.",
)
replace_once(
    "docs/tools/texts.md",
    "- a text-information lookup preserving Ephrem source/edition/editorial/quality notes in CAL order, plus CAL's explicit `No information on record for this text.` missing state;\n",
    "- a text-information lookup preserving Ephrem source/edition/editorial/quality notes in CAL order, plus CAL's explicit `No information on record for this text.` missing state;\n- a line-comments lookup preserving ordered CAL citation/comment records, independently nullable source/translation text, validated lexicon-entry metadata, and CAL's explicit no-citations state;\n",
)

replace_once(
    "src/cal_mcp/server.py",
    '        "explicit source, edition, editorial, and other free-form Text Information metadata "\n        "for one returned file/subtext identifier. Use cal_token_analysis for every CAL lexical "',
    '        "explicit source, edition, editorial, and other free-form Text Information metadata "\n        "for one returned file/subtext identifier. Use cal_text_line_comments with one returned "\n        "TextLine.coordinate to retrieve CAL line citations/comments/translations without following "\n        "returned lexicon links. Use cal_token_analysis for every CAL lexical "',
)
