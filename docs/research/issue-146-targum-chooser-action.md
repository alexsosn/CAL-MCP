# Issue #146 research — Targum chooser form-action identity

Date: 2026-09-23. Base: `eee6e34c570acebed9af8fbbc034e63d12df40f4`.

## Live-current evidence

A one-shot bounded GitHub Actions probe, run `35853288206`, fetched exactly one page:

```text
GET https://cal.huc.edu/Omtlemmas/memMTlemma.html
```

The probe used no redirect following and reported:

```text
HTTP status: 200
Forms: [('post', '/getOmtlemma.php')]
POST actions: ['/getOmtlemma.php']
```

The temporary workflow was deleted immediately after the run. No chooser candidates or other CAL content were logged.

This matches the reduced Onqelos fixture captured/rechecked for the Targum adapter. The corresponding committed Neofiti fixture uses the analogous root action `/getNmtlemma.php`.

## Existing parser boundary

`_HebrewLemmaChooserParser` recognizes the selection form when:

- `method=post`; and
- `_is_same_origin_path(source_url, action, expected_action)` returns true.

The helper currently resolves the action and checks only:

- the same scheme/netloc as the chooser page; and
- the final path basename equals the configured action basename.

It does not require the reviewed root path, and it ignores query/fragment semantics. As a result, all of these are currently treated as equivalent to the reviewed Onqelos action:

```text
/archive/getOmtlemma.php
/getOmtlemma.php?mode=x
/getOmtlemma.php#
/getOmtlemma.php#changed
```

A bare `?` or `#` can also be normalized away by URL resolution/parsing, so post-resolution nonempty-query/fragment checks alone are not sufficient if the contract is “no query or fragment delimiter”.

## Why this is material

The chooser action is not returned to the caller and is not later submitted verbatim. `TargumService.hebrew_reflexes()` posts to the adapter's fixed configured route (`getOmtlemma.php` or `getNmtlemma.php`) with the selected opaque `R1` value.

Therefore, accepting a same-basename action in another directory or one carrying query/fragment semantics can hide an upstream workflow change: the discovery parser would claim the chooser is understood, while the explicit follow-up operation would still target a different adapter-owned route identity.

The fail-closed boundary should recognize the effective reviewed route, not merely a matching filename.

## Valid route identity

For the current contract, a target form is recognizable when its resolved URL:

- stays on the chooser page's exact scheme/netloc;
- resolves to the root path `/<expected_action>`;
- has no literal query delimiter in the original action;
- has no literal fragment delimiter in the original action.

This permits semantically equivalent same-origin absolute or network/root-relative forms that resolve to the same root route, while rejecting a changed directory or selector-bearing action. Percent-encoded `%3F` or `%23` are path/query data rather than URL delimiters and are not rejected by the delimiter check itself; they still must satisfy the exact resolved path.

## Scope and load

This is parser-only hardening. It changes no public dataclass, MCP tool/schema, service request path, cache namespace, retry behavior, or request count. Normal tests remain offline.

CAL research load: exactly one GET, already completed in run `35853288206`.
