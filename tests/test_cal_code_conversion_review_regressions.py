from __future__ import annotations

import pytest

from cal_mcp.normalization import InputRepresentation, convert_to_cal_code


@pytest.mark.parametrize(
    "representation",
    [None, InputRepresentation.UNICODE_TRANSLITERATION],
)
def test_unicode_transliteration_underscore_separator_is_preserved(
    representation: InputRepresentation | None,
) -> None:
    result = convert_to_cal_code("š_mlk", representation=representation)

    assert result.representation is InputRepresentation.UNICODE_TRANSLITERATION
    assert result.words[0].candidates == ("$_mlk",)
