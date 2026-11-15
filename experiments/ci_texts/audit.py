"""Experimental, offline annotation audit. No CAL lookup or linguistic verification."""

import math
import re
import unicodedata
from collections.abc import Mapping
from typing import Any


class DraftAuditError(ValueError):
    """A pilot annotation is malformed or overclaims evidence."""


_END_PUNCTUATION = ".,!?;:܀"
_DRAFT_KEYS = {
    "dialect",
    "text",
    "known_lemma_keys",
    "tokens",
    "minimum_coverage",
    "max_new_lemmas",
    "evidence_status",
    "linguistic_review",
}


def _lemma_keys(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(key, str) and key and key == key.strip() for key in value
    ):
        raise DraftAuditError(f"{field} must be a list of nonblank lemma strings")
    if len(value) != len(set(value)):
        raise DraftAuditError(f"{field} has duplicate lemma keys")
    return value


def _surface_from_raw(raw: str) -> str:
    surface = raw.rstrip(_END_PUNCTUATION)
    # Classical Syriac letter blocks and optional vowels. No Roman/Hebrew text in this pilot.
    if not surface or not any(
        (0x0710 <= ord(char) <= 0x072F or 0x0860 <= ord(char) <= 0x086A)
        and unicodedata.category(char).startswith("L")
        for char in surface
    ):
        raise DraftAuditError("each running token needs a Syriac base letter")
    if any(
        not (0x0710 <= ord(char) <= 0x074F or 0x0860 <= ord(char) <= 0x086F) for char in surface
    ):
        raise DraftAuditError("unexpected script or punctuation inside running token")
    return surface


def audit_draft(draft: Mapping[str, Any]) -> dict[str, Any]:
    """Check *supplied annotations* only, never attestations or actual comprehension."""
    if not isinstance(draft, Mapping) or set(draft) != _DRAFT_KEYS:
        raise DraftAuditError("draft fields differ from the experimental contract")
    if draft["dialect"] != "Classical Syriac":
        raise DraftAuditError("the pilot accepts only Classical Syriac")
    if draft["evidence_status"] != "unverified" or draft["linguistic_review"] != "pending":
        raise DraftAuditError("the pilot cannot claim CAL or linguistic verification")
    text = draft["text"]
    if not isinstance(text, str) or not text.strip():
        raise DraftAuditError("a nonempty Syriac draft is required")
    minimum = draft["minimum_coverage"]
    if type(minimum) not in (int, float) or not math.isfinite(minimum) or not 0 <= minimum <= 1:
        raise DraftAuditError("minimum_coverage must be a finite fraction in [0, 1]")
    maximum = draft["max_new_lemmas"]
    if type(maximum) is not int or maximum < 0:
        raise DraftAuditError("max_new_lemmas must be a nonnegative integer")

    known = set(_lemma_keys(draft["known_lemma_keys"], "known_lemma_keys"))
    surfaces = [_surface_from_raw(raw) for raw in re.findall(r"\S+", text)]
    annotations = draft["tokens"]
    if not isinstance(annotations, list) or len(annotations) != len(surfaces):
        raise DraftAuditError("every running token requires exactly one annotation")

    novel: list[str] = []
    unknown = 0
    for position, (surface, annotation) in enumerate(zip(surfaces, annotations, strict=True)):
        if not isinstance(annotation, dict) or set(annotation) != {"surface", "lemma_keys"}:
            raise DraftAuditError(f"token {position}: malformed annotation")
        if annotation["surface"] != surface:
            raise DraftAuditError(f"token {position}: surface mismatch")
        keys = _lemma_keys(annotation["lemma_keys"], f"token {position} lemma_keys")
        if not keys:
            raise DraftAuditError(f"token {position}: no lemma keys")
        unseen = [key for key in keys if key not in known]
        if unseen:
            unknown += 1
        for key in unseen:
            if key not in novel:
                novel.append(key)

    total = len(surfaces)
    coverage = (total - unknown) / total
    return {
        "running_tokens": total,
        "known_tokens": total - unknown,
        "unknown_tokens": unknown,
        "coverage": coverage,
        "new_lemma_keys": novel,
        "passes_lexical_budget": coverage >= minimum and len(novel) <= maximum,
        "linguistically_verified": False,
    }
