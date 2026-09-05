# Installation

CAL-MCP is currently **pre-release**. The repository version is `0.1.0.dev0`; no versioned PyPI/release artifact is documented yet. Issue #15 owns the clean published v0.1 package/release gate.

The instructions here describe the current source/development installation and the entry points already exercised by the deterministic test suite.

## Requirements

- Python 3.11 or newer;
- network access to `https://cal.huc.edu/` when a CAL-backed tool is actually called.

Importing/introspecting the server does not contact CAL. Normal automated tests are offline.

## Install from a repository checkout

From the CAL-MCP repository root:

```bash
python -m pip install -e ".[dev]"
```

The `dev` extra installs Ruff, mypy, and pytest for repository development. Runtime dependencies are declared separately in `pyproject.toml`.

## Start the stdio server

The installed command is:

```bash
cal-mcp
```

The equivalent module entry point is:

```bash
python -m cal_mcp
```

Both start the same local MCP server over stdio. CAL-MCP does not require Agora to run.

See [Standalone MCP](integrations/standalone-mcp.md) for the client/process boundary and [Configuration](configuration.md) for the request-policy defaults.

## Development checks

Run the deterministic repository gates with:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

The normal suite uses reduced fixtures and mocked transports; it must not rely on CAL availability.

## What is not published yet

Until issue #15 completes, do not assume any of the following exists as a stable release contract:

- a released `cal-mcp==0.1.0` package/version;
- a package-index installation command;
- versioned release notes or changelog;
- scheduled/opt-in live drift smoke tests for the release;
- a version suitable for downstream marketplace pinning.

Until issue #16 completes, CAL-MCP is also **not** documented as registered in Agora. Agora remains an optional future discovery/install path, not a runtime dependency.

## Data boundary

Installing CAL-MCP installs software only. It does not install CAL lexical data, texts, citations, dictionaries, or bibliography. CAL-backed results are retrieved live for explicit tool calls and remain subject to CAL and underlying source rights/terms.

See [Limitations](limitations.md) and [Provenance and citation](concepts/provenance-and-citation.md).