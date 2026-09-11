from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one replacement anchor, found {count}: {old!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Review-regression hardening: incomplete reference markup must fail closed and
# returned oneentry.php lemma selectors must satisfy the shared canonical lemma-key contract.
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

# Frozen public release surface: 31 -> 32 tools.
replace_once(
    "src/cal_mcp/release_surface.py",
    '        "cal_text_information",\n        "cal_token_analysis",\n',
    '        "cal_text_information",\n        "cal_text_line_comments",\n        "cal_token_analysis",\n',
)

replace_once(
    "tests/test_docs_contract.py",
    "    assert len(tool_names) == 31\n",
    "    assert len(tool_names) == 32\n",
)
replace_once(
    "tests/test_docs_contract.py",
    '    assert "31 public tools" in readme\n    assert "31-tool surface" in readme\n',
    '    assert "32 public tools" in readme\n    assert "32-tool surface" in readme\n',
)
replace_once(
    "tests/test_docs_contract.py",
    '    assert "`cal_text_information`" in readme\n    assert "`cal_kwic_full_context`" in readme\n',
    '    assert "`cal_text_information`" in readme\n    assert "`cal_text_line_comments`" in readme\n    assert "`cal_kwic_full_context`" in readme\n',
)
replace_once(
    "tests/test_docs_contract.py",
    '    assert "31 tools" in index\n',
    '    assert "32 tools" in index\n',
)
replace_once(
    "tests/test_docs_contract.py",
    '    assert "`cal_text_information`" in index\n    assert "`cal_kwic_full_context`" in index\n',
    '    assert "`cal_text_information`" in index\n    assert "`cal_text_line_comments`" in index\n    assert "`cal_kwic_full_context`" in index\n',
)

replace_once(
    "tests/test_reachability_docs_contract.py",
    '    "#108": "comments",\n',
    "",
)
replace_once(
    "tests/test_reachability_docs_contract.py",
    '_RESOLVED_ROUTE_ISSUES = ("#78", "#97", "#101", "#105", "#106", "#107", "#113", "#125")\n',
    '_RESOLVED_ROUTE_ISSUES = (\n    "#78",\n    "#97",\n    "#101",\n    "#105",\n    "#106",\n    "#107",\n    "#108",\n    "#113",\n    "#125",\n)\n',
)

# README release/user surface.
replace_once(
    "README.md",
    "The current v0.1 candidate exposes 31 public tools: one deterministic local CAL-code conversion tool plus 30 CAL-backed tools",
    "The current v0.1 candidate exposes 32 public tools: one deterministic local CAL-code conversion tool plus 31 CAL-backed tools",
)
replace_once(
    "README.md",
    "The current v0.1 contract contains a 31-tool surface: the issue-#12 audit's 26 CAL-backed tools, the release-blocking deterministic conversion tool added by issue #52, the specialized CAL indexed gloss-field search added by issue #107, the explicit CAL text-information metadata follow-up added by issue #106, the explicit Syriac GROUP follow-up added by issue #105, and the typed KWIC full-context follow-up added by issue #113.",
    "The current v0.1 contract contains a 32-tool surface: the issue-#12 audit's 26 CAL-backed tools, the release-blocking deterministic conversion tool added by issue #52, the specialized CAL indexed gloss-field search added by issue #107, the explicit CAL text-information metadata follow-up added by issue #106, the explicit Syriac GROUP follow-up added by issue #105, the typed KWIC full-context follow-up added by issue #113, and the explicit text-line comments/translations follow-up added by issue #108.",
)
replace_once(
    "README.md",
    "| Texts | `cal_text_catalogue`, `cal_text_search`, `cal_text_page`, `cal_text_information` |",
    "| Texts | `cal_text_catalogue`, `cal_text_search`, `cal_text_page`, `cal_text_information`, `cal_text_line_comments` |",
)
replace_once(
    "README.md",
    "KWIC full context is available only as a separate explicit call over typed selectors from a returned hit; parent KWIC calls do not prefetch it.",
    "KWIC full context and text-line comments/translations are available only as separate explicit calls over typed selectors returned by parent results; parent KWIC/text-page calls do not prefetch them.",
)

# Changelog/release artifact contract.
replace_once("CHANGELOG.md", "v0.1.0 freezes **31 public tools**", "v0.1.0 freezes **32 public tools**")
replace_once(
    "CHANGELOG.md",
    "- text catalogue/topic discovery, one-page retrieval, and explicit text-information metadata;",
    "- text catalogue/topic discovery, one-page retrieval, explicit text-information metadata, and explicit line comments/translations via `cal_text_line_comments`;",
)
replace_once(
    "CHANGELOG.md",
    "checks version + the frozen 31-tool schema",
    "checks version + the frozen 32-tool schema",
)
replace_once(
    "CHANGELOG.md",
    "No background crawl, mirror, cache warming, hidden pagination, link traversal, or automatic source expansion. KWIC full-context retrieval is a separate explicit caller action over typed selectors returned with a hit.",
    "No background crawl, mirror, cache warming, hidden pagination, link traversal, or automatic source expansion. KWIC full-context retrieval and text-line comments/translations are separate explicit caller actions over typed selectors returned by parent results.",
)

# Public index and reachability classification.
replace_once(
    "docs/index.md",
    "The current public contract contains 31 tools",
    "The current public contract contains 32 tools",
)
replace_once(
    "docs/index.md",
    "| Online text discovery, including dedicated Onkelos/Jonathan and Mandaic routes plus operation-aware Syriac root handoff, topic search, explicit text-information metadata, and bounded page reading | **Implemented** | [`cal_text_catalogue`, `cal_text_search`, `cal_text_information`, `cal_text_page`](tools/texts.md); root Syriac discovery returns explicit `cal_syriac_texts` follow-up metadata rather than a synthetic CAL category ID |",
    "| Online text discovery, including dedicated Onkelos/Jonathan and Mandaic routes plus operation-aware Syriac root handoff, topic search, explicit text-information metadata, bounded page reading, and explicit line comments/translations | **Implemented** | [`cal_text_catalogue`, `cal_text_search`, `cal_text_information`, `cal_text_page`, `cal_text_line_comments`](tools/texts.md); root Syriac discovery returns explicit `cal_syriac_texts` follow-up metadata rather than a synthetic CAL category ID |",
)
replace_once(
    "docs/index.md",
    '- [#108](https://github.com/alexsosn/CAL-MCP/issues/108) — text-line **comments and translations** linked from red coordinates are preserved as metadata but have no typed follow-up operation yet.\n',
    "",
)
replace_once(
    "docs/index.md",
    "does not automatically traverse result links, next pages, books, dialects, sources, text-information metadata, specialized gloss fields, Syriac groups, KWIC full-context pages, or bibliography archives.",
    "does not automatically traverse result links, next pages, books, dialects, sources, text-information metadata, line-comment pages, specialized gloss fields, Syriac groups, KWIC full-context pages, or bibliography archives.",
)
replace_once(
    "docs/index.md",
    "KWIC full context is available only when the caller explicitly passes a returned hit's typed selectors to `cal_kwic_full_context`.",
    "KWIC full context is available only when the caller explicitly passes a returned hit's typed selectors to `cal_kwic_full_context`; line comments/translations are available only when the caller passes a returned line coordinate to `cal_text_line_comments`.",
)

# Text-family tool documentation.
replace_once(
    "docs/tools/texts.md",
    "CAL-MCP exposes four bounded tools for discovering CAL texts, retrieving CAL's explicit text-information metadata, and reading one rendered text page at a time.",
    "CAL-MCP exposes five bounded tools for discovering CAL texts, retrieving CAL's explicit text-information metadata, reading one rendered text page at a time, and explicitly retrieving comments/translations for one returned line coordinate.",
)
replace_once(
    "docs/tools/texts.md",
    "| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | `cal_text_information(file_id, subtext_id=None)` |\n| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |",
    "| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | `cal_text_information(file_id, subtext_id=None)` |\n| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |\n| Retrieve CAL's comments/translations for one returned line coordinate | `cal_text_line_comments(coordinate)` |",
)
line_comments_section = '''## `cal_text_line_comments`\n\n```text\ncal_text_line_comments(coordinate: string)\n```\n\nCAL text pages can render a red coordinate link to `comment.php` for comments and/or translations associated with that line. `cal_text_page` preserves the line's machine `coordinate` and `comment_url` but does **not** follow it automatically. Pass the returned `coordinate` to this tool when that explicit follow-up is needed. Arbitrary URLs are not accepted.\n\nCurrent CAL line-comment coordinates are opaque ASCII-alphanumeric selectors; CAL-MCP accepts 1–64 ASCII letters/digits and preserves the value verbatim. One explicit call submits at most one new logical CAL request; a completed cache hit may perform zero new upstream I/O.\n\nThe result contains:\n\n- `status`: `found` or `no_citations`;\n- the requested `coordinate`;\n- ordered `records`;\n- provenance with the actual CAL source URL, retrieval timestamp, operation name, and coordinate.\n\nEach found record preserves CAL's rendered reference, optional source text, optional translation/comment, canonical CAL `lemma_key`, rendered headword, optional part of speech/gloss, and validated same-origin `entry_url`. The entry link is navigation metadata only and is never followed automatically.\n\nCAL currently uses the explicit marker `NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED` both for lines with no currently used citations and for at least one deliberately invalid coordinate. Therefore `no_citations` does **not** claim that the coordinate exists, and the tool deliberately does not expose `not_found`. Marker/record contradictions, response-coordinate mismatches, malformed/noncanonical lemma keys, changed semantic field order, or unrecognized successful markup fail closed as `TextParseError`.\n\n'''
replace_once("docs/tools/texts.md", "## `cal_text_page`\n", line_comments_section + "## `cal_text_page`\n")
replace_once(
    "docs/tools/texts.md",
    "- `comment_url`: CAL's line-comment URL when CAL renders one.\n",
    "- `comment_url`: CAL's line-comment URL when CAL renders one; use the line's `coordinate` with `cal_text_line_comments` for an explicit MCP-native follow-up.\n",
)
replace_once(
    "docs/tools/texts.md",
    "- no automatic text-information lookup from discovery/page results;\n",
    "- no automatic text-information lookup from discovery/page results;\n- no automatic line-comment/translation lookup from text-page results;\n",
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
    "- a text-information lookup preserving Ephrem source/edition/editorial/quality notes in CAL order, plus CAL's explicit `No information on record for this text.` missing state;\n- a line-comments lookup preserving two ordered CAL citation records, including independently nullable source/translation text, plus CAL's explicit `NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED` state;\n",
)
