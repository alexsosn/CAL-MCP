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

## Proxy and certificate environments

The server's HTTP client honors supported proxy and certificate environment
variables inherited by the child process, including `HTTPS_PROXY`,
`HTTP_PROXY`, `NO_PROXY`, `SSL_CERT_FILE` and `SSL_CERT_DIR`. The
`StdioServerParameters` default environment provided by some Python MCP SDK
versions/launchers may omit `HTTPS_PROXY` even if it exists in the calling
shell. Explicitly pass `env=` where your network requires a proxy or custom CA
certificates. Other MCP clients have their own child-process environment settings.

The following Python MCP SDK example starts the installed server and lists its
tools **without making any CAL request**:

```python
import asyncio
import os

from mcp import Client, StdioServerParameters


async def main() -> None:
    parameters = StdioServerParameters(
        command="cal-mcp",
        env=os.environ.copy(),
    )
    async with Client(parameters) as client:
        tools = await client.list_tools()
        print(len(tools.tools))


asyncio.run(main())
```

Use this full-environment forwarding only for a trusted local executable and
review the inherited variables if they include secrets. A tightly restricted
launcher can instead supply the required proxy/CA variables together with
whatever basic environment (`PATH`, for example) the subprocess needs.
Do not print proxy URLs with embedded credentials.

If a required proxy is absent, CAL-backed calls can fail with
`upstream_http` / `CAL returned HTTP 403`; a 2026-09-24 egress-gateway
reproduction returned `Host not in allowlist`. **Not every 403 comes from
a proxy**: CAL may legitimately return a 403, and proxy or TLS failures can
present differently. Check the actual child environment and your network
administrator's policy before attributing the response to CAL.
See [Installation](../installation.md#proxy-and-ca-troubleshooting-for-mcp-clients).

## Network/data boundary

The MCP transport is local stdio, but CAL-MCP's data source is remote CAL. Tool calls that need CAL therefore require outbound HTTPS access to `cal.huc.edu`.

The process does not host a CAL proxy, expose a public network service, or maintain a local CAL database. Returned CAL data stays bounded by the explicit tool call and request policy.

See [Configuration](../configuration.md) and [Limitations](../limitations.md).

## Tool discovery

MCP clients should use the server's executable tool schemas rather than relying on hand-maintained parameter lists. The v0.1 surface contains 36 public tools grouped in the [user documentation index](../index.md).

CAL form field names and PHP endpoint names are not part of the MCP contract.

## Failure handling

Anticipated CAL-MCP failures return MCP tool results with `isError=true` and a machine-readable `structuredContent.error` object. Clients can inspect its `kind`, `retryable`, and `upstream_reached` fields instead of parsing the human-readable text block. For example, local invalid input is non-retryable with `upstream_reached=false`, while an exhausted network timeout is retryable with `upstream_reached=null` because CAL receipt cannot be known.

Successful empty/not-found results remain ordinary success results. Unexpected programming failures are deliberately different again: they remain on the MCP SDK's generic sanitized error path and do not receive a misleading CAL-MCP error classification.

For the complete public taxonomy and fields, see [Errors and upstream drift](../concepts/errors-and-upstream-drift.md). A parser-drift error should never be interpreted by the client as a legitimate empty CAL result.

## Shutdown

When the MCP session ends, the client should close or terminate the stdio server normally. CAL-MCP closes its owned HTTP client at server shutdown; its in-memory cache is not persisted.

## Release pin and Agora status

The v0.1 downstream coordinates are `cal-mcp==0.1.0`, `command: cal-mcp`, no arguments, and stdio transport. The tagged release workflow verifies the clean wheel and sdist, then downloads the exact built wheel into a fresh environment and tests representative live CAL operations through its installed stdio MCP server (at most 25 actual transport attempts). It checks MCP output schemas, structured errors, provenance and measured request counts before allowing publication. The new smoke gate must pass live acceptance for issue #157 before v0.1 can be published; repository merge alone is not evidence that PyPI publication completed.

Agora registration is a separate downstream task in issue #16. CAL-MCP does not import Agora and does not require it to operate. After publication, Agora should remain discovery/install/launch metadata around the same standalone server rather than a second CAL implementation.
