# Issue #39 execution plan — CAL recent bibliography snapshot

**Plan committed after research, before test/implementation.** Ticket: [#39](https://github.com/alexsosn/CAL-MCP/issues/39). Standalone v0.1.0 publication is complete; this is a post-v0.1 change, not a retroactive modification of the immutable v0.1.0 tag.

## Public surface

`cal_bibliography_recent()` has **no input arguments** and returns:

- `heading`: exact recognized `CAL Recent Bibliography`;
- `records`: the CAL-ordered array of existing `BibliographyRecord` objects, retaining citation strings and link metadata, including duplicates;
- `provenance`: source, actual source URL/retrieved time, operation `bibliography_recent` and empty original/submitted query strings for this no-query operation.

The five-year label comes from CAL's index, but no `year`, `start_year`, `end_year`, page offset, derived year group, fuzzy search, polling or archive traversal is added. One explicit call causes exactly one logical `GET getrecentbib.php` with no params; completed cache hits cause zero new CAL starts. The established shared 2 MiB response cap is the only size bound and fails closed.

## RED (before production changes)

Add reduced semantic parser + service + MCP schema tests for:
1. Heading and multiple `<p>` records inside CAL cards; Unicode, citations, link kinds/values, source order, and duplicate preservation.
2. Year tokens inside citation content remain opaque; no invented year grouping and no inference from publication/date snippets.
3. Wrong/duplicate heading, empty page without an observed explicit empty marker, malformed/unbalanced record, cross-origin/malformed link, legacy document without boundaries, and an unexpected pagination/form control all fail as bibliography parser drift.
4. One request to fixed GET path with empty params, no navigation, and exact provenance/source date. Test zero-input MCP registration; reject supplied query/year/page parameters.
5. Shared client response-size and upstream HTTP/error semantics remain unchanged (reuse existing client tests; targeted regression if needed).

Confirm failing tests against current branch by CI/test output before editing production. Tests use small structural snippets, not the full 63.5 KB CAL page.

## GREEN / documentation

- Reuse the existing bibliography HTML record parser with source-specific heading validation, and strengthen it narrowly to detect pagination controls rather than silently return partial lists.
- Add dedicated typed result/service method and `cal_bibliography_recent` to server instructions and tool registration. Do not change existing author/keyword/lemma behavior or `V01_PUBLIC_TOOLS` frozen contract.
- Update user bibliography reference and docs index/capability matrix, add a post-v0.1 changelog entry, and mark #39 as implemented only after review/merge; retain tagged v0.1 release snapshots unchanged.
- Run deterministic and latest-compatible CI offline; inspect source and PR diff independently, including existing-query regressions, parser drift, result size, provenance, empty semantics, pagination and request count. Review the exact final SHA after fixes.

## Release acceptance

After offline green, a separate bounded user-facing installed-wheel smoke (one explicit recent-bibliography call, no other CAL surface) should verify the current HTML. A release smoke must respect the shared client backpressure and stop on HTTP 429; no background schedule. Any live mismatch blocks issue closure and should produce a new failing reduced fixture. The existing v0.1.0 release is unaffected.

## Non-goals

No CAL HTML archival fixture, year regex, bibliographic correction, duplicate elimination, cross-link recursion, archive enumeration, local index, extra transport, or new integration dependency.
