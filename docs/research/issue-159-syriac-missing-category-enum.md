# Issue #159 research — discoverable Syriac missing-word category choices

Date: 2026-10-10. **Offline only:** code, checked-in Syriac fixture, existing
API/schema regression tests, and public tool conventions. No CAL requests.

## Problem and exact evidence

`cal_syriac_missing_words(category)` in `src/cal_mcp/server.py` currently
annotates `category: str`. Its advertised MCP `inputSchema` therefore lacks
an `enum`, although `SyriacService.missing_words()` dispatches exclusively
through `_MISSING_WORD_PATHS` in `src/cal_mcp/syriac.py`. Its 9 fixed slugs
(in dictionary declaration order) are:

`adjectives`, `adverbs`, `miscellaneous`, `nomina-agentis`,
`abstracts`, `verbal-nouns`, `verbs`, `masculine-nouns`,
`feminine-nouns`.

No other string is a valid selector; the outgoing request remains one GET
to that selector's fixed endpoint, and no upstream dynamic category enumeration
is necessary. The successful `verbs` path is already fixture-backed by
`tests/fixtures/cal/syriac_missing_verbs.html` and `tests/test_syriac.py`.

Existing `GlossField(StrEnum)` and `DictionarySource(StrEnum)` are
precedent for generating discoverable MCP enums with Python type annotations.
The SDK supports resolving `$defs`/`$ref` in `inputSchema`. A `StrEnum`
also remains string-comparable at the internal dispatch boundary, so public
results and HTTP routing need not change.

**Additional SDK boundary uncovered:** `CalMCPServer.call_tool` traps
SDK Pydantic `ValidationError` and calls `_sdk_validation_message`, which
intentionally reduces errors to **field names only**. Merely adding a typed
enum would expose the choices to well-behaved clients but still return
`Invalid tool arguments: category` to an invalid call. Issue #159 asks
that the invalid-input message *also* list the allowed slugs. This requires
a narrowly scoped, length-bounded supplement to the public SDK error message
for this tool only, plus the existing service-level invalid-input message.

## Decision

Create one `SyriacMissingWordCategory(StrEnum)` with nine members and
use it to annotate the MCP tool's `category` input. Keep existing
`_MISSING_WORD_PATHS` as the route mapping, keyed by those enum members
with an exhaustiveness regression test. Expose a small helper returning
these authoritative enum values in stable declared order. Service methods
continue accepting ordinary strings to avoid changes to their Python API.

Expose the fixed choices for malformed direct service calls and for the
public `cal_syriac_missing_words` validation branch. Preserve the
generic 500-character, no-echo error sanitization behavior for all other
operations.

No public MCP tools, return schemas, CAL requests, private endpoints,
category values, or corpus content are added. This is a backward-compatible
validation/documentation correction **before the first v0.1.0 release**,
which #15 still blocks on PyPI Trusted Publisher verification.

## TDD and review

RED against live in-process MCP `list_tools`, rejecting an unknown
category, verifying the 9 values and no transport; RED service invalid
category checks; GREEN enum/dispatch/error/docs; both CI configurations;
fresh logically independent review on exact head before merge.
