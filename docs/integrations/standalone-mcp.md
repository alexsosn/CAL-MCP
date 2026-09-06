# Standalone MCP

CAL-MCP v0.1.0 runs as a normal local MCP server without Agora. The required v0.1 transport is stdio.

## Process contract

After installing the v0.1.0 wheel, launch either:

```bash
cal-mcp
```

or:

```bash
python -m cal_mcp
```

Both start the same MCP server and communicate over standard input/output according to the installed MCP framework.

A client should treat CAL-MCP as a long-running local child process for the session. The server creates one bounded `CalHttpClient` for its lifespan and reuses it across tool calls, which allows process-local cache and duplicate in-flight request suppression to work across requests in that session.

Starting the process does not itself send a CAL query. CAL traffic begins only when a CAL-backed tool is called.

## Stable downstream launch contract

Exact client configuration syntax differs by MCP client and changes independently of CAL-MCP. The stable v0.1.0 launch contract is:

```text
package: cal-mcp
version: 0.1.0
command: cal-mcp
arguments: none
transport: stdio
```

For a source/development environment where the module entry point is preferred:

```text
command: python
arguments: -m cal_mcp
transport: stdio
```

The client should launch the command in an environment where CAL-MCP and its runtime dependencies are installed. No Agora runtime is required.

## Network/data boundary

The MCP transport is local stdio, but CAL-MCP's data source is remote CAL. Tool calls that need CAL therefore require outbound HTTPS access to `cal.huc.edu`.

The process does not host a CAL proxy, expose a public network service, or maintain a local CAL database. Returned CAL data stays bounded by the explicit tool call and request policy.

See [Configuration](../configuration.md) and [Limitations](../limitations.md).

## Tool discovery

MCP clients should use the server's executable tool schemas rather than relying on hand-maintained parameter lists. The v0.1.0 surface contains 26 public tools grouped in the [user documentation index](../index.md).

CAL form field names and PHP endpoint names are not part of the MCP contract.

## Failure handling

Transport-level MCP process failures are distinct from CAL request/parser failures produced while executing a tool. For the CAL-side taxonomy, see [Errors and upstream drift](../concepts/errors-and-upstream-drift.md).

A parser-drift error should not be interpreted by the client as a legitimate empty CAL result. The separately scheduled/opt-in live smoke treats MCP error results as failures and keeps network/upstream unavailability distinguishable from adapter/parser drift where the execution boundary provides enough evidence.

## Release verification

The v0.1 release gate builds both source distribution and wheel, installs the built wheel into a fresh environment, verifies installed metadata version `0.1.0`, and launches the installed `cal-mcp` command over stdio. Normal CI remains CAL-independent.

A separate live drift smoke exercises eight fixed public operations sequentially with retries disabled, cache disabled, concurrency 1, and a hard ceiling of nine CAL requests. It does not enumerate results or follow discovered links.

## Shutdown

When the MCP session ends, the client should close/terminate the stdio server normally. CAL-MCP closes its owned HTTP client at server shutdown; its in-memory cache is not persisted.

## Agora status

Agora registration is a separate downstream task in issue #16. CAL-MCP does not import Agora and does not require it to operate. After registration, Agora should remain discovery/install/launch metadata around the same standalone `cal-mcp==0.1.0` server rather than a second CAL implementation.
