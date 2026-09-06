# Issue #41 research — current CAL lexicon citation-count drift

**Rechecked:** 2026-09-06

## Release failure

The bounded release probe recorded by issue #41 reproduced a failure in the core exact-lexicon path:

```text
cal_lexicon_lookup(query="br", lemma_key="br N")
```

The browse request succeeds, then the current `cal_entry_web.php` response raises:

```text
LexiconParseError: CAL lexicon citation count does not match the rendered citation marker
```

No public schema or request-volume change is needed; the failure occurs inside current full-entry parsing.

## Focused current-source check

Research on this branch was intentionally limited to the single existing CAL entry `br N`. Three fixed GETs were made to the same URL while diagnosing presentation/client differences; there was no neighboring-entry enumeration or traversal.

The first two raw curl probes received CAL's compact landing presentation and contained no entry/citation markup. A final probe used the production CAL-MCP User-Agent (`CAL-MCP/0.1.0.dev0 (+https://github.com/alexsosn/CAL-MCP)`) and returned the current full entry (about 152 KB). The temporary live-probe workflow was deleted before planning/implementation.

Current full-entry citation markup has semantic structure that the existing reduced fixture does not preserve:

- each rendered group has a citation-count toggle such as `2 citations` / `3 citations`;
- every citation is wrapped in `span.cit-item`;
- inter-citation punctuation is separately wrapped in `span.cit-sep`;
- linked references use `span.cit-ref-inline > a.cit-ref-link`;
- unlinked but explicitly rendered references use `span.cit-ref-inline > span.cit-ref-plain`;
- citation text contains one visible `span.cit-script[data-pref=default]` plus alternate pre-rendered script representations whose `cit-script` elements carry inline `display:none`;
- translations are rendered in `span.cit-xlat`.

The current `BT Yev 76a(40)` citation demonstrates why punctuation-only splitting is unsafe. Its citation content contains a semicolon inside the transliteration (`... nynhw; ˀbl ...`) and the rendered translation also contains an internal clause semicolon. Those semicolons belong to one citation. By contrast, CAL's separator between adjacent citations is a distinct `span.cit-sep` element.

The same entry also contains unlinked citations such as `EphCruc 2:3`, now explicitly delimited by `span.cit-ref-plain`; this is a safely separable rendered reference even though it has no CAL navigation URL.

Sources:

- https://cal.huc.edu/cal_entry_web.php?lemma=br+N
- issue #41 release probe run `33995822616`
- focused branch probe run `34024100169` (production User-Agent; structural snippets only)

## Root cause in CAL-MCP

`_SemanticHTMLParser` currently flattens the citation DOM to `_Line.text` plus actual `<a>` links. `_parse_citations()` then discovers citation boundaries by applying `_CITATION_SEPARATOR_RE` to any whitespace-adjacent semicolon.

That loses three current upstream distinctions:

1. a semantic `cit-sep` separator versus punctuation inside one citation;
2. visible default citation text versus hidden alternate script representations;
3. an unlinked but structurally explicit `cit-ref-plain` reference versus undifferentiated raw citation text.

The count check itself is valuable and should remain strict. The defect is that semantic extraction destroys the upstream citation boundaries before the count check runs.

## Compatibility / smallest faithful fix

The smallest faithful correction is at the semantic HTML extraction boundary, not by weakening citation-count validation:

1. preserve current `span.cit-sep` boundaries as an internal citation-boundary marker;
2. when those structural boundaries are present, split citations only on them, so punctuation inside `cit-text`/`cit-xlat` remains content;
3. ignore only hidden alternate `span.cit-script` variants with inline `display:none`, preserving the visible default representation and translation;
4. expose `span.cit-ref-plain` through the existing citation-reference path with `url=None` instead of inventing a URL or leaving a safely delimited reference embedded in raw text;
5. retain the existing semicolon fallback for legacy/reduced markup that has no `cit-sep` elements;
6. retain exact rendered citation-count equality and existing malformed/truncated drift failures.

This is generic to CAL's current full-entry citation component, although `br N` is the fixed regression case. It does not justify a broad lexicon crawl or a public model change.

## Test implications

A reduced fixture should contain only the current structural semantics needed to reproduce the bug:

- one normal lemma/sense;
- a `3 citations` marker;
- three `cit-item` elements separated by `cit-sep`;
- one `cit-ref-plain` citation;
- linked citations;
- a visible citation translation containing an internal semicolon;
- one hidden alternate `cit-script` containing semicolon punctuation.

The RED should exercise the public `LexiconLookupService.lookup("br", lemma_key="br N")` path with the existing reduced browse fixture plus the new entry fixture. Current production should fail on citation-count mismatch. GREEN must preserve exactly three citations, the internal semicolon, the plain reference with no URL, and no hidden alternate-script duplication.

A separate malformed-count regression must continue to raise `LexiconParseError`; no test should make count validation permissive.

## Non-goals confirmed

- no MCP error-envelope redesign;
- no new CAL request or fallback;
- no adjacent-entry probes;
- no citation guessing or URL invention;
- no global handling of arbitrary CSS visibility outside the current `cit-script` component;
- no public schema change.
