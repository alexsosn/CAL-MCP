# Research: reject non-file/non-directory members in release sdists (#250)

Date: 2026-10-10; base: main `66fbe3ab420c640a2f57dbec361292e15bdc6018`.

The actual pre-release artifact validator at
`scripts/verify_release_artifact.py::_sdist_version` uses
`tarfile.open(..., "r:gz")`, `getmembers()`, and
`PurePosixPath(member.name)`, and verifies names cannot be absolute,
contain `..`, or cross the expected `cal_mcp-<version>` root.
It also requires `PKG-INFO` and `pyproject.toml` to be regular files.
However, the remainder of the archive may contain *any* tar type,
including `SYMTYPE`, `LNKTYPE`, `FIFOTYPE`, block/character devices,
or unknown typeflags. These members can have entirely safe-looking
member *names* while their link targets are outside the source root.
The subsequent `pip install` may have protections, but the independent
release verifier must not deem such an archive safe.

The simplest correct policy for CAL-MCP's own software-only sdist is
**allow regular files and directories, reject every other type**.
This avoids trying to normalize a dangerous link target, and does not
require reading or extracting contents. A regular `PKG-INFO` or
`pyproject.toml` remains mandatory. If Hatchling legitimately emits
other member types, the tag-free real wheel+sdist rehearsal must expose
that before publication.

Evidence: tag-free unmodified `main` release rehearsal Actions
[38068767600](https://github.com/alexsosn/CAL-MCP/actions/runs/38068767600)
built wheel and sdist, installed each independently in clean venvs,
and verified `cal-mcp 0.1.0`/36-tool stdio MCP without creating a tag
or contacting CAL. This establishes current packaging compatibility,
not proof that malicious tar member types are refused.

No upstream CAL requests, PyPI account calls, public schema changes or
unversioned artifacts are in this ticket.
