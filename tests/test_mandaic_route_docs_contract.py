from pathlib import Path


TEXTS_DOC = Path(__file__).parents[1] / "docs" / "tools" / "texts.md"


def test_mandaic_route_docs_treat_74_prefix_as_collection_boundary_only() -> None:
    text = TEXTS_DOC.read_text(encoding="utf-8")

    assert "The `74` prefix identifies only the Mandaic collection boundary" in text
    assert "known subdivided files" in text
    assert "direct" in text
