# Issue #158 plan — `cal-mcp --help` / `--version` print and exit

This change is local only, with no CAL request and no research step.

## Change

`cal_mcp.server.main(argv=None)` parses its arguments with `argparse` before starting the server:

- no arguments: `mcp.run()` exactly as now (stdio MCP server);
- `--help` / `-h`: print usage to stdout (what the command does, that it is a stdio MCP server
  meant to be launched by an MCP client, and where the docs are), then exit 0;
- `--version`: print `cal-mcp <version>`, then exit 0;
- an unknown argument: argparse's usage error on stderr, exit 2. The server does not start.

`python -m cal_mcp` shares the same entry point.

## RED tests (subprocess, offline)

- `python -m cal_mcp --version` exits 0 promptly with `cal-mcp <__version__>`.
- `python -m cal_mcp --help` exits 0 promptly, and the usage mentions stdio and MCP.
- `python -m cal_mcp --bogus` exits non-zero with usage on stderr.
- No arguments: the existing stdio tests stay unchanged.

## Docs

`docs/installation.md` gains `cal-mcp --version` as an install check and notes that `--help` does
not start the server. `CHANGELOG.md` is updated too.
