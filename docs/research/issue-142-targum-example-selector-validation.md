# Issue #142 research — Targum example-link selector validation

Date: 2026-09-17. Base: `4e7cc1db6ce114773548d9ac631092288252c333`.

## Existing contract

CAL-MCP returns Targum concordance/reflex `example_url` values as navigation metadata after parser validation. The reduced Targum fixtures rechecked on 2026-09-05 establish these supported shapes:

- concordance: `show1dialectKWIC.php?lemma=<lemma>&pos=<suffix>&texts=<CAL text IDs>&charset=H`;
- Onqelos reflex: `getOMT.php?MT=<opaque MT id>&cal=<canonical CAL lemma key>`;
- Neofiti reflex: analogous `getNMT.php` selectors.

The concordance `texts` selector is an ASCII-space-separated list of one or more decimal CAL text IDs; the positive Onqelos fixture uses `51001 51002 51003 51004 51005`. The parser need not impose `cal_kwic_texts`' caller-side eight-ID limit here, because this ticket validates upstream metadata rather than defining a follow-up API.

## Current validation gap

`_validated_concordance_url()` currently resolves the href to the same CAL origin and endpoint family, parses `lemma`, `pos`, and `texts`, checks only that `texts` is nonblank and that `lemma + pos` equals the requested canonical key, then returns the original resolved URL. It does not:

- require the exact known selector set `{lemma, pos, texts, charset}`;
- require `charset=H`;
- require every `texts` token to be ASCII decimal;
- reject duplicate text IDs;
- reject non-ASCII whitespace or empty/ambiguous text-list structure.

`_validated_reflex_url()` validates the selected `MT` value and canonical `cal` lemma key but does not require the exact `{MT, cal}` selector set.

`_validated_same_origin_url()` checks origin and endpoint basename but currently accepts a fragment. Fragments are not sent to CAL and have no place in returned server-generated route identity, so accepting one weakens fail-closed metadata validation.

Repeated required query fields are already rejected by `_single_query_value()` because `parse_qs()` yields multiple values. Missing/empty required fields are likewise rejected. The new work should preserve that behavior while closing the remaining shape gaps.

## Boundary with #109

This ticket does not make example pages MCP-followable. #109's concordance half can later expose typed validated text IDs and compose into existing `cal_kwic_texts`; reflex examples remain a separate route family. Those are public-contract questions and stay deferred while v0.1 remains frozen/unpublished.

## Implementation direction

Keep the public dataclasses and URLs unchanged. Add narrow parser helpers that validate the known upstream selectors before returning the existing URL. Invalid upstream selectors must raise `TargumParseError` as parser drift. No request path, cache key, public tool, result field, retry behavior, or CAL request count changes.

Normal CI remains fully offline; no live CAL request is needed for this adapter-boundary hardening.