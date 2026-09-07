# Installation

The v0.1 release coordinate is `cal-mcp==0.1.0`. The repository release workflow publishes that exact version from the `v0.1.0` tag after deterministic tests, built-artifact validation, and the bounded CAL live smoke pass.

Public package-index availability should be treated as established only after the tagged release workflow's PyPI publication step succeeds. Until then, install from a repository checkout rather than assuming `cal-mcp==0.1.0` is already available on PyPI.

## Requirements

- Python 3.11 or newer;
- network access to `https://cal.huc.edu/` when a CAL-backed tool is actually called.

Importing or introspecting the server does not contact CAL. Normal automated tests are offline.

## Install the released package

After v0.1.0 has been published to PyPI, install the exact release pin with:

```bash
python -m pip install "cal-mcp==0.1.0"
```

The exact package/version pair is the downstream integration coordinate for the v0.1 release. Avoid an unpinned install when reproducible integration metadata is required.

## Install from a repository checkout

For development, or before the tagged package has been published, install from the CAL-MCP repository root:

```bash
python -m pip install -e ".[dev]"
```

The `dev` extra installs Ruff, mypy, pytest, and the release build tooling used by repository validation. Runtime dependencies are declared separately in `pyproject.toml`.

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

See [Standalone MCP](integrations/standalone-mcp.md) for the client/process boundary and [Configuration](configuration.md) for request-policy defaults.

## Release validation

The v0.1 release pipeline builds one wheel and one source distribution, verifies the built wheel in a fresh virtual environment, launches its installed `cal-mcp` executable over stdio, and checks the frozen 26-tool MCP surface. A separate bounded live smoke then checks representative CAL-backed surfaces before publication.

Merging the release preparation PR does not itself prove that the package is publicly available. The tagged release workflow and its PyPI publication result are the publication evidence.

## Development checks

Run the deterministic repository gates with:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

The normal suite uses reduced fixtures and mocked transports; it must not rely on CAL availability.

## Agora status

Agora registration is a separate downstream task in issue #16. CAL-MCP remains a standalone stdio MCP server and does not import or require Agora. Once v0.1.0 publication is confirmed, Agora can pin the exact `cal-mcp==0.1.0` coordinate and `cal-mcp` executable without changing the runtime implementation.

## Data boundary

Installing CAL-MCP installs software only. It does not install CAL lexical data, texts, citations, dictionaries, or bibliography. CAL-backed results are retrieved live for explicit tool calls and remain subject to CAL and underlying source rights/terms.

See [Limitations](limitations.md) and [Provenance and citation](concepts/provenance-and-citation.md).
