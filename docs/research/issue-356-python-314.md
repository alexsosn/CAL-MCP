# Issue #356 — Python 3.14 installed-client compatibility (2026-11-18)

## Research and user outcome

A researcher should be able to install CAL-MCP on a maintained Python release,
start the standard stdio server and discover the same current 37 public tools.
This must remain usable independently of Agora and must not require CAL requests
merely to start or enumerate tools.

The current `pyproject.toml` permits Python >=3.11 and depends on `mcp>=2,<3`,
`httpx2>=2.12,<3`, and `jsonschema>=4.26,<5`. The existing GitHub Actions
CI runs both frozen `deterministic` and unfrozen `latest-compatible` jobs
under Python 3.11. The 3.11 freeze is intentionally tied to
`constraints/ci-py311.txt` and `constraints/build-py311.txt`; it is not
evidence that the same pinned distributions install on 3.14.

Relevant upstream references (subject to verification by the actual CI run):
- https://py.sdk.modelcontextprotocol.io/get-started/installation/
- https://github.com/modelcontextprotocol/python-sdk/blob/main/pyproject.toml
- https://python-jsonschema.readthedocs.io/

A supported-requires-python declaration or upstream package marker is not
proof that the **CAL-MCP** installed stdio transport works on Python 3.14.
The checked-in `scripts/verify_release_artifact.py` already builds isolated
installation environments for the wheel and sdist and checks server identity,
distribution version and the **exact** release-surface tool-name set. Reuse it.

## Plan / minimal implementation

1. Test first: extend existing CI contract tests to require a 3.14 latest-compatible
   matrix lane, unpinned dependency resolution, `pip check`, full pytest, a
   wheel+sdist build, and invocation of the existing clean-install MCP verifier.
   Keep the frozen Python 3.11 lane untouched. Confirm the new test is RED
   against the current workflow.
2. Replace only the `latest-compatible` job's fixed Python 3.11 with a 3.11/3.14
   matrix. Add `python -m build` and
   `python scripts/verify_release_artifact.py dist` to the 3.14 lane.
   Do not add new per-version constraint files, custom transport scripts, or
   separate workflow infrastructure.
3. Require an exact-head GitHub Actions GREEN result for deterministic 3.11,
   latest-compatible 3.11, and latest-compatible 3.14, including tests and
   clean installation/stdio tool discovery on 3.14. Independently audit the
   workflow, package dependencies and verifier for false positives.
4. If CI shows a real compatibility failure, fix only the demonstrated defect
   with a focused failing regression first. Check docs only after tested evidence.
   The release/tag workflow remains frozen for reviewed v0.2.0 candidate
   commit `e5af84ba1aed6a477720c2e23c3da270340deba6`.

## Scope and remaining acceptance

Normal CI must not query CAL. A single source-attributed *live* CAL request on
Python 3.14, when permitted, remains an explicit user-facing acceptance gate
for #356; a green installed-offline CI run alone does not establish it.
Do not mark #356 fully complete without recording that gate and any separate
Python 3.15 observation. This is independent of the blocked v0.2.0 tag/publish
handoff tracked in #353. No tags or PyPI publishing in this branch.


## Observed implementation/CI result (2026-11-18)

The workflow change landed in the PR branch and the first complete, exact-head
GitHub Actions run passed at commit
`dc6b6eb929ae8b638b4a5752cad99fd0136387bb`:
https://github.com/alexsosn/CAL-MCP/actions/runs/44394364828

- Python 3.11 frozen: 2,468 pytest tests passed.
- Python 3.11 latest-compatible: 2,468 pytest tests passed.
- Python 3.14 latest-compatible: 2,468 pytest tests passed.
- The Python 3.14 job built one `cal_mcp-0.2.0-py3-none-any.whl`
  and one `cal_mcp-0.2.0.tar.gz`.
- Its clean wheel **and** sdist installs both succeeded; the existing verifier
  reported `verified cal-mcp 0.2.0 wheel/sdist and installed stdio MCP surface`.
  That verifier starts the installed server via the MCP SDK and checks the exact
  `CURRENT_PUBLIC_TOOLS` set (37 names) plus server identity/version.
- Observed unpinned Python 3.14 resolution included `mcp==2.3.0`,
  `httpx2==2.16.2`, and `jsonschema==4.26.0`.
- Ruff lint, format and strict mypy passed in all three jobs. No CAL operation
  or PyPI publication was attempted.

The initial test-only CI head `d24e6da` stopped at Ruff format *before*
pytest; do not cite it as a pytest RED run. The contract assertion was checked
against the prechange workflow and failed on its missing matrix/installed test
steps. Final revision fixed style and passed the full GitHub CI gate.

**Remaining:** a bounded real CAL source-attributed operation from an installed
Python 3.14 client, and a separate Python 3.15 probe. Issue #356 stays open
until those acceptance items are evidenced. A source-wheel CI run is not a
public PyPI `cal-mcp==0.2.0` publication; issue #353 remains blocked on tagging.


## Final acceptance evidence (2026-11-25)

The exact merged source `c9b01aa0bd2fb508110499af241fd483231f16e4`
passed all three normal CI jobs in [run 44396089460](https://github.com/alexsosn/CAL-MCP/actions/runs/44396089460).
A separate one-shot, nonpublishing [run 45516445118](https://github.com/alexsosn/CAL-MCP/actions/runs/45516445118)
checked out that exact source and completed successfully on its first attempt.
Its probe workflow is preserved in commit
[`e34f6b5`](https://github.com/alexsosn/CAL-MCP/blob/e34f6b5455037469b1f36316d1cdb54e2cb20d56/.github/workflows/probe-python-356.yml)
and was removed from the temporary branch after completion.

- [Python 3.14.10 live job](https://github.com/alexsosn/CAL-MCP/actions/runs/45516445118/job/138876988994):
  clean wheel install, pip check, exact 37-tool stdio discovery and server
  version 0.2.0; one `cal_bibliography_lemma` call for `cly V` passed the
  existing MCP output-schema, content and provenance checks. The measured
  transport count was exactly 1 (no retry). It returned one record; the
  reported source was
  https://cal.huc.edu/getbiblemma.php?myauthor=cly+V
  and retrieval timestamp `2026-11-25T00:14:24.403886+00:00`.
  The probe checked the query, operation, endpoint and timestamp against
  the actual call. No bibliography content is redistributed here.
- [Python 3.15.2 offline job](https://github.com/alexsosn/CAL-MCP/actions/runs/45516445118/job/138876988486):
  wheel/sdist build, pip check, independent clean wheel and sdist installs,
  server identity/version and exact 37-tool stdio discovery passed using the
  existing artifact verifier. No CAL call or full pytest suite was run on 3.15.
- Both probe environments resolved `mcp==2.3.0`, `httpx2==2.16.2` and
  `jsonschema==4.26.0`.

This completes the scoped compatibility acceptance for issue #356: 3.14 is
covered by normal CI and a bounded live installed-client operation; 3.15
has an additional successful offline installation/discovery observation only.
It does not establish full 3.15 runtime compatibility, every CAL operation on
3.14, or a published v0.2.0 artifact. The tagged-wheel publication gate in
issue #353 remains separate and unchanged. No further CAL traffic or
permanent probe workflow is needed for this issue.
