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
