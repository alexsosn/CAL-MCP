from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from cal_mcp import __version__
from cal_mcp.client import CalHttpClient
from cal_mcp.concordance import ConcordanceService
from cal_mcp.lexicon import LexiconLookupService
from cal_mcp.search import EnglishSearchService
from cal_mcp.texts import TextService
from cal_mcp.token_analysis import TokenAnalysisService


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
        "for English words inside CAL citations. Use cal_text_catalogue to discover CAL "
        "text/category identifiers, cal_text_search to find texts by topic, and cal_text_page "
        "to retrieve one bounded CAL text page. Use cal_token_analysis for every CAL lexical "
        "analysis attached to one explicit text coordinate and zero-based token index. "
        "Use cal_text_concordance for one text's ordered lemma-frequency index, cal_kwic_texts "
        "for one lemma in 1-8 explicit texts, cal_kwic_dialects to discover CAL's current "
        "dialect identifiers, and cal_kwic_dialect for one explicit dialect. Concordance/KWIC "
        "follow-ups are always explicit tool calls; there is no hidden text, dialect, or full-"
        "context traversal. Ambiguous analyses remain ordered CAL alternatives rather than a "
        "guessed preferred reading. Results include CAL provenance and retrieval time."
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


@mcp.tool(
    name="cal_text_catalogue",
    title="Browse one CAL text catalogue level",
    structured_output=True,
)
async def cal_text_catalogue(
    ctx: Context[AppContext],
    category_id: str | None = None,
) -> dict[str, object]:
    """List one explicit CAL text catalogue level without recursive traversal.

    Omit ``category_id`` for the root catalogue or pass one CAL category identifier returned
    by a prior call. Each call performs exactly one bounded CAL request.
    """

    client = ctx.request_context.lifespan_context.client
    result = await TextService(client).catalogue(category_id=category_id)
    return result.to_dict()


@mcp.tool(
    name="cal_text_search",
    title="Search CAL texts by topic",
    structured_output=True,
)
async def cal_text_search(
    query: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Search CAL's current text/topic index without expanding or reranking the query.

    Each call performs exactly one bounded CAL search request and returns CAL file/subtext
    identifiers suitable for explicit follow-up retrieval.
    """

    client = ctx.request_context.lifespan_context.client
    result = await TextService(client).search(query)
    return result.to_dict()


@mcp.tool(
    name="cal_text_page",
    title="Retrieve one CAL text page",
    structured_output=True,
)
async def cal_text_page(
    file_id: str,
    ctx: Context[AppContext],
    subtext_id: str | None = None,
    page: int = 1,
) -> dict[str, object]:
    """Retrieve one normal CAL text page with line/token coordinate metadata.

    Public page numbers are one-based. CAL's unbounded ``show all`` navigation is not
    exposed; moving to another page requires another explicit tool call.
    """

    client = ctx.request_context.lifespan_context.client
    result = await TextService(client).page(file_id, subtext_id=subtext_id, page=page)
    return result.to_dict()


@mcp.tool(
    name="cal_token_analysis",
    title="Analyze one CAL text token",
    structured_output=True,
)
async def cal_token_analysis(
    coordinate: str,
    word_index: int,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return every CAL lexical analysis for one explicit text coordinate/token index.

    ``coordinate`` is CAL's opaque decimal machine coordinate and ``word_index`` is
    zero-based, matching the token metadata returned by ``cal_text_page``. One call performs
    one bounded CAL request and never expands candidate lexicon entries automatically.
    """

    client = ctx.request_context.lifespan_context.client
    result = await TokenAnalysisService(client).analyze(coordinate, word_index)
    return result.to_dict()


@mcp.tool(
    name="cal_text_concordance",
    title="List one CAL text concordance",
    structured_output=True,
)
async def cal_text_concordance(
    text_id: str,
    ctx: Context[AppContext],
    script: str = "semitic",
) -> dict[str, object]:
    """Return CAL's ordered lemma-frequency index for one explicit text.

    ``script`` is ``semitic`` (default) or ``transliteration``. One call performs exactly
    one bounded CAL request. Following a lemma into KWIC requires another explicit tool call.
    """

    client = ctx.request_context.lifespan_context.client
    result = await ConcordanceService(client).text_concordance(text_id, script=script)
    return result.to_dict()


@mcp.tool(
    name="cal_kwic_texts",
    title="Find CAL KWIC hits in explicit texts",
    structured_output=True,
)
async def cal_kwic_texts(
    lemma_key: str,
    text_ids: list[str],
    ctx: Context[AppContext],
    script: str = "roman",
) -> dict[str, object]:
    """Return ordered CAL KWIC hits for one lemma key in 1-8 explicit texts.

    Duplicate CAL hits remain duplicated and ordered. ``script`` is ``roman``, ``hebrew``,
    or ``syriac``. One call performs one bounded CAL request and never fetches full context.
    """

    client = ctx.request_context.lifespan_context.client
    result = await ConcordanceService(client).kwic_texts(
        lemma_key,
        text_ids,
        script=script,
    )
    return result.to_dict()


@mcp.tool(
    name="cal_kwic_dialects",
    title="List CAL KWIC dialect choices",
    structured_output=True,
)
async def cal_kwic_dialects(
    lemma_key: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL's current ordered dialect ID/label choices for one lemma key.

    Dialect identifiers are read live from CAL rather than hard-coded. Use a returned
    ``dialect_id`` in a separate ``cal_kwic_dialect`` call.
    """

    client = ctx.request_context.lifespan_context.client
    result = await ConcordanceService(client).kwic_dialects(lemma_key)
    return result.to_dict()


@mcp.tool(
    name="cal_kwic_dialect",
    title="Find CAL KWIC hits in one dialect",
    structured_output=True,
)
async def cal_kwic_dialect(
    lemma_key: str,
    dialect_id: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return ordered CAL KWIC hits for one lemma key and one explicit dialect.

    One call performs exactly one CAL request and never expands to other dialects or fetches
    full-context pages automatically.
    """

    client = ctx.request_context.lifespan_context.client
    result = await ConcordanceService(client).kwic_dialect(lemma_key, dialect_id)
    return result.to_dict()


def main() -> None:
    """Run the CAL-MCP server over stdio."""
    mcp.run()
