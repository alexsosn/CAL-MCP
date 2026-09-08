# Issue #79 plan — restore Tel Dan text-page parsing across current CAL token-link families

Date: 2026-09-08
Research: `docs/research/issue-79-tel-dan-text-page.md` and R-024 in `research.md`.

## Scope

Repair the existing `cal_text_page` parser so current Tel Dan (`file_id="13250"`) is returned as a normal bounded text page when CAL exposes token links through `getlex.php`. Preserve compatibility with current/legacy text pages that expose `bablex.php` links.

This ticket does not change the public MCP schema, page-number mapping, token-analysis operation, generic MCP error envelope, catalogue/search discovery, or special Mandaic subtext routing.

## TDD RED gate

Before production changes:

1. add a deliberately reduced fixture derived from the 2026-09-08 Tel Dan response with:
   - file-info link for `13250`;
   - no pagination marker;
   - two representative line rows;
   - `getlex.php` token links with decimal `coord`/`word` and `hasvariant=0`;
   - one comment link;
2. add a service-level regression for `TextService.page("13250", page=1)` proving:
   - exactly one GET to `get_a_chapter.php` with `file=13250&page=0`;
   - `status="found"`;
   - unpaginated page metadata remains null;
   - current CAL coordinates/word indexes and exact `getlex.php` lexical URLs are preserved;
3. add parser edge regressions showing malformed `getlex.php` `coord`/`word` values fail closed;
4. retain the existing `bablex.php` BT AZ tests unchanged.

A valid RED requires both deterministic/latest-compatible dependency setup, Ruff lint, Ruff format, and strict mypy to pass while pytest fails only because `getlex.php` links are not yet recognized as text tokens.

## Minimal GREEN implementation

Change only token-link recognition in `src/cal_mcp/texts.py`:

- recognize a token link when its path ends in `bablex.php` **or** `getlex.php`;
- parse/validate the existing `coord` and `word` fields identically for both families;
- preserve the full exact CAL link via `urljoin` as `TextToken.lexical_url`, including extra upstream query fields such as `hasvariant=0`;
- do not treat other endpoints as token links.

Prefer a small named endpoint predicate/set rather than duplicating parser logic.

No fallback that manufactures tokens from plain rendered text is allowed.

## Documentation

Update `docs/tools/texts.md` only where it currently implies a single token-link implementation detail. User-facing semantics remain: `cal_text_page` returns CAL token coordinates/indexes and a lexical navigation URL; the endpoint name remains private. Record the Tel Dan fixture recheck date if useful, but do not expose `hasvariant` as a public parameter.

## GREEN gate

Require full repository CI in both matrices:

- frozen deterministic dependencies + verification;
- latest-compatible dependency resolution + `pip check`;
- `ruff check .`;
- `ruff format --check .`;
- strict `mypy`;
- full `pytest`.

Normal CI performs zero CAL requests.

## Independent adversarial review

Review the exact final SHA skeptically against current CAL and repository invariants. Challenge at least:

- whether `getlex.php` recognition is limited to the token-link position rather than globally trusting that endpoint;
- malformed/repeated/missing `coord`/`word` semantics for both endpoint families;
- preservation of exact CAL URL/query metadata without exposing private params publicly;
- same-row coordinate consistency and comment-coordinate validation;
- existing `bablex.php` compatibility;
- one-request public operation bound;
- no weakening to accept line-only/unlinked text as tokenized output;
- no scope creep into #81/#84/#85.

If review finds a blocker, enter review-regression RED → minimal fix → full GREEN → fresh exact-head review before merge.

## Merge gate

Merge only after research and plan precede tests/implementation, valid test-only RED is recorded, full GREEN is authoritative on an exact helper-free head, the independent exact-SHA review is clean, no unresolved review threads remain, and guarded merge pins that SHA.

## CAL load

No further live CAL access is planned. Research used four fixed Tel Dan GETs total; implementation, tests, and review should use reduced offline fixtures and current recorded evidence.