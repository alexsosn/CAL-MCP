from __future__ import annotations

import re

_SUBTEXT_ID_RE = re.compile(r"^[0-9]+[a-z]?$")


def is_cal_subtext_id(value: object) -> bool:
    """Return whether value matches CAL's researched public subtext-ID grammar."""

    return isinstance(value, str) and _SUBTEXT_ID_RE.fullmatch(value) is not None


def has_subtext_letter_suffix(value: str) -> bool:
    """Return whether an already validated CAL subtext ID ends in a lowercase ASCII letter."""

    return bool(value) and "a" <= value[-1] <= "z"


__all__ = ["has_subtext_letter_suffix", "is_cal_subtext_id"]
