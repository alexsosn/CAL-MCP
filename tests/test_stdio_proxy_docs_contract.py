"""Offline documentation contract for issue #160 (stdio proxy environments)."""

from __future__ import annotations

from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
INSTALLATION = DOCS / "installation.md"
STANDALONE = DOCS / "integrations" / "standalone-mcp.md"


@pytest.mark.parametrize("guide", [INSTALLATION, STANDALONE], ids=["install", "standalone"])
def test_stdio_proxy_troubleshooting_is_documented_in_both_guides(guide: Path) -> None:
    text = guide.read_text(encoding="utf-8")

    for name in ("HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR"):
        assert f"`{name}`" in text, (guide.name, name)
    assert "403" in text
    assert "StdioServerParameters" in text
    assert "env=" in text
    assert "cal.huc.edu" in text
    assert "not every 403" in text.lower()


def test_standalone_guide_shows_explicit_python_sdk_environment_forwarding() -> None:
    text = STANDALONE.read_text(encoding="utf-8")

    assert "from mcp import Client, StdioServerParameters" in text
    assert "env=os.environ.copy()" in text
    assert 'command="cal-mcp"' in text
    assert "await client.list_tools()" in text
    assert "asyncio.run(main())" in text
