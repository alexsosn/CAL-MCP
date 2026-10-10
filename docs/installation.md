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

Both start the same local MCP server over stdio. Run without arguments, the command waits silently for an MCP client on stdin; it is normally launched by your MCP client rather than typed into a terminal. CAL-MCP does not require Agora to run.

To check an installation without starting the server:

```bash
cal-mcp --version   # prints "cal-mcp <version>" and exits
cal-mcp --help      # prints usage and exits
```

Any other argument, including one combined with `--help` or `--version` and abbreviations such as `--vers`, prints the usage to stderr and exits with status 2 without starting the server.

See [Standalone MCP](integrations/standalone-mcp.md) for the client/process boundary and [Configuration](configuration.md) for request-policy defaults.

## Proxy and CA troubleshooting for MCP clients

An MCP client starts `cal-mcp` as a **child process**. The server's HTTP client
uses the process environment for proxy and CA trust settings; a proxy configured
in your terminal or desktop session may **not** be passed through by your MCP
launcher. In particular, pass the required `HTTPS_PROXY`, `HTTP_PROXY`,
`NO_PROXY`, `SSL_CERT_FILE`, and `SSL_CERT_DIR` variables to the child
process where applicable. These are environment variables, not CAL-MCP
command-line flags.

If your network requires a proxy but the child process lacks that configuration,
every CAL-backed tool may fail. One observed egress-gateway symptom was
`upstream_http` / `CAL returned HTTP 403` with a gateway message
`Host not in allowlist`. **Not every 403 is a proxy error**; inspect the
launcher environment and network policy before deciding whether it came from
CAL or an intermediate gateway. An unconfigured CA bundle can instead produce
a TLS verification failure.

For a Python MCP SDK launcher, set `StdioServerParameters(env=...)` explicitly.
See the runnable [standalone MCP proxy example](integrations/standalone-mcp.md#proxy-and-certificate-environments)
for `env=os.environ.copy()` and the security considerations when forwarding
the parent environment. Avoid placing proxy credentials in logs or issue reports.

## Release validation

The v0.1 release pipeline builds one wheel and one source distribution. Before publication it validates the source archive's embedded package identity/required root metadata, then installs the exact wheel and exact source distribution independently in fresh virtual environments. Each installed artifact launches its `cal-mcp` executable over stdio and must expose the same release version and frozen 35-tool MCP surface. The release job then downloads the **exact wheel** produced by the preceding build job, installs it into a fresh environment without a source checkout, and executes the 12-case MCP stdio smoke through that installed executable. Its server enforces a hard **25-transport-attempt** cap, reports the measured number of attempts, and validates CAL provenance, output schemas, and structured error results. PyPI publication depends on that live job succeeding. The weekly/manual drift workflow uses the same suite against a wheel built from its checked-out revision. The installed-wheel release smoke and independent review for issue #157 have passed.

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
