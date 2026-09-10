from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from cal_mcp import __version__
from cal_mcp.bibliography import BibliographyService
from cal_mcp.client import CalHttpClient
from cal_mcp.concordance import ConcordanceService
from cal_mcp.dictionary_collation import DictionaryCollationService, DictionarySource
from cal_mcp.external_citations import ExternalCitationService
from cal_mcp.lexicon import LexiconLookupService
from cal_mcp.normalization import InputRepresentation, convert_to_cal_code
from cal_mcp.search import EnglishSearchService, GlossField
from cal_mcp.syriac import SyriacService
from cal_mcp.targum import TargumService
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
        "Use cal_convert_to_code for local-only conversion of supported Aramaic Unicode or "
        "transliteration input into explicit bounded CAL-code candidates; this tool performs "
        "no CAL request. Use cal_lexicon_lookup for bounded live CAL lexicon lookup; finite "
        "orthographic ambiguity is searched across all bounded CAL-code variants rather than "
        "guessed. "
        "Use cal_gloss_search for ordinary CAL English-gloss search, cal_gloss_field for "
        "CAL indexed specialized gloss fields, and cal_citation_text_search for English "
        "words inside CAL citations. Use cal_text_catalogue to discover CAL "
        "text/category identifiers, cal_text_search to find texts by topic, cal_text_page "
        "to retrieve one bounded CAL text page, and cal_text_information to retrieve CAL's "
        "explicit source, edition, editorial, and other free-form Text Information metadata "
        "for one returned file/subtext identifier. Use cal_token_analysis for every CAL lexical "
        "analysis attached to one explicit text coordinate and zero-based token index. "
        "Use cal_text_concordance for one text's ordered lemma-frequency index, cal_kwic_texts "
        "for one lemma in 1-8 explicit texts, cal_kwic_dialects to discover CAL's current "
        "dialect identifiers, cal_kwic_dialect for one explicit dialect, and "
        "cal_kwic_full_context to follow one returned KWIC hit using its typed "
        "file/target/charset selectors. Use "
        "cal_bibliography_authors to discover exact author choices, then "
        "cal_bibliography_author for one selected author. Use cal_bibliography_keyword for "
        "one exact CAL text/subject bibliography tag and cal_bibliography_lemma for one exact "
        "CAL lemma key. Use cal_dictionary_collation for CAL's stored lemma "
        "correspondences for one explicit dictionary page reference. Use "
        "cal_targum_parallel for one biblical verse across current CAL "
        "Targum readings, cal_targum_concordance for Targum-specific lemma counts, and the "
        "two cal_targum_hebrew_* tools for explicit MT-lemma discovery/reflex lookup. "
        "Use cal_syriac_texts for one explicit CAL Syriac text category and "
        "cal_syriac_group for one GROUP selector returned by that tool. Use "
        "cal_syriac_missing_words for one CAL-curated missing-from-A-Syriac-Lexicon "
        "list, and cal_syriac_peshitta_parallel for one MT/Peshitta verse. Syriac direct-text, "
        "catalogue, and lexicon follow-ups compose through cal_text_page, cal_text_catalogue, "
        "and cal_lexicon_lookup. Use cal_external_citation_dialects to discover CAL "
        "dialect identifiers for citations from texts not in the online corpus, "
        "cal_external_citation_sources for one returned dialect, and "
        "cal_external_citations for one exact returned source abbreviation. "
        "The external/non-online-text citations workflow is distinct from "
        "cal_citation_text_search. "
        "Follow-ups are always explicit tool calls; there is no "
        "hidden text, dialect, "
        "bibliography-tag, dictionary-page, Targum-version, or full-context traversal. "
        "Ambiguous analyses and "
        "author prefixes remain ordered CAL alternatives rather than guessed preferred readings. "
        "Results include CAL provenance and retrieval time."
    ),
    version=__version__,
    lifespan=app_lifespan,
)


@mcp.tool(
    name="cal_convert_to_code",
    title="Convert Aramaic input to CAL code candidates",
    structured_output=True,
)
async def cal_convert_to_code(
    value: str,
    representation: InputRepresentation | None = None,
) -> dict[str, object]:
    """Convert supported Aramaic input locally without any CAL network request.

    Finite orthographic ambiguity is returned as ordered CAL-code candidates per word.
    Unsupported or unverified marks fail explicitly rather than being stripped or guessed.
    """

    return convert_to_cal_code(value, representation=representation).to_dict()


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

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await EnglishSearchService(client).search_gloss(query, all_glosses=all_glosses)
    return result.to_dict()


@mcp.tool(
    name="cal_gloss_field",
    title="Search one CAL specialized gloss field",
    structured_output=True,
)
async def cal_gloss_field(
    field: GlossField,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Search one CAL indexed specialized gloss field.

    The readable enum is mapped to CAL's private current field selector. It does not expand or
    traverse other fields.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await EnglishSearchService(client).search_gloss_field(field)
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
    and English translation.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
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
    by a prior call. One explicit call submits at most one new logical CAL request. A
    completed cache hit performs no new upstream I/O.
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

    One explicit call submits at most one new logical CAL request and returns CAL file/subtext
    identifiers suitable for explicit follow-up retrieval. A completed cache hit performs no
    new upstream I/O.
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
    name="cal_text_information",
    title="Retrieve CAL text information metadata",
    structured_output=True,
)
async def cal_text_information(
    file_id: str,
    ctx: Context[AppContext],
    subtext_id: str | None = None,
) -> dict[str, object]:
    """Retrieve CAL's explicit Text Information metadata for one text or subtext.

    Metadata is returned as CAL's ordered free-form text rather than inferred bibliographic
    fields. One explicit call submits at most one new logical CAL request and follows no
    metadata links. A completed cache hit performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await TextService(client).information(file_id, subtext_id=subtext_id)
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
    zero-based, matching the token metadata returned by ``cal_text_page``. Candidate lexicon
    entries are never expanded automatically.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
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

    ``script`` is ``semitic`` (default) or ``transliteration``. Following a lemma into
    KWIC requires another explicit tool call.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
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
    or ``syriac``. Full context is never fetched automatically.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
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

    It never expands to other dialects or fetches full-context pages automatically.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await ConcordanceService(client).kwic_dialect(lemma_key, dialect_id)
    return result.to_dict()


@mcp.tool(
    name="cal_kwic_full_context",
    title="Read full CAL context for one KWIC hit",
    structured_output=True,
)
async def cal_kwic_full_context(
    file_id: str,
    target_coordinate: str,
    charset: str,
    ctx: Context[AppContext],
    subtext_id: str | None = None,
) -> dict[str, object]:
    """Follow one returned CAL KWIC hit into its bounded full-context page.

    Pass the hit's ``file_id``, ``target_coordinate``, ``charset``, and optional
    ``subtext_id``. Arbitrary URLs are not accepted and no returned links are followed.
    One explicit call submits at most one new logical CAL request; a completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await ConcordanceService(client).kwic_full_context(
        file_id,
        target_coordinate,
        charset,
        subtext_id=subtext_id,
    )
    return result.to_dict()


@mcp.tool(
    name="cal_bibliography_authors",
    title="Find exact CAL bibliography authors",
    structured_output=True,
)
async def cal_bibliography_authors(
    prefix: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL's ordered exact author choices for a 1-6 character prefix.

    Ambiguous prefixes remain explicit choices. Use a returned author value in a separate
    ``cal_bibliography_author`` call.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await BibliographyService(client).authors(prefix)
    return result.to_dict()


@mcp.tool(
    name="cal_bibliography_author",
    title="Search CAL bibliography by exact author",
    structured_output=True,
)
async def cal_bibliography_author(
    author: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL bibliography records for one exact author value.

    Reuse an exact value returned by ``cal_bibliography_authors`` rather than guessing among
    prefix matches. Citation text, Unicode, and CAL record links are preserved.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await BibliographyService(client).author(author)
    return result.to_dict()


@mcp.tool(
    name="cal_bibliography_keyword",
    title="Search CAL bibliography by exact text or subject tag",
    structured_output=True,
)
async def cal_bibliography_keyword(
    keyword: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return records for one exact CAL text/subject bibliography tag.

    ``keyword`` follows CAL's bibliography tag vocabulary; it is not fuzzy or full-text
    search. Returned record tags can be reused in later explicit calls.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await BibliographyService(client).keyword(keyword)
    return result.to_dict()


@mcp.tool(
    name="cal_bibliography_lemma",
    title="Search CAL bibliography by exact lemma",
    structured_output=True,
)
async def cal_bibliography_lemma(
    lemma_key: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return bibliography records for one exact canonical CAL lemma key.

    Reuse canonical lemma keys returned by CAL-MCP where possible. Linked lemma keys and CAL
    tags are preserved for explicit follow-up calls.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await BibliographyService(client).lemma(lemma_key)
    return result.to_dict()


@mcp.tool(
    name="cal_targum_parallel",
    title="Compare one biblical verse across CAL Targum sources",
    structured_output=True,
)
async def cal_targum_parallel(
    book: str,
    chapter: int,
    verse: int,
    ctx: Context[AppContext],
    include_peshitta: bool = False,
    include_samaritan: bool = False,
) -> dict[str, object]:
    """Return CAL's ordered MT/Targum readings for one explicit biblical verse.

    ``book`` is one exact CAL Targum book label. Peshitta and Samaritan are optional
    upstream comparison sources and are never fabricated when CAL has no reading.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await TargumService(client).parallel(
        book,
        chapter,
        verse,
        include_peshitta=include_peshitta,
        include_samaritan=include_samaritan,
    )
    return result.to_dict()


@mcp.tool(
    name="cal_targum_concordance",
    title="Count a CAL lemma across Targum sources",
    structured_output=True,
)
async def cal_targum_concordance(
    lemma_key: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL's ordered Targum-specific occurrence counts for one lemma key.

    A complete all-zero CAL table is preserved as a valid zero-result concordance.
    Detailed source examples remain separate explicit follow-up requests.
    """

    client = ctx.request_context.lifespan_context.client
    result = await TargumService(client).concordance(lemma_key)
    return result.to_dict()


@mcp.tool(
    name="cal_targum_hebrew_lemmas",
    title="Discover MT Hebrew lemmas for CAL Targum reflex study",
    structured_output=True,
)
async def cal_targum_hebrew_lemmas(
    initial: str,
    targum: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return ordered CAL MT-lemma choices for one Hebrew initial and Targum source.

    ``targum`` is currently ``onqelos`` or ``neofiti``. Returned MT lemma IDs are opaque
    CAL selector identifiers for a later explicit ``cal_targum_hebrew_reflexes`` call.
    """

    client = ctx.request_context.lifespan_context.client
    result = await TargumService(client).hebrew_lemmas(initial, targum)
    return result.to_dict()


@mcp.tool(
    name="cal_targum_hebrew_reflexes",
    title="Find Targumic reflexes of one selected MT Hebrew lemma",
    structured_output=True,
)
async def cal_targum_hebrew_reflexes(
    targum: str,
    mt_lemma_id: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL Aramaic lemma correspondences for one selected MT lemma.

    Use an opaque ID returned by ``cal_targum_hebrew_lemmas``. CAL currently supports the
    exposed workflow for Onqelos and Neofiti; no hidden example traversal is performed.
    """

    client = ctx.request_context.lifespan_context.client
    result = await TargumService(client).hebrew_reflexes(targum, mt_lemma_id)
    return result.to_dict()


@mcp.tool(
    name="cal_syriac_texts",
    title="Browse one CAL Syriac text category",
    structured_output=True,
)
async def cal_syriac_texts(
    category: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return one bounded CAL Syriac text-category listing.

    ``category`` is a CAL-MCP descriptive slug, not CAL's private numeric category value.
    Direct text, grouped-navigation, and catalogue results remain distinct and are never
    followed automatically. Use ``cal_syriac_group`` for returned GROUP selectors and the
    generic text tools for explicit direct-text/catalogue follow-up.
    """

    client = ctx.request_context.lifespan_context.client
    result = await SyriacService(client).texts(category)
    return result.to_dict()


@mcp.tool(
    name="cal_syriac_group",
    title="Browse one returned CAL Syriac grouped-text selector",
    structured_output=True,
)
async def cal_syriac_group(
    group_id: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Follow one GROUP selector returned by ``cal_syriac_texts``.

    ``group_id`` is CAL's grouped-text selector, not a generic file or catalogue identifier.
    Returned child navigation remains ordered metadata and is never followed recursively.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await SyriacService(client).group(group_id)
    return result.to_dict()


@mcp.tool(
    name="cal_syriac_missing_words",
    title="List CAL Syriac headwords absent from A Syriac Lexicon",
    structured_output=True,
)
async def cal_syriac_missing_words(
    category: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return one CAL-curated missing-from-A-Syriac-Lexicon category.

    This is CAL's published comparison surface against A Syriac Lexicon, not SEDRA and not
    an adapter-inferred equivalence. Full CAL lexicon entries require a separate explicit
    lookup.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await SyriacService(client).missing_words(category)
    return result.to_dict()


@mcp.tool(
    name="cal_syriac_peshitta_parallel",
    title="Compare one biblical verse in MT and CAL Peshitta",
    structured_output=True,
)
async def cal_syriac_peshitta_parallel(
    book: str,
    chapter: int,
    verse: int,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL's MT/Peshitta comparison for one explicit biblical verse.

    The result preserves CAL Hebrew/Syriac text and the Peshitta source link. Invalid
    coordinates are a typed not-found state; previous/next verse links are never followed.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await SyriacService(client).peshitta_parallel(book, chapter, verse)
    return result.to_dict()


@mcp.tool(
    name="cal_external_citation_dialects",
    title="Discover CAL dialects with external citations",
    structured_output=True,
)
async def cal_external_citation_dialects(
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL's current dialect choices for citations from non-online texts.

    Use one returned ``dialect_id`` in a separate ``cal_external_citation_sources`` call.
    It does not enumerate sources.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await ExternalCitationService(client).dialects()
    return result.to_dict()


@mcp.tool(
    name="cal_external_citation_sources",
    title="List cited non-online CAL sources in one dialect",
    structured_output=True,
)
async def cal_external_citation_sources(
    dialect_id: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL source abbreviations/descriptions for one explicit dialect.

    ``dialect_id`` must come from ``cal_external_citation_dialects``. The returned sources
    have citations in CAL but no full online text; no source or citation is followed
    automatically.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await ExternalCitationService(client).sources(dialect_id)
    return result.to_dict()


@mcp.tool(
    name="cal_external_citations",
    title="Retrieve CAL citations for one non-online source",
    structured_output=True,
)
async def cal_external_citations(
    source_abbrev: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL's ordered lexical citations for one exact external source abbreviation.

    ``source_abbrev`` should come from ``cal_external_citation_sources``. Lexical-entry links
    are preserved as metadata but are never followed automatically, and the source is not
    represented as an online CAL passage.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await ExternalCitationService(client).citations(source_abbrev)
    return result.to_dict()


@mcp.tool(
    name="cal_dictionary_collation",
    title="Collate one CAL dictionary page",
    structured_output=True,
)
async def cal_dictionary_collation(
    source: DictionarySource,
    page: str,
    ctx: Context[AppContext],
) -> dict[str, object]:
    """Return CAL's stored lemma correspondences for one dictionary page reference.

    ``source`` is a readable CAL-MCP dictionary identifier. ``page`` accepts CAL's documented
    decimal page syntax, including volume-qualified lists such as ``1:134, 2:212``. Returned
    lemma links are never followed automatically.

    One explicit call submits at most one new logical CAL request. A completed cache hit
    performs no new upstream I/O.
    """

    client = ctx.request_context.lifespan_context.client
    result = await DictionaryCollationService(client).collate(source, page)
    return result.to_dict()


def main() -> None:
    """Run the CAL-MCP server over stdio."""
    mcp.run()
