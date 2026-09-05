from pathlib import Path

server = Path("src/cal_mcp/server.py")
text = server.read_text()
old_import = "from cal_mcp.search import EnglishSearchService\nfrom cal_mcp.texts import TextService\n"
new_import = (
    "from cal_mcp.search import EnglishSearchService\n"
    "from cal_mcp.targum import TargumService\n"
    "from cal_mcp.texts import TextService\n"
)
if text.count(old_import) != 1:
    raise SystemExit("server import anchor mismatch")
text = text.replace(old_import, new_import)

old_instruction = (
    '        "one exact CAL text/subject bibliography tag and cal_bibliography_lemma for one exact "\n'
    '        "CAL lemma key. Follow-ups are always explicit tool calls; there is no hidden text, "\n'
)
new_instruction = (
    '        "one exact CAL text/subject bibliography tag and cal_bibliography_lemma for one exact "\n'
    '        "CAL lemma key. Use cal_targum_parallel for one biblical verse across current CAL "\n'
    '        "Targum readings, cal_targum_concordance for Targum-specific lemma counts, and the "\n'
    '        "two cal_targum_hebrew_* tools for explicit MT-lemma discovery/reflex lookup. "\n'
    '        "Follow-ups are always explicit tool calls; there is no hidden text, "\n'
)
if text.count(old_instruction) != 1:
    raise SystemExit("server instruction anchor mismatch")
text = text.replace(old_instruction, new_instruction)

anchor = "\n\ndef main() -> None:\n"
block = '''

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
    One call performs exactly one bounded CAL request.
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
'''
if text.count(anchor) != 1:
    raise SystemExit("server main anchor mismatch")
server.write_text(text.replace(anchor, block + anchor))

bootstrap = Path("tests/test_bootstrap.py")
text = bootstrap.read_text()
old_names = (
    '        "cal_bibliography_keyword",\n'
    '        "cal_bibliography_lemma",\n'
    "    }\n"
)
new_names = (
    '        "cal_bibliography_keyword",\n'
    '        "cal_bibliography_lemma",\n'
    '        "cal_targum_parallel",\n'
    '        "cal_targum_concordance",\n'
    '        "cal_targum_hebrew_lemmas",\n'
    '        "cal_targum_hebrew_reflexes",\n'
    "    }\n"
)
if text.count(old_names) != 1:
    raise SystemExit("bootstrap name anchor mismatch")
text = text.replace(old_names, new_names)

old_schema = (
    '    bibliography_lemma_schema = tools["cal_bibliography_lemma"].input_schema\n'
    '    assert set(bibliography_lemma_schema["properties"]) == {"lemma_key"}\n'
    '    assert bibliography_lemma_schema["required"] == ["lemma_key"]\n\n'
    "    for schema in (\n"
)
new_schema = (
    '    bibliography_lemma_schema = tools["cal_bibliography_lemma"].input_schema\n'
    '    assert set(bibliography_lemma_schema["properties"]) == {"lemma_key"}\n'
    '    assert bibliography_lemma_schema["required"] == ["lemma_key"]\n\n'
    '    targum_parallel_schema = tools["cal_targum_parallel"].input_schema\n'
    '    assert set(targum_parallel_schema["properties"]) == {\n'
    '        "book",\n'
    '        "chapter",\n'
    '        "verse",\n'
    '        "include_peshitta",\n'
    '        "include_samaritan",\n'
    "    }\n"
    '    assert targum_parallel_schema["required"] == ["book", "chapter", "verse"]\n\n'
    '    targum_concordance_schema = tools["cal_targum_concordance"].input_schema\n'
    '    assert set(targum_concordance_schema["properties"]) == {"lemma_key"}\n'
    '    assert targum_concordance_schema["required"] == ["lemma_key"]\n\n'
    '    targum_hebrew_lemmas_schema = tools["cal_targum_hebrew_lemmas"].input_schema\n'
    '    assert set(targum_hebrew_lemmas_schema["properties"]) == {"initial", "targum"}\n'
    '    assert targum_hebrew_lemmas_schema["required"] == ["initial", "targum"]\n\n'
    '    targum_hebrew_reflexes_schema = tools["cal_targum_hebrew_reflexes"].input_schema\n'
    '    assert set(targum_hebrew_reflexes_schema["properties"]) == {\n'
    '        "targum",\n'
    '        "mt_lemma_id",\n'
    "    }\n"
    '    assert targum_hebrew_reflexes_schema["required"] == ["targum", "mt_lemma_id"]\n\n'
    "    for schema in (\n"
)
if text.count(old_schema) != 1:
    raise SystemExit("bootstrap schema anchor mismatch")
text = text.replace(old_schema, new_schema)

old_loop = (
    "        bibliography_keyword_schema,\n"
    "        bibliography_lemma_schema,\n"
    "    ):\n"
)
new_loop = (
    "        bibliography_keyword_schema,\n"
    "        bibliography_lemma_schema,\n"
    "        targum_parallel_schema,\n"
    "        targum_concordance_schema,\n"
    "        targum_hebrew_lemmas_schema,\n"
    "        targum_hebrew_reflexes_schema,\n"
    "    ):\n"
)
if text.count(old_loop) != 1:
    raise SystemExit("bootstrap loop anchor mismatch")
text = text.replace(old_loop, new_loop)

old_private = '            "lth",\n        ):\n'
new_private = (
    '            "lth",\n'
    '            "bookname",\n'
    '            "Peshitta",\n'
    '            "Sam",\n'
    "        ):\n"
)
if text.count(old_private) != 1:
    raise SystemExit("bootstrap private anchor mismatch")
bootstrap.write_text(text.replace(old_private, new_private))
