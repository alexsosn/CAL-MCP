from __future__ import annotations

from mcp.server import MCPServer

from cal_mcp import __version__
from cal_mcp.client import CalHttpClient
from cal_mcp.lexicon import LexiconLookupService

mcp = MCPServer(
    "cal-mcp",
    description="Read-only MCP adapter for the Comprehensive Aramaic Lexicon.",
    instructions=(
        "Use cal_lexicon_lookup for bounded live CAL lexicon lookup. "
        "Ambiguous headwords return CAL lemma-key candidates instead of a guessed entry. "
        "Results include CAL provenance and retrieval time."
    ),
    version=__version__,
)


@mcp.tool(
    name="cal_lexicon_lookup",
    title="Look up a CAL lexicon entry",
    structured_output=True,
)
async def cal_lexicon_lookup(query: str, lemma_key: str | None = None) -> dict[str, object]:
    """Look up a CAL root, headword, or full form without guessing between homographs.

    Supply ``lemma_key`` only to choose one of the exact CAL candidates returned by an
    ambiguous lookup. CAL endpoint/form parameters remain internal to this adapter.
    """

    async with CalHttpClient() as client:
        result = await LexiconLookupService(client).lookup(query, lemma_key=lemma_key)
    return result.to_dict()


def main() -> None:
    """Run the CAL-MCP server over stdio."""
    mcp.run()
