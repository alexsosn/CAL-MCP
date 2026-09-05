from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.dictionary_collation import (
    DictionaryCollationParseError,
    parse_dictionary_collation_page,
)


# Re-established against current main after the issue-14 branch integration: the
# parser must reject a nested semantic result container rather than duplicate rows.
def test_nested_duplicate_summary_card_fails_closed() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/searchdicts.php",
        body=b"""
        <html>
          <head><title>CAL: entries for page 705 of Jastrow</title></head>
          <body>
            <div class="summary-card">
              <div class="summary-card">
                <p><a href="oneentry.php?lemma=br+N">br N</a> : son</p>
              </div>
            </div>
          </body>
        </html>
        """,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )

    with pytest.raises(DictionaryCollationParseError, match="summary card"):
        parse_dictionary_collation_page(response)
