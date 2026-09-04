from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.token_analysis import TokenAnalysisParseError, parse_token_analysis_page


def test_truncated_second_analysis_is_parser_drift() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getlex.php?coord=7102601002203&word=0",
        body=b"""<html><body>
<div>Click on a headword to see a complete lexicon entry</div>
<div>w_ c</div>
<div><a href="oneentry.php?lemma=w_+c&amp;cits=all">w_ (wə_) conj. and, also</a></div>
<div>my c</div>
</body></html>""",
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
    )

    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(response)
