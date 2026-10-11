# Issue #301 — research → plan → RED → GREEN

See [source audit](../research/issue-301-cal-path-canonicalization.md).

1. **RED** using an injected non-network transport: show `CalHttpClient.fetch` currently dispatches ambiguous paths (`foo/..`, `foo/./entry.php`, `./entry.php`, `foo//entry.php`, `foo/%2e%2e/entry.php`, `foo/%2Fentry.php`, backslash, raw C0) rather than rejecting at validation. Test zero transport attempts, zero smoke-budget hook invocations and no cache pollution for rejected paths; ordinary `/entry.php`, `cgi-bin/getlex.php`, encoded selector **values** in params remain legal. Use real HTTPX MockTransport with zero network to verify that accepted URL dispatch remains on CAL and original named path.
2. **GREEN**: a small validator on the raw path *before* urlsplit drops controls, reject backslashes / controls / percent encoded path tokens; after lstrip leading separators, require nonempty path with no interior empty or dot/dotdot path segments. Do not permit literal URL query or fragment (existing behavior). Use a stable `CalRequestValidationError`, no downstream transport or processing.
3. Preserve existing direct client defaults and 8-per-60 real request ceiling; no live CAL traffic. Update request safety docs (one concise paragraph) and/or decision entry if policy interpretation changes.
4. Complete both frozen/latest-compatible CI, then a **logically independent skeptical review** of real diff with bypass vectors, legitimate endpoint use, Unicode/encoded selectors, URL provenance; repair and re-run exact-head CI before squash merge.

No release tag, no PyPI; #262 and #15 remain blocked.
