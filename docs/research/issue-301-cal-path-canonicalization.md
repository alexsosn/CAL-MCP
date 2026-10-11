# Issue #301 — source audit of CAL request-path canonicalization

Date: 2026-10-11. Offline inspection of main `00a988b`, Python `urllib.parse` path resolution, existing `tests/test_http_client.py` and `tests/test_http_policy_review_regressions.py`; **no CAL HTTP requests**.

## Concrete discrepancy

`CalHttpClient.fetch` calls `_validate_and_normalize_request` before cache, single-flight and transport. It accepts GET/POST, a relative path with no parsed scheme/authority/query/fragment, and explicitly rejects only the literal `..` path, `../` prefix or internal `/../`. The real `_Httpx2Transport` builds a URL via `urljoin("https://cal.huc.edu/", request.path.lstrip("/"))`.

Python 3's `urljoin` **normalizes dot and empty interior segments**. The following paths pass the current validator but are not sent as the same apparent path:

| Caller path | Resolved path at CAL origin |
| --- | --- |
| `foo/..` | `/` |
| `foo/./entry.php` | `/foo/entry.php` |
| `./entry.php` | `/entry.php` |
| `foo//entry.php` | `/foo/entry.php` |

These are ambiguities, **not a demonstrated off-origin SSRF**. The current origin check already blocks literal `https://other/` and `//other/`. Percent-escaped components such as `%2e%2e`, `%2F` and `%5C` may be interpreted differently by downstream servers/proxies; canonicalization cannot safely infer server-side decoding from `urljoin`. Backslashes and raw control bytes can also be parsed or stripped differently by intermediaries. Avoid authorizing ambiguous endpoints before any CAL I/O.

## Boundaries / compatibility

CAL public service adapters use named relative script endpoints and move dynamic ids, transliteration and selector values through `CalRequest.params`/`data` rather than by percent-encoded path components. Keep bare `entry.php`, leading-single-slash `/entry.php`, and multi-component `cgi-bin/getlex.php` valid; there is no reason to stop slash-separated legitimate paths. Do not change URL encoding of repeated params/form fields or networking, retries, pacing, cache, and MCP public schemas.

No claim about upstream CAL quota; #262's full 37-token zero429 acceptance and #15 publishing gate remain unmet.

## Skeptical follow-up: leading spaces

The initial fix covered C0 controls, but an independently checked standard-library example demonstrated that `urlsplit(" entry.php").path == "entry.php"`, and `urljoin("https://cal.huc.edu/", " entry.php")` targets `/entry.php`. Plain ASCII space is not a C0 control. Four supplemental offline RED tests reproduced acceptance of leading / embedded ASCII whitespace and a nonbreaking space (CI run 38131127861: 4 failed, 2,233 passed). The raw-path guard now rejects whitespace via `str.isspace()` before URL parsing; spaces in typed query/form values remain supported. Triple-leading slashes and interior empty segments were also regression-tested.
