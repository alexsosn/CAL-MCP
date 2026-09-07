# Standalone MCP

CAL-MCP is designed to run as a normal local MCP server without Agora. The v0.1 release coordinate is `cal-mcp==0.1.0`, and the required v0.1 transport is stdio.

Public package-index availability is established by the successful tagged release workflow. Before that publication step succeeds, the same server can be run from a source/development install without changing its MCP contract.

## Process contract

After installing the released package or a source checkout, launch either:

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

## Client configuration

Exact client configuration syntax differs by MCP client and changes independently of CAL-MCP. The stable v0.1 launch contract is the pinned package plus executable, arguments, and transport rather than a copied client-specific JSON schema.

Release pin:

```text
package: cal-mcp==0.1.0
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

The client should launch the command in an environment where the CAL-MCP package and its dependencies are installed. A downstream integration should treat the successful publication of `cal-mcp==0.1.0` as the availability check rather than inferring publication from the repository version alone.

## Network/data boundary

The MCP transport is local stdio, but CAL-MCP's data source is remote CAL. Tool calls that need CAL therefore require outbound HTTPS access to `cal.huc.edu`.

The process does not host a CAL proxy, expose a public network service, or maintain a local CAL database. Returned CAL data stays bounded by the explicit tool call and request policy.

See [Configuration](../configuration.md) and [Limitations](../limitations.md).

## Tool discovery

MCP clients should use the server's executable tool schemas rather than relying on hand-maintained parameter lists. The v0.1 surface contains 26 public tools grouped in the [user documentation index](../index.md).

CAL form field names and PHP endpoint names are not part of the MCP contract.

## Failure handling

Transport-level MCP process failures are distinct from CAL request/parser failures produced while executing a tool. For the CAL-side taxonomy, see [Errors and upstream drift](../concepts/errors-and-upstream-drift.md).

A parser-drift error should not be interpreted by the client as a legitimate empty CAL result.

## Shutdown

When the MCP session ends, the client should close or terminate the stdio server normally. CAL-MCP closes its owned HTTP client at server shutdown; its in-memory cache is not persisted.

## Release pin and Agora status

The v0.1 downstream coordinates are `cal-mcp==0.1.0`, `command: cal-mcp`, no arguments, and stdio transport. The tagged release workflow performs the clean-artifact, live-smoke, and publication gates; repository merge alone is not evidence that PyPI publication completed.

Agora registration is a separate downstream task in issue #16. CAL-MCP does not import Agora and does not require it to operate. After publication, Agora should remain discovery/install/launch metadata around the same standalone server rather than a second CAL implementation.
