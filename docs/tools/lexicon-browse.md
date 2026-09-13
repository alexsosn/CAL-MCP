# Lexicon prefix browsing

`cal_lexicon_browse` exposes CAL's lexicon browser as a bounded discovery operation separate from `cal_lexicon_lookup`.

```text
cal_lexicon_browse(prefix, representation=None, continuation=None)
```

Use it when you want neighboring CAL lexicon headwords by prefix rather than an exact/root/full-form lookup. A one-character prefix follows CAL's JUMP TO workflow; two- and three-character prefixes use CAL's prefix browser. The same deterministic supported input-normalization layer is reused, but ambiguous input is rejected rather than expanded into multiple browse requests.

Each call represents at most one CAL browse page. The tool never fetches entry pages, never follows NEXT PAGE automatically, and never crawls the lexicon. If the current CAL page exposes a canonical continuation, the result contains `next_continuation`; pass that exact returned value in a later explicit call together with the same prefix.

A normal result contains the original and normalized prefix, input representation, ordered CAL lemma references from the current page, nullable `next_continuation`, and CAL provenance. Lemma references preserve CAL lemma keys, headword variants, pronunciation, part of speech, gloss, and aliases where CAL exposes them. Use `cal_lexicon_lookup` with a selected lemma/headword when you need the structured entry itself.

Input is validated locally before CAL I/O. Browse prefixes must normalize to one through three CAL browse consonants (or the documented bound-form separator where supported by the researched browser contract). Unsupported scripts, marks, punctuation, finite orthographic ambiguity, malformed continuation values, or prefixes outside the bounded browse contract fail before a request is sent.

Returned NEXT PAGE links are treated as untrusted upstream navigation. CAL-MCP accepts only the canonical CAL browse route with the expected single continuation selector and rejects cross-origin, wrong-route, duplicate-selector, fragment, or extra-control navigation as parser drift. A continuation is opaque adapter input: callers should not synthesize it from URLs or lexicographic guesses.

The parser also fails closed when CAL's browse structure contradicts itself—for example, when a no-results page exposes a continuation or navigation no longer matches the researched route contract. CAL endpoint/form details remain private implementation details rather than MCP arguments.

`cal_lexicon_browse` is intended for explicit lexicographic exploration. It does not perform fuzzy search, semantic ranking, bulk extraction, hidden pagination, automatic homograph selection, entry expansion, or construction of a local lexicon index.
