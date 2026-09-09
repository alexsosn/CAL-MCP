from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_syriac_docs_explain_peshitta_catalogue_navigation_composition() -> None:
    docs = (ROOT / "docs" / "tools" / "syriac.md").read_text(encoding="utf-8")

    assert "`navigation_kind`" in docs
    assert "`catalogue`" in docs
    assert "`text`" in docs
    assert "`group`" in docs
    assert 'cal_text_catalogue(category_id="62001")' in docs
    assert 'cal_text_page(file_id="62001", subtext_id="01")' in docs
    assert "62040" in docs
    assert "no chapter" in docs.lower() or "chapter prefetch" in docs.lower()


def test_durable_research_records_current_peshitta_subtext_route_correction() -> None:
    research = (ROOT / "research.md").read_text(encoding="utf-8")

    assert "62001" in research
    assert "showsubtexts.php" in research
    assert "subtext" in research
    assert "Peshitta" in research
