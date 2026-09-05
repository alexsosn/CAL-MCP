from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.dictionary_collation import (
    DictionaryCollationParseError,
    DictionaryCollationService,
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


@pytest.mark.anyio
async def test_qumran_source_uses_current_cal_dictionary_label() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/searchdicts.php",
            body=b"""
            <html>
              <head>
                <title>CAL: entries for page 99999 of Dictionary of Qumran Aramaic</title>
              </head>
              <body>
                <div class="summary-card">
                  <p class="red">No data available for that page.</p>
                </div>
              </body>
            </html>
            """,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
        )

    result = await DictionaryCollationService(CalHttpClient(transport=transport)).collate(
        "qumran_aramaic", "99999"
    )

    assert requests == [
        CalRequest(
            method="POST",
            path="searchdicts.php",
            data=(("dict", "Q"), ("page", "99999")),
        )
    ]
    assert result.source_label == "Dictionary of Qumran Aramaic"
    assert result.entries == ()
