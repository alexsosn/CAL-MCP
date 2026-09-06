# Issue #15 plan — publish v0.1 standalone release and add low-load drift smoke

**Plan date:** 2026-09-06

This ticket follows research → plan → test-only RED → minimal implementation → offline GREEN → capped live smoke → exact-head adversarial review → review-regression RED/GREEN if needed → fresh review → merge → immutable release publication/verification.

Issue #15 is **not complete merely when its implementation PR merges**. It closes only after the released artifact exists and its clean install/version/entry point have been verified. If PyPI Trusted Publisher setup is absent, the in-repository work may become merge-ready while the issue remains blocked on that explicit external prerequisite.

## Frozen release contract

The release is CAL-MCP **v0.1.0** and preserves the already frozen 26-tool public MCP surface from issue #12. This ticket does not add a new CAL research operation and does not redesign public error/result schemas.

The release contract is:

- package name: `cal-mcp`;
- version: `0.1.0`;
- Python: `>=3.11`;
- primary v0.1 transport: stdio;
- installed command: `cal-mcp`;
- equivalent module entry point: `python -m cal_mcp`;
- software license: MIT;
- CAL data remains remote/live and is not bundled;
- ordinary CI remains fully offline from CAL.

## Gate 1 — test-only RED

Before release implementation, add deterministic tests for the missing release machinery.

### Release metadata / artifact contract

Add `tests/test_release_contract.py` (or equivalent) that initially fails because the repository is still pre-release. It should assert:

1. `pyproject.toml` declares exactly `0.1.0` rather than `.dev0`;
2. a versioned `CHANGELOG.md` or release-notes file contains `0.1.0` and the frozen supported surface/known limitations;
3. a permanent live-smoke module/workflow exists and has the researched hard request cap;
4. a dedicated release workflow exists with least-privilege Trusted Publishing structure;
5. release workflow/tag version consistency is machine-checked rather than trusted manually.

Do not require a live PyPI upload in normal tests.

### Live-smoke logic contract

Add offline tests around a testable smoke runner before any new live workflow is enabled. Inject fake operations/client behavior and prove:

- the request budget cannot exceed 9;
- concurrency/retry/cache settings are fixed to 1/0/disabled for live smoke;
- a domain parser exception is classified as `drift`;
- `CalNetworkError` / `CalUpstreamError` are classified as upstream/network failure rather than drift;
- other content/policy errors are distinguishable;
- an unexpected local/harness error fails the run;
- every required representative case must succeed; failures are not logged and ignored;
- if an MCP-result helper is retained anywhere, `result.is_error` is failure.

The RED is valid only when install, Ruff lint, Ruff format, and strict mypy pass and pytest fails only for the intended missing release contract.

## Gate 2 — offline release implementation

### Package metadata

Change package version to `0.1.0`. Do not narrow runtime dependency ranges merely to make a release lock; issue #18 owns reproducible-vs-latest dependency policy.

Add build tooling only where needed for developer/release validation. `python -m build` should produce both wheel and sdist from the same source revision.

### Clean artifact validation

Add a deterministic release-artifact validation path that:

1. builds wheel + sdist;
2. creates a fresh temporary virtual environment;
3. installs the **built wheel**, not the source tree/editable package;
4. launches the installed `cal-mcp` command over stdio;
5. checks server name `cal-mcp`, version `0.1.0`, and exactly the frozen 26 tool names;
6. performs no CAL-backed tool call and therefore no CAL network request.

This can be a small reusable script under `tests/release/` or `scripts/` plus a CI step/workflow. It must not depend on the development checkout being importable inside the fresh environment.

### Release notes

Add `CHANGELOG.md` with v0.1.0 notes covering:

- released capability groups;
- conservative request bounds/live-data dependency;
- parser-drift behavior;
- no CAL data bundling;
- stdio-only transport for v0.1;
- known limitations/deferred #39 recent-bibliography snapshot;
- optional Agora integration still belongs to #16 after publication.

## Gate 3 — permanent capped live smoke

Implement a testable runner (for example `src/cal_mcp/live_smoke.py`) that uses one shared `CalHttpClient` configured with:

- `max_concurrency=1`;
- `max_retries=0`;
- `cache_enabled=False`;
- hard total request budget = **9**.

Use the previously researched eight cases unchanged unless a regression test proves a reason to change them:

1. lexicon `br` / `br N` (2 requests);
2. text search `Tel Dan`;
3. text concordance `13250`;
4. bibliography lemma `cly V`;
5. Jastrow page `705` dictionary collation;
6. external-citation dialect discovery;
7. Targum Gen 1:1;
8. Syriac Peshitta Gen 1:1.

For each case require normal success/provenance semantics. Do not follow any returned link.

Use service-layer operations for diagnostic classification, preserving typed parser/request exceptions. Separately, the built-wheel stdio test proves the actual MCP process boundary.

Add `.github/workflows/live-smoke.yml` with:

- `workflow_dispatch`;
- a conservative weekly schedule;
- Python 3.11;
- installation of the package/source revision under test;
- a single execution of the hard-capped runner;
- read-only repository permission;
- no matrix, retries, pagination, or parallel CAL operations.

Normal `ci.yml` must never invoke this workflow or CAL.

Before final review, run the permanent live smoke once on the release candidate. That one run replaces any further temporary live probes.

## Gate 4 — release workflow

Add `.github/workflows/release.yml` isolated from normal CI.

Preferred immutable trigger: a version tag matching `v*` (specifically `v0.1.0` for this release). Optionally allow manual dispatch only if it cannot bypass tag/version checks.

Workflow structure:

1. **build/test job** — no OIDC publish permission:
   - checkout exact tag;
   - setup Python 3.11;
   - verify tag `vX.Y.Z` equals `project.version`;
   - build wheel + sdist;
   - run artifact metadata/clean-install/stdio validation;
   - run ordinary deterministic test gates if they are not already guaranteed by the tagged commit;
   - upload distributions as an Actions artifact.
2. **live-smoke job** — no publishing credential:
   - run the same capped 9-request smoke exactly once against the tagged release candidate;
   - fail publication on drift/upstream failure rather than publishing an unverified adapter.
3. **PyPI publish job**:
   - depends on build + live smoke;
   - use GitHub environment `pypi`;
   - grant **job-level** `id-token: write` and only necessary read permission;
   - download the already built distributions;
   - publish with `pypa/gh-action-pypi-publish@release/v1`;
   - never use a stored long-lived PyPI token in repository code.
4. **GitHub release job**:
   - use the same distributions, not a rebuild;
   - create the versioned GitHub release and attach wheel/sdist only after the release gates succeed;
   - release notes should derive from the committed v0.1 changelog/release note.

The account-side PyPI Trusted Publisher must match repository owner `alexsosn`, repository `CAL-MCP`, workflow `release.yml`, and environment `pypi` if that environment is used.

## Gate 5 — user documentation

Before publication, update docs to describe the **release process/prerequisite** without falsely claiming publication.

After actual successful publication, release truth must state:

- stable version `0.1.0`;
- package-index install command for the successfully published artifact;
- `cal-mcp` and `python -m cal_mcp` stdio entry points;
- clean-install validation status;
- live-smoke schedule/budget and what it diagnoses;
- Agora remains optional and pending #16.

If publication is externally blocked, keep the user docs truthful about that state and do not replace the source-install instructions with a package-index command prematurely.

## Gate 6 — deterministic GREEN

Require:

```text
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
pytest
```

Additionally run the built-artifact clean-install/stdio validation in a clean environment. No CAL access occurs in these deterministic gates.

## Gate 7 — live release candidate GREEN

Run the permanent live smoke exactly once on the candidate after both #41 and #42 fixes are present.

Acceptance requires:

- at most 9 CAL requests, exactly matching the documented case accounting;
- concurrency 1;
- retries 0;
- cache disabled;
- all eight cases semantically successful;
- provenance present;
- no hidden traversal;
- failure classification visible in logs.

A newly detected CAL drift preempts release and gets its own focused bug issue/research/TDD/review loop.

## Gate 8 — logically independent adversarial review

Freeze the exact final implementation SHA and review from release/operations boundaries rather than author history.

Challenge at least:

1. **Artifact integrity:** are wheel and sdist built once and the same artifacts validated/published?
2. **Clean install:** could tests be accidentally importing from checkout instead of the fresh wheel environment?
3. **Version integrity:** can a mismatched tag/package version be published?
4. **OIDC least privilege:** is `id-token: write` isolated to the publish job, with no token secret or PR publish path?
5. **External prerequisite truth:** do docs avoid claiming PyPI publication before it exists?
6. **Smoke budget:** can any branch/retry/loop exceed 9 CAL requests?
7. **Smoke diagnosis:** are `is_error`, parser drift, network/upstream, and unexpected local failures all non-success?
8. **No crawl:** do selected probes remain fixed and avoid link/page traversal?
9. **Offline CI:** can normal CI pass with CAL unreachable?
10. **Package contents:** is CAL data absent from distributions?
11. **Dependency scope:** did #15 accidentally implement or conflict with #18?
12. **Release notes:** do they accurately list the frozen 26-tool v0.1 surface and limitations?

Any blocker enters review-regression RED → minimal fix → full offline GREEN → capped live smoke if the blocker affects live behavior → fresh exact-head review.

## Merge and publication lifecycle

The implementation PR should reference `#15` but should **not** automatically close it on merge if publication is still pending.

After a clean reviewed merge:

1. ensure the PyPI Trusted Publisher/environment prerequisite is configured;
2. create immutable tag `v0.1.0` on the reviewed/merged release commit;
3. let `release.yml` build, validate, live-smoke, publish, and create the GitHub release;
4. verify PyPI exposes `cal-mcp==0.1.0` and the GitHub release/assets exist;
5. verify a clean `pip install cal-mcp==0.1.0` starts `cal-mcp` and reports version `0.1.0`;
6. only then close #15 and unblock #16.

If step 1 cannot be performed with available automation/account access, record the exact blocked prerequisite on #15 and continue other independent backlog work rather than claiming release completion.

## CAL access / load impact

- Research: no new CAL probes; reuse run `33995822616` and focused #41/#42 evidence.
- Normal implementation/CI: zero CAL requests.
- Candidate validation: one permanent capped run, maximum 9 requests.
- Scheduled smoke: one capped run per week, maximum 9 requests/run.
- Release: one capped run for the immutable tagged release, maximum 9 requests.
- No crawl, result enumeration, pagination, retries, background polling, or cache warming.