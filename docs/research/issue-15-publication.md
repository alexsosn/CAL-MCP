# Issue #15 — v0.1.0 publication record

Published **2026-10-12 in Europe/Helsinki** (PyPI uploads 2026-10-11 22:06:54–56 UTC; GitHub release 22:07:07 UTC). Package `cal-mcp==0.1.0`, Python >=3.11, stdio executable `cal-mcp`, equivalent module `python -m cal_mcp`. Agora is not required.

- [PyPI release](https://pypi.org/project/cal-mcp/0.1.0/).
- [GitHub release](https://github.com/alexsosn/CAL-MCP/releases/tag/v0.1.0).
- [Successful tagged release workflow](https://github.com/alexsosn/CAL-MCP/actions/runs/38178217487).
- Immutable annotated tag `v0.1.0` targets `d8aa7fe269198ee37b4da8d71f5ed2f7eb5fe1fb`; subsequent `main` changes are not part of that release.

The workflow passed 2,303 offline tests, lint, formatting, typing, pinned-environment verification, wheel/sdist clean installation and the frozen 36-tool stdio surface. Its exact installed-wheel fixed smoke passed all 12 cases with **13 actual CAL transport starts out of the 25-attempt cap**, concurrency one, zero retries and 60-second completion spacing. No other CAL requests were made during publication verification. The separate slow 37-token acceptance remains documented in [issue #262's measured record](issue-262-slow-acceptance.md).

Both public PyPI distribution digests and GitHub release-asset digests matched the distributions downloaded from that successful workflow:

| Distribution | SHA-256 |
| --- | --- |
| `cal_mcp-0.1.0-py3-none-any.whl` | `777bdd8d539033ca8403c889d14294a2073a6154c3199952b1ce923b9dfbb785` |
| `cal_mcp-0.1.0.tar.gz` | `aab8c42daefac30bd170653faa35968f87d124a6ec835dfb75f3ee834c605d47` |

A fresh environment installed `cal-mcp==0.1.0` directly from `https://pypi.org/simple`, with committed runtime validation constraints. All 28 installed package Python files matched the published wheel bytes; `cal-mcp --version` reported 0.1.0, and an MCP client launched the installed command outside the checkout and verified server identity, version and exactly 36 public tools. Those post-publication checks made **zero CAL requests**. No CAL textual or lexical content is retained in this record.
