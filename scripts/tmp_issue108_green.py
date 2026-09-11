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
replace_once(
    "docs/tools/texts.md",
    "optional translation/comment text, the opaque returned lemma key, rendered headword",
    "optional translation/comment text, canonical CAL `lemma_key`, rendered headword",
)
replace_once(
    "docs/tools/texts.md",
    "foreign or malformed entry links, repeated/empty lemma selectors, and unrecognized successful markup fail closed as parser drift.",
    "foreign or malformed entry links, repeated/empty lemma selectors, malformed or non-canonical returned lemma keys, and unrecognized successful markup fail closed as parser drift.",
)
replace_once(
    "docs/tools/texts.md",
    "Offline tests use deliberately reduced semantic excerpts captured/rechecked on 2026-09-04 and 2026-09-08, plus the 2026-09-09 text-information contract.",
    "Offline tests use deliberately reduced semantic excerpts captured/rechecked on 2026-09-04 and 2026-09-08, plus the 2026-09-09 text-information contract and the 2026-09-10 line-comments contract.",
)
