from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "src/cal_mcp/texts.py",
    "from cal_mcp.lexicon import _Line, _Link, _parse_lines\n",
    "from cal_mcp.lemma_key import validate_lemma_key\n"
    "from cal_mcp.lexicon import _Line, _Link, _parse_lines\n",
)
replace_once(
    "src/cal_mcp/texts.py",
    '''    if cits_values != ["all"]:\n        raise TextParseError("CAL line-comments lexical-entry link must request cits=all")\n    return resolved, lemma_values[0]\n''',
    '''    if cits_values != ["all"]:\n        raise TextParseError("CAL line-comments lexical-entry link must request cits=all")\n\n    raw_lemma_key = lemma_values[0]\n    try:\n        _lemma, _suffix, lemma_key = validate_lemma_key(raw_lemma_key)\n    except ValueError as exc:\n        raise TextParseError(\n            "CAL line-comments lexical-entry link returned an invalid lemma key"\n        ) from exc\n    if lemma_key != raw_lemma_key:\n        raise TextParseError(\n            "CAL line-comments lexical-entry link returned a non-canonical lemma key"\n        )\n    return resolved, lemma_key\n''',
)
replace_once(
    "tests/test_kwic_full_context.py",
    "    assert len(V01_PUBLIC_TOOLS) == 31\n",
    "    assert len(V01_PUBLIC_TOOLS) == 32\n",
)
replace_once(
    "tests/test_release_artifact_verifier.py",
    "    assert len(V01_PUBLIC_TOOLS) == 31\n",
    "    assert len(V01_PUBLIC_TOOLS) == 32\n",
)

path = Path("docs/tools/texts.md")
text = path.read_text(encoding="utf-8")
replacements = [
    (
        "CAL-MCP exposes four bounded tools for discovering CAL texts, retrieving CAL's explicit text-information metadata, and reading one rendered text page at a time.",
        "CAL-MCP exposes five bounded tools for discovering CAL texts, retrieving CAL's explicit text-information metadata, reading one rendered text page at a time, and explicitly retrieving CAL line comments/translations.",
    ),
    (
        "| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | `cal_text_information(file_id, subtext_id=None)` |\n| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |",
        "| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | `cal_text_information(file_id, subtext_id=None)` |\n| Retrieve CAL citations/comments/translations for one returned line coordinate | `cal_text_line_comments(coordinate)` |\n| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |",
    ),
    (
        "- `comment_url`: CAL's line-comment URL when CAL renders one.\n",
        "- `comment_url`: CAL's line-comment URL when CAL renders one; use the returned line `coordinate` with `cal_text_line_comments` for an explicit MCP-native follow-up.\n",
    ),
    (
        "- no automatic text-information lookup from discovery/page results;\n- no metadata-link traversal;",
        "- no automatic text-information lookup from discovery/page results;\n- no automatic line-comment/translation lookup from page results;\n- no metadata-link traversal;",
    ),
    (
        "provenance also records the requested `file_id`, `subtext_id`, `category_id`, one-based page, or original/submitted search query.",
        "provenance also records the requested `file_id`, `subtext_id`, `category_id`, one-based page, line coordinate, or original/submitted search query.",
    ),
    (
        "Offline tests use deliberately reduced semantic excerpts captured/rechecked on 2026-09-04 and 2026-09-08, plus the 2026-09-09 text-information contract.",
        "Offline tests use deliberately reduced semantic excerpts captured/rechecked on 2026-09-04 and 2026-09-08, plus the 2026-09-09 text-information contract and the 2026-09-10 line-comments contract.",
    ),
    (
        "- a text-information lookup preserving Ephrem source/edition/editorial/quality notes in CAL order, plus CAL's explicit `No information on record for this text.` missing state;",
        "- a text-information lookup preserving Ephrem source/edition/editorial/quality notes in CAL order, plus CAL's explicit `No information on record for this text.` missing state;\n- a line-comments lookup preserving ordered CAL citation/comment records, independently nullable source/translation text, validated lexicon-entry metadata, and CAL's explicit no-citations state;",
    ),
]
for old, new in replacements:
    if text.count(old) != 1:
        raise SystemExit(f"docs/tools/texts.md: expected one anchor, found {text.count(old)}")
    text = text.replace(old, new, 1)

heading = "## `cal_text_page`\n"
if text.count(heading) != 1:
    raise SystemExit("docs/tools/texts.md: page heading anchor changed")
section = '''## `cal_text_line_comments`

```text
cal_text_line_comments(coordinate: string)
```

Use the exact `coordinate` returned on a caller-selected `TextLine` from `cal_text_page`. CAL line coordinates are opaque ASCII-alphanumeric identifiers on this route; CAL-MCP accepts 1–64 ASCII letters/digits and does not accept a `comment_url`, arbitrary CAL path, or arbitrary query selectors.

One explicit call submits at most one new logical CAL request to the private line-comment route. A completed cache hit performs zero new upstream I/O. Returned lexicon-entry links are validated and preserved as metadata but are never followed automatically.

The result contains `status: "found" | "no_citations"`, the requested coordinate, ordered `records`, and provenance. Each found record preserves CAL's rendered reference, optional source citation text, optional translation/comment text, canonical CAL `lemma_key`, rendered headword, optional part of speech, optional gloss, and validated same-origin `entry_url`.

CAL's exact `NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED` state maps to `no_citations` with an empty record list. It does **not** map to `not_found`: current CAL returns the same state for a deliberately invalid coordinate, so this endpoint alone cannot prove whether the line exists.

Malformed response identity, contradictory empty-state/content combinations, structurally incomplete records, foreign or malformed entry links, malformed or non-canonical returned lemma keys, and unrecognized successful markup fail closed as `TextParseError`. `cal_text_page` does not prefetch comments for any line.

'''
text = text.replace(heading, section + heading, 1)
path.write_text(text, encoding="utf-8")
