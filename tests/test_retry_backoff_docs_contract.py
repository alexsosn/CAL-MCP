from pathlib import Path


def test_retry_backoff_documentation_states_absolute_per_sleep_cap() -> None:
    configuration = (Path(__file__).parents[1] / "docs" / "configuration.md").read_text()

    assert "capped at 1 second per retry sleep" in configuration
    assert "min(base * 2**attempt, 1.0)" in configuration
