"""Offline adversarial acceptance contract for CAL external source positive probe."""

import importlib
from types import SimpleNamespace


def _module():
    return importlib.import_module("cal_mcp.external_citations_diagnostic")


def _result(*rows: tuple[str, str], dialect: str = "6"):
    return SimpleNamespace(
        dialect_id=dialect,
        sources=tuple(SimpleNamespace(abbreviation=a, citations_url=url) for a, url in rows),
    )


_GOOD_URL = "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar"


def test_choose_candidate_from_returned_current_sources_only() -> None:
    module = _module()
    historical = ("1CorH", "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH")
    assert module.choose_candidate(_result(historical, ("EbPar", _GOOD_URL))) == "EbPar"
    assert module.choose_candidate(_result(historical)) is None
    assert module.choose_candidate(_result(("EbPar", _GOOD_URL), dialect="8")) is None


def test_reject_ambiguous_or_foreign_source_navigation() -> None:
    module = _module()
    invalid = (
        "https://example.org/displaycits.abbrev.php?abbrev=EbPar",
        "http://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar&extra=1",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar&abbrev=1CorH",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=1CorH",
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar#fragment",
    )
    for link in invalid:
        assert module.choose_candidate(_result(("EbPar", link))) is None
        assert module.choose_candidate(_result(("EbPar", _GOOD_URL), ("EbPar", link))) is None


def test_identical_duplicate_abbrev_rows_remain_a_single_valid_target() -> None:
    module = _module()
    assert module.choose_candidate(_result(("EbPar", _GOOD_URL), ("EbPar", _GOOD_URL))) == "EbPar"


def test_only_real_positive_citation_count_is_acceptance() -> None:
    module = _module()

    def response(total: int, hits: int, source: str = "EbPar"):
        return SimpleNamespace(
            source_abbrev=source,
            total=total,
            citations=tuple(SimpleNamespace(reference="synthetic") for _ in range(hits)),
        )

    assert module.is_positive(response(1, 1), "EbPar")
    assert not module.is_positive(response(0, 0), "EbPar")
    assert not module.is_positive(response(2, 1), "EbPar")
    assert not module.is_positive(response(1, 1, "JS"), "EbPar")
    assert not module.is_positive(response(0, 1), "EbPar")


def test_three_request_mode_requires_actual_syrian_dialect_identity() -> None:
    module = _module()

    def response(*items: tuple[str, str]):
        return SimpleNamespace(
            dialects=tuple(
                SimpleNamespace(dialect_id=identity, label=label)
                for identity, label in items
            )
        )

    assert module.choose_syriac_dialect(response(("6", "Syriac"))) == "6"
    assert module.choose_syriac_dialect(response(("4", "Mandaic"), ("6", "Syriac"))) == "6"
    assert module.choose_syriac_dialect(response(("6", "Other"))) is None
    assert module.choose_syriac_dialect(response(("6", "Syriac"), ("6", "Syriac"))) is None
    assert module.choose_syriac_dialect(response(("06", "Syriac"))) is None
    assert module.choose_syriac_dialect(response()) is None
