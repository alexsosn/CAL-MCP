from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.dictionary_collation import (
    DictionaryCollationParseError,
    parse_dictionary_collation_page,
)


def test_invalid_returned_lemma_key_fails_closed() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/searchdicts.php",
        body=b"""
        <html>
          <head><title>CAL: entries for page 705 of Jastrow</title></head>
          <body>
            <div class="summary-card">
              <p><a href="oneentry.php?lemma=not-a-structural-key">not-a-key</a> : gloss</p>
            </div>
          </body>
        </html>
        """,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )

    with pytest.raises(DictionaryCollationParseError, match="lemma key"):
        parse_dictionary_collation_page(response)
