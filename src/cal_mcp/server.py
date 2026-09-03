from mcp.server import MCPServer

from cal_mcp import __version__

mcp = MCPServer(
    "cal-mcp",
    description="Read-only MCP adapter for the Comprehensive Aramaic Lexicon.",
    instructions=(
        "CAL-MCP exposes CAL-backed research tools. "
        "No CAL network-backed scholarly tools are implemented in this bootstrap release."
    ),
    version=__version__,
)


def main() -> None:
    """Run the CAL-MCP server over stdio."""
    mcp.run()
