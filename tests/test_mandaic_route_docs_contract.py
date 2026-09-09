def test_mandaic_route_docs_treat_74_prefix_as_collection_boundary_only() -> None:
    with open("docs/tools/texts.md", encoding="utf-8") as handle:
        text = handle.read()

    assert "The `74` prefix identifies only the Mandaic collection boundary" in text
    assert "known subdivided files" in text
    assert "direct" in text
