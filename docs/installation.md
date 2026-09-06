# Installation

CAL-MCP v0.1.0 is distributed as a standard Python wheel/source distribution in the GitHub `v0.1.0` release. The project does not currently claim a PyPI publication path.

## Requirements

- Python 3.11 or newer;
- network access to `https://cal.huc.edu/` when a CAL-backed tool is actually called.

Importing/introspecting the server does not contact CAL. Normal automated tests are offline with respect to CAL.

## Install the release artifact

Download the `cal_mcp-0.1.0-py3-none-any.whl` asset from the GitHub `v0.1.0` release, then install that wheel:

```bash
python -m pip install ./cal_mcp-0.1.0-py3-none-any.whl
```

The wheel installs CAL-MCP plus its declared runtime dependencies. The release also carries a source distribution for standard Python packaging workflows.

The stable downstream pin is:

```text
package: cal-mcp
version: 0.1.0
entry point: cal-mcp
transport: stdio
```

No Agora runtime is required.

## Start the stdio server

The installed command is:

```bash
cal-mcp
```

The equivalent module entry point is:

```bash
python -m cal_mcp
```

Both start the same local MCP server over stdio. Starting the process and listing its tool schemas do not contact CAL; CAL traffic begins only when a CAL-backed tool is invoked.

See [Standalone MCP](integrations/standalone-mcp.md) for the client/process boundary and [Configuration](configuration.md) for request-policy defaults.

## Install from a repository checkout

For development from the repository root:

```bash
python -m pip install -e ".[dev]"
```

The `dev` extra installs Ruff, mypy, and pytest. Runtime dependencies are declared separately in `pyproject.toml`.

## Development checks

Run the deterministic repository gates with:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

The normal suite uses reduced fixtures and mocked transports; it does not depend on CAL availability. Release verification separately builds the wheel/sdist and tests the built wheel in a fresh environment. Live drift checks are isolated from normal CI and have a fixed request budget.

## Package-index status

v0.1.0 publication is through the versioned GitHub release and its attached Python artifacts. Do not use or document a `pip install cal-mcp==0.1.0` package-index command unless a separately reviewed PyPI publication path has actually been established.

Issue #16 owns optional downstream Agora registration. Agora is discovery/install/launch metadata around this same standalone release, not a CAL-MCP runtime dependency.

## Data boundary

Installing CAL-MCP installs software only. It does not install CAL lexical data, texts, citations, dictionaries, or bibliography. CAL-backed results are retrieved live for explicit tool calls and remain subject to CAL and underlying source rights/terms.

See [Limitations](limitations.md) and [Provenance and citation](concepts/provenance-and-citation.md).
