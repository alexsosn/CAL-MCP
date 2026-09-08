from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"


def test_v01_release_notes_describe_implemented_dependency_validation() -> None:
    changelog = CHANGELOG.read_text(encoding="utf-8")

    assert "remains the separate non-blocking issue #18" not in changelog
    assert (
        "Deterministic CI and release validation use committed Python 3.11 target/build constraints"
        in changelog
    )
    assert (
        "a separate latest-compatible job checks the broad dependency ranges declared for "
        "downstream users"
        in changelog
    )
