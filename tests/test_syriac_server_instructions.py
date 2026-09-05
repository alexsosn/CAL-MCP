from __future__ import annotations

from pathlib import Path


def test_server_instructions_route_syriac_studies_tools() -> None:
    """Keep top-level MCP routing aligned with the registered Syriac tool surface."""

    source = Path("src/cal_mcp/server.py").read_text(encoding="utf-8")
    instructions = source.split("instructions=(", 1)[1].split("version=__version__", 1)[0]

    assert "cal_syriac_texts" in instructions
    assert "cal_syriac_missing_words" in instructions
    assert "cal_syriac_peshitta_parallel" in instructions
    assert "external/non-online-text citations" in instructions
    assert "cal_text_page" in instructions
    assert "cal_lexicon_lookup" in instructions
