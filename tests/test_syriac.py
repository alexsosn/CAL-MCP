from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.syriac import (
    SyriacPeshittaStatus,
    SyriacService,
    SyriacTextNavigationKind,
    SyriacParseError,
    parse_syriac_missing_words_page,
    parse_syriac_peshitta_page,
    parse_syriac_text_category_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 5, 14, 28, tzinfo=UTC)


def _fixture_response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _inline_response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def test_dynamic_syriac_category_preserves_order_navigation_kind_and_info_links() -> None:
    page = parse_syriac_text_category_page(
        _fixture_response(
            "syriac_category_metrical.html",
            "https://cal.huc.edu/show_Syriac_categories.php?category=6",
        ),
        category="metrical-homilies-hymns",
    )

    assert page.label == "METRICAL HOMILIES AND HYMNS"
    assert [(item.upstream_id, item.label, item.navigation_kind) for item in page.items] == [
        ("60420", "Jacob of Serugh, metrical homilies", SyriacTextNavigationKind.GROUP),
        ("60424", "Ephrem, Hymns", SyriacTextNavigationKind.TEXT),
        ("63400", "Narsai, metrical homilies", SyriacTextNavigationKind.GROUP),
    ]
    assert page.items[0].navigation_url == (
        "https://cal.huc.edu/showsubtexts.php?keyword=60420"
    )
    assert page.items[1].navigation_url == (
        "https://cal.huc.edu/get_a_chapter.php?file=60424&cset=S"
    )
    assert page.items[1].info_url == "https://cal.huc.edu/get_file_info.php?coord=60424"


def test_static_syriac_category_uses_same_typed_item_model() -> None:
    page = parse_syriac_text_category_page(
        _fixture_response(
            "syriac_category_ot_peshitta.html",
            "https://cal.huc.edu/ot_peshitta.html",
        ),
        category="ot-peshitta",
    )

    assert page.label == "OT Peshitta"
    assert [(item.upstream_id, item.label) for item in page.items] == [
        ("62001", "P Gn"),
        ("62002", "P Ex"),
    ]
    assert all(item.navigation_kind is SyriacTextNavigationKind.TEXT for item in page.items)


@pytest.mark.parametrize(
    "body",
    [
        (
            "<h1>METRICAL HOMILIES AND HYMNS</h1><ul><li>"
            '<a href="https://example.org/get_a_chapter.php?file=60424">60424</a> Ephrem'
            "</li></ul>"
        ),
        (
            "<h1>METRICAL HOMILIES AND HYMNS</h1><ul><li>"
            '<a href="/showsubtexts.php?keyword=60420&amp;keyword=60421">60420</a> Jacob'
            "</li></ul>"
        ),
        (
            "<h1>METRICAL HOMILIES AND HYMNS</h1><ul><li>"
            '<a href="/get_a_chapter.php?file=60424">60424</a> Ephrem '
            '<a href="/showsubtexts.php?keyword=60424">group</a>'
            "</li></ul>"
        ),
        (
            "<h1>METRICAL HOMILIES AND HYMNS</h1><ul><li>"
            '<a href="/get_a_chapter.php?file=60424">60424</a> Ephrem '
            '<a href="/get_file_info.php?coord=99999">ⓘ</a>'
            "</li></ul>"
        ),
        "<h1>METRICAL HOMILIES AND HYMNS</h1><p>changed markup</p>",
    ],
)
def test_syriac_category_rejects_cross_origin_ambiguous_or_incomplete_rows(body: str) -> None:
    with pytest.raises(SyriacParseError):
        parse_syriac_text_category_page(
            _inline_response(
                body,
                "https://cal.huc.edu/show_Syriac_categories.php?category=6",
            ),
            category="metrical-homilies-hymns",
        )


def test_syriac_category_heading_must_match_selected_category() -> None:
    with pytest.raises(SyriacParseError):
        parse_syriac_text_category_page(
            _fixture_response(
                "syriac_category_metrical.html",
                "https://cal.huc.edu/show_Syriac_categories.php?category=6",
            ),
            category="commentaries",
        )


def test_missing_words_preserve_cal_lemma_keys_labels_notes_and_entry_urls() -> None:
    page = parse_syriac_missing_words_page(
        _fixture_response(
            "syriac_missing_verbs.html",
            "https://cal.huc.edu/display_missing_verbs.php",
        ),
        category="verbs",
    )

    assert page.dictionary_label == "A Syriac Lexicon"
    assert [item.lemma_key for item in page.items] == [")br V", "gbl V", ")t) V"]
    assert [item.label for item in page.items] == ["ˀbr vb.", "gbl vb.", "ˀtˀ vb."]
    assert [item.note for item in page.items] == [
        "D to make a son",
        "to form, fashion",
        "to come",
    ]
    assert page.items[0].entry_url == (
        "https://cal.huc.edu/oneentry.php?cits=all&lemma=%29br+V"
    )


@pytest.mark.parametrize(
    "body",
    [
        (
            "<h1>The following verbs not found in A Syriac Lexicon have citations in the "
            "database. Click the link to see the full entry.</h1><ul><li>"
            '<a href="https://example.org/oneentry.php?cits=all&amp;lemma=%29br+V">ˀbr vb.</a>'
            " D to make a son</li></ul>"
        ),
        (
            "<h1>The following verbs not found in A Syriac Lexicon have citations in the "
            "database. Click the link to see the full entry.</h1><ul><li>"
            '<a href="/oneentry.php?cits=all&amp;lemma=%29br+V&amp;lemma=gbl+V">ˀbr vb.</a>'
            " D to make a son</li></ul>"
        ),
        (
            "<h1>The following verbs not found in A Syriac Lexicon have citations in the "
            "database. Click the link to see the full entry.</h1><ul>"
            '<li><a href="/oneentry.php?cits=all&amp;lemma=%29br+V">ˀbr vb.</a> first</li>'
            '<li><a href="/oneentry.php?cits=all&amp;lemma=%29br+V">ˀbr vb.</a> duplicate</li>'
            "</ul>"
        ),
        (
            "<h1>The following verbs not found in A Syriac Lexicon have citations in the "
            "database. Click the link to see the full entry.</h1><p>no list rows</p>"
        ),
    ],
)
def test_missing_words_reject_malformed_links_duplicates_and_incomplete_pages(body: str) -> None:
    with pytest.raises(SyriacParseError):
        parse_syriac_missing_words_page(
            _inline_response(body, "https://cal.huc.edu/display_missing_verbs.php"),
            category="verbs",
        )


def test_peshitta_parallel_preserves_unicode_label_and_chapter_link() -> None:
    page = parse_syriac_peshitta_page(
        _fixture_response(
            "syriac_peshitta_gen_1_1.html",
            "https://cal.huc.edu/showpesh.php",
        ),
        book="Gen",
        chapter=1,
        verse=1,
    )

    assert page.status is SyriacPeshittaStatus.FOUND
    assert page.mt_text is not None and "בְּרֵאשִׁית" in page.mt_text
    assert page.peshitta_label == "Peshitta:"
    assert page.peshitta_text == "ܒܪܫܝܬ ܒܪܐ ܐܠܗܐܲ ܝܬ ܫܡܝܐ ܘܝܬ ܐܪܥܐܲ"
    assert page.peshitta_url == (
        "https://cal.huc.edu/get_a_chapter.php?file=62001&sub=01&cset=U"
    )


def test_peshitta_explicit_coordinate_error_is_typed_not_found() -> None:
    page = parse_syriac_peshitta_page(
        _fixture_response(
            "syriac_peshitta_not_found.html",
            "https://cal.huc.edu/showpesh.php",
        ),
        book="Gen",
        chapter=1,
        verse=99,
    )

    assert page.status is SyriacPeshittaStatus.NOT_FOUND
    assert page.mt_text is None
    assert page.peshitta_text is None
    assert page.peshitta_url is None


@pytest.mark.parametrize(
    "body",
    [
        (
            "<center>MT and Peshitta for Exod 1:1</center>"
            '<span class="heb">MT</span><a href="/get_a_chapter.php?file=62001">Peshitta:</a>'
            '<span class="syr">ܒܪܫܝܬ</span>'
        ),
        (
            "<center>MT and Peshitta for Gen 1:1</center>error in coord"
            '<span class="heb">MT</span><a href="/get_a_chapter.php?file=62001">Peshitta:</a>'
            '<span class="syr">ܒܪܫܝܬ</span>'
        ),
        "<center>MT and Peshitta for Gen 1:1</center><p>changed markup</p>",
        (
            "<center>MT and Peshitta for Gen 1:1</center>"
            '<span class="heb">MT</span><a href="https://example.org/get_a_chapter.php?file=62001">'
            'Peshitta:</a><span class="syr">ܒܪܫܝܬ</span>'
        ),
        (
            "<center>MT and Peshitta for Gen 1:1</center>"
            '<span class="heb">MT</span><a href="/unexpected.php?file=62001">Peshitta:</a>'
            '<span class="syr">ܒܪܫܝܬ</span>'
        ),
    ],
)
def test_peshitta_rejects_reference_contradiction_incomplete_or_bad_links(body: str) -> None:
    with pytest.raises(SyriacParseError):
        parse_syriac_peshitta_page(
            _inline_response(body, "https://cal.huc.edu/showpesh.php"),
            book="Gen",
            chapter=1,
            verse=1,
        )


@pytest.mark.parametrize(
    ("parser", "body", "kwargs", "url"),
    [
        (
            parse_syriac_text_category_page,
            "<style><h1>METRICAL HOMILIES AND HYMNS</h1></style>"
            "<h1>METRICAL HOMILIES AND HYMNS</h1><p>changed</p>",
            {"category": "metrical-homilies-hymns"},
            "https://cal.huc.edu/show_Syriac_categories.php?category=6",
        ),
        (
            parse_syriac_missing_words_page,
            "<script>The following verbs not found in A Syriac Lexicon have citations in the "
            "database.</script><p>changed</p>",
            {"category": "verbs"},
            "https://cal.huc.edu/display_missing_verbs.php",
        ),
        (
            parse_syriac_peshitta_page,
            "<style>error in coord</style><center>MT and Peshitta for Gen 1:1</center>"
            '<span class="heb">MT</span><a href="/get_a_chapter.php?file=62001">Peshitta:</a>'
            '<span class="syr">ܒܪܫܝܬ</span>',
            {"book": "Gen", "chapter": 1, "verse": 1},
            "https://cal.huc.edu/showpesh.php",
        ),
    ],
)
def test_non_rendered_content_cannot_supply_or_poison_semantic_markers(
    parser: object,
    body: str,
    kwargs: dict[str, object],
    url: str,
) -> None:
    if parser is parse_syriac_peshitta_page:
        page = parse_syriac_peshitta_page(_inline_response(body, url), **kwargs)  # type: ignore[arg-type]
        assert page.status is SyriacPeshittaStatus.FOUND
    else:
        with pytest.raises(SyriacParseError):
            parser(_inline_response(body, url), **kwargs)  # type: ignore[operator]


@pytest.mark.parametrize(
    ("parser", "body", "kwargs", "url"),
    [
        (
            parse_syriac_text_category_page,
            "<h1>METRICAL HOMILIES AND HYMNS</h1><style>unclosed",
            {"category": "metrical-homilies-hymns"},
            "https://cal.huc.edu/show_Syriac_categories.php?category=6",
        ),
        (
            parse_syriac_missing_words_page,
            "<h1>The following verbs not found in A Syriac Lexicon have citations in the "
            "database.</h1><script>unclosed",
            {"category": "verbs"},
            "https://cal.huc.edu/display_missing_verbs.php",
        ),
        (
            parse_syriac_peshitta_page,
            "<center>MT and Peshitta for Gen 1:1</center><style>unclosed",
            {"book": "Gen", "chapter": 1, "verse": 1},
            "https://cal.huc.edu/showpesh.php",
        ),
    ],
)
def test_unclosed_ignored_subtrees_fail_closed(
    parser: object,
    body: str,
    kwargs: dict[str, object],
    url: str,
) -> None:
    with pytest.raises(SyriacParseError):
        parser(_inline_response(body, url), **kwargs)  # type: ignore[operator]


class RecordingTransport:
    def __init__(self, responses: dict[str, CalResponse]) -> None:
        self.responses = responses
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.responses[request.path]


def _service() -> tuple[SyriacService, RecordingTransport]:
    transport = RecordingTransport(
        {
            "show_Syriac_categories.php": _fixture_response(
                "syriac_category_metrical.html",
                "https://cal.huc.edu/show_Syriac_categories.php?category=6",
            ),
            "display_missing_verbs.php": _fixture_response(
                "syriac_missing_verbs.html",
                "https://cal.huc.edu/display_missing_verbs.php",
            ),
            "showpesh.php": _fixture_response(
                "syriac_peshitta_gen_1_1.html",
                "https://cal.huc.edu/showpesh.php",
            ),
        }
    )
    return SyriacService(CalHttpClient(transport=transport)), transport


@pytest.mark.anyio
async def test_services_issue_exactly_one_request_each_and_preserve_provenance() -> None:
    service, transport = _service()

    texts = await service.texts("metrical-homilies-hymns")
    missing = await service.missing_words("verbs")
    peshitta = await service.peshitta_parallel("Gen", 1, 1)

    assert len(texts.items) == 3
    assert len(missing.items) == 3
    assert peshitta.status is SyriacPeshittaStatus.FOUND
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="show_Syriac_categories.php",
            params=(("category", "6"),),
        ),
        CalRequest(method="GET", path="display_missing_verbs.php"),
        CalRequest(
            method="POST",
            path="showpesh.php",
            data=(("bookname", "01"), ("chapter", "01"), ("verse", "01")),
        ),
    ]
    assert texts.provenance.operation == "syriac_texts"
    assert texts.provenance.category == "metrical-homilies-hymns"
    assert missing.provenance.operation == "syriac_missing_words"
    assert missing.provenance.category == "verbs"
    assert peshitta.provenance.operation == "syriac_peshitta_parallel"
    assert peshitta.provenance.book == "Gen"
    assert peshitta.provenance.book_id == "01"
    assert peshitta.provenance.chapter == 1
    assert peshitta.provenance.verse == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("texts", ("not-a-category",)),
        ("missing_words", ("not-a-category",)),
        ("peshitta_parallel", ("Genesis", 1, 1)),
        ("peshitta_parallel", ("Gen", 0, 1)),
        ("peshitta_parallel", ("Gen", 1, 0)),
        ("peshitta_parallel", ("Gen", 1000, 1)),
        ("peshitta_parallel", ("Gen", 1, 1000)),
    ],
)
async def test_invalid_public_inputs_fail_before_transport(method: str, args: tuple[object, ...]) -> None:
    service, transport = _service()

    with pytest.raises(ValueError):
        await getattr(service, method)(*args)

    assert transport.requests == []
