# Issue #144 research — bare-fragment Targum navigation URLs

Date: 2026-09-23. Base: `8b61613c4d04fd29afbd5c50854a74125b05a811`.

## Trigger

The exact-head adversarial review for #143 noted one nonblocking URL-identity edge case: `_validated_same_origin_url()` rejects nonempty fragments using `urlsplit(resolved).fragment`, but a bare trailing fragment delimiter is not represented as a nonempty fragment.

## Python URL behavior

For an otherwise-valid link such as:

```text
getOMT.php?MT=1751&cal=tyq%232+N#
```

`urlsplit(...).fragment` is the empty string. More importantly, `urljoin(source_url, href)` normalizes the bare trailing `#` away entirely. Therefore checking only the resolved URL cannot distinguish a bare fragment delimiter from no fragment delimiter.

The original HTML `href` still contains the literal `#`, so the narrow fail-closed check must occur before `urljoin()`.

A percent-encoded number sign remains different:

```text
getOMT.php?MT=1751&cal=tyq%232+N
```

contains `%23`, not a literal `#`. That encoding is already required by the fixture-backed canonical reflex lemma key `tyq#2 N` and must continue to pass.

## Contract boundary

Targum chapter, concordance-example, and reflex-example URLs are parser-validated navigation metadata. #143 already established that fragments are outside the accepted server-generated route identity. Accepting an empty fragment delimiter is therefore inconsistent with that contract even though browsers do not transmit fragments to CAL.

This hardening changes no public dataclass, serialized field, MCP schema, request path, cache key, retry behavior, or request count. Valid links are returned byte-for-byte as before.

## Live CAL decision

No live CAL probe is needed. The behavior under test is a synthetic malformed-URL boundary in Python URL parsing, not a claim about current CAL content. Existing reduced fixtures remain the authority for valid route/query shapes.

## Implementation direction

Reject any literal `#` in the original `href` at the shared Targum same-origin URL validator before resolution. Keep the existing parsed-fragment check as defense in depth for future refactors or alternate callers. Add focused parser regressions for bare-fragment concordance and reflex links plus an explicit valid `%23` reflex control.
