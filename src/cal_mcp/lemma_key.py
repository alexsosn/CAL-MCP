from __future__ import annotations

import re

from cal_mcp.normalization import InputRepresentation, normalize_query

_SUFFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]{0,7}$")


def validate_lemma_key(value: str) -> tuple[str, str, str]:
    """Validate and canonicalize one structural CAL lemma key."""

    if not isinstance(value, str):
        raise ValueError("lemma_key must be a string")
    candidate = value.strip(" ")
    if any(char.isspace() and char != " " for char in candidate):
        raise ValueError("lemma_key may contain only ASCII spaces")
    if candidate.count(" ") != 1:
        raise ValueError("lemma_key must contain one CAL lemma and one key suffix")
    lemma, suffix = candidate.rsplit(" ", 1)
    if not lemma or " " in lemma or _SUFFIX_RE.fullmatch(suffix) is None:
        raise ValueError("lemma_key has an invalid CAL lemma/key-suffix structure")

    base_lemma = lemma
    if "#" in lemma:
        base_lemma, homograph = lemma.rsplit("#", 1)
        if (
            not base_lemma
            or "#" in base_lemma
            or not homograph.isascii()
            or not homograph.isdecimal()
            or homograph.startswith("0")
        ):
            raise ValueError("lemma_key has an invalid CAL homograph suffix")
    normalize_query(base_lemma, representation=InputRepresentation.CAL_CODE)
    return lemma, suffix, f"{lemma} {suffix}"


__all__ = ["validate_lemma_key"]
