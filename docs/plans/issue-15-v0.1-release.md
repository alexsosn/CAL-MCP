# Issue #15 plan — v0.1 standalone release and low-load live smoke

**Plan date:** 2026-09-06

This plan follows the required gate order: research → committed plan → test-only RED → minimal implementation → focused/full offline GREEN → bounded live GREEN → exact-head independent adversarial review → merge → release publication.

## Contract to preserve

- package: `cal-mcp`;
- release version: `0.1.0`;
- Python `>=3.11`;
- required transport: stdio;
- installed executable: `cal-mcp`;
- module equivalent: `python -m cal_mcp`;
- frozen 26-tool public MCP schema from #12;
- normal CI remains CAL-independent;
- CAL data is never bundled.

## Test-only RED gate

Before release implementation:

1. add release-contract tests requiring project version `0.1.0`, release notes/changelog presence, and no stale pre-release wording in installation/standalone docs;
2. add deterministic tests for the live-smoke harness using fake MCP result objects:
   - successful structured/provenance-bearing result passes;
   - `is_error=True` is a smoke failure;
   - missing structured output/provenance is a smoke failure;
   - upstream/network classification remains distinct from parser/tool failure classification;
   - request budget rejects request 10 before it is issued;
3. add a package-build/clean-install workflow or test path that builds sdist+wheel, installs the wheel into a fresh environment, checks metadata version, and launches the installed stdio entry point;
4. establish RED with static gates green and failures caused only by the absent release/smoke implementation.

## Minimal implementation

- change project version from `0.1.0.dev0` to `0.1.0`;
- add `CHANGELOG.md` with a `0.1.0` release section listing the frozen capability families and known limitations;
- update installation and standalone docs with the released version/artifact/entry-point contract;
- add one small `cal_mcp.live_smoke` module that owns:
  - the fixed eight public-tool smoke cases from research;
  - the nine-request hard ceiling;
  - deterministic result validation/classification helpers;
  - sequential execution through one shared MCP server/client context;
- keep the live workflow separate from `.github/workflows/ci.yml`;
- live workflow configures one shared `CalHttpClient` with concurrency 1, retries 0, cache disabled, executes only the fixed cases, and fails on any MCP `is_error` result;
- add a release/build workflow path that produces sdist+wheel and proves clean wheel installation/stdio startup before publication.

No public MCP tool or parameter changes belong in #15.

## Offline GREEN gate

Run the existing deterministic suite plus new release/smoke tests:

```text
ruff check .
ruff format --check .
mypy
pytest
```

The offline gate must not contact CAL.

The package check must build both artifacts and test the built wheel from a fresh environment rather than relying only on editable installation.

## Live GREEN gate

Run the permanent live smoke once on the release candidate with:

- exactly the researched eight public tool calls;
- hard maximum nine CAL requests;
- concurrency 1;
- retries 0;
- cache disabled;
- no loop driven by CAL-returned content;
- request count printed even on failure.

If any case returns `is_error`, lacks the expected typed/structured/provenance semantics, or the request budget is exceeded, stop release work and open/fix a focused blocker through research → plan → TDD → independent review.

## Documentation/release notes gate

Before final review:

- `docs/installation.md` documents the exact released version and standalone installation artifact/path actually published;
- `docs/integrations/standalone-mcp.md` records `cal-mcp` + no arguments + stdio as the stable downstream launch contract;
- `CHANGELOG.md` lists v0.1 capability families and known limitations, including live CAL dependency and no bundled corpus/data;
- root/project docs must not claim PyPI availability unless it has actually been published;
- issue #16 must be able to pin the exact version/entry point without importing CAL code into Agora.

## Independent adversarial review gate

Review the exact final PR head independently from implementation history and try to falsify:

- clean-install evidence actually uses the built wheel rather than the checkout;
- the installed console script is the one launched;
- package metadata/version/docs agree exactly;
- normal CI remains CAL-independent;
- live smoke cannot exceed nine upstream requests, including lexicon's two-request path;
- retries/cache/concurrency cannot silently inflate the live budget;
- MCP `is_error` cannot be mistaken for success;
- successful smoke results require provenance rather than accepting empty payloads;
- smoke does not enumerate discovered rows/results;
- failure classification does not turn parser drift into a normal empty result;
- no CAL HTML/data fixture/page is bundled into release artifacts beyond existing minimal test fixtures;
- no Agora or hosted-service behavior has leaked into this ticket;
- release/tag publication has not happened before merge.

Any blocker gets a test-first review regression where applicable, then fresh full GREEN and a new exact-head independent review.

## Publication gate

Only after the PR merges and merged `main` is verified:

1. build sdist + wheel from the exact merge commit;
2. create GitHub tag/release `v0.1.0` from that exact commit;
3. attach the reviewed artifacts;
4. record checksums/version/entry point in the release notes if supported by the publication workflow;
5. close #15 only after the published artifact can be consumed by downstream issue #16.

Do not claim PyPI publication without an authenticated reviewed PyPI path.
