from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from cal_mcp import __version__
from cal_mcp.client import CalHttpClient
from cal_mcp.lexicon import LexiconLookupService


@dataclass(frozen=True, slots=True)
class AppContext:
    client: CalHttpClient


@asynccontextmanager
async def app_lifespan(_server: MCPServer[AppContext]) -> AsyncIterator[AppContext]:
    client = CalHttpClient()
    try:
        yield AppContext(client=client)
    finally:
        await client.aclose()


mcp = MCPServer(
    "cal-mcp",
    description="Read-only MCP adapter for the Comprehensive Aramaic Lexicon.",
    instructions=(
        "Use cal_lexicon_lookup for bounded live CAL lexicon lookup. "
        "Ambiguous headwords return CAL lemma-key candidates instead of a guessed entry. "
        "Results include CAL provenance and retrieval time."
    ),
    version=__version__,
    lifespan=app_lifespan,
)


@mcp.tool(
    name="cal_lexicon_lookup",
    title="Look up a CAL lexicon entry",
    structured_output=True,
)
async def cal_lexicon_lookup(
    query: str,
    ctx: Context[AppContext],
    lemma_key: str | None = None,
) -> dict[str, object]:
    """Look up a CAL root, headword, or full form without guessing between homographs.

    Supply ``lemma_key`` only to choose one of the exact CAL candidates returned by an
    ambiguous lookup. CAL endpoint/form parameters remain internal to this adapter.
    """

    client = ctx.request_context.lifespan_context.client
    result = await LexiconLookupService(client).lookup(query, lemma_key=lemma_key)
    return result.to_dict()


def main() -> None:
    """Run the CAL-MCP server over stdio."""
    mcp.run()
