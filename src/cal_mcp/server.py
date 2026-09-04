from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from cal_mcp import __version__
from cal_mcp.client import CalHttpClient
from cal_mcp.lexicon import LexiconLookupService
from cal_mcp.search import EnglishSearchService


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
        "Use cal_gloss_search for CAL English-gloss search and cal_citation_text_search "
        "for English words inside CAL citations. Ambiguous lexicon headwords return CAL "
        "lemma-key candidates instead of a guessed entry. Results include CAL provenance "
        "and retrieval time."
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


@mcp.tool(
    name="cal_gloss_search",
    title="Search CAL English glosses",
    structured_output=True,
)
async def cal_gloss_search(
    query: str,
    ctx: Context[AppContext],
    all_glosses: bool = False,
) -> dict[str, object]:
    """Search CAL English glosses without reranking or expanding the query.

    Set ``all_glosses`` to include subsidiary CAL glosses as well as primary glosses.
    One tool call performs one bounded CAL search request.
    """

    client = ctx.request_context.lifespan_context.client
    result = await EnglishSearchService(client).search_gloss(query, all_glosses=all_glosses)
    return result.to_dict()


@mcp.tool(
    name="cal_citation_text_search",
    title="Search English words in CAL citations",
    structured_output=True,
)
async def cal_citation_text_search(
    query: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Search one to three English words in CAL lexicon citations.

    Results preserve CAL lemma references, lexical context, citation reference, source text,
    and English translation. One tool call performs one bounded CAL search request.
    """

    client = ctx.request_context.lifespan_context.client
    result = await EnglishSearchService(client).search_citations(query)
    return result.to_dict()


def main() -> None:
    """Run the CAL-MCP server over stdio."""
    mcp.run()
