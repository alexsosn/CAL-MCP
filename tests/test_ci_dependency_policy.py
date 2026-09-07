from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_CONSTRAINTS = ROOT / "constraints" / "ci-py311.txt"
BUILD_CONSTRAINTS = ROOT / "constraints" / "build-py311.txt"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
TESTING_GUIDE = ROOT / "wiki" / "testing.md"


def _constraint_names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        assert "==" in line, f"constraint must be an exact pin: {line!r}"
        name, version = line.split("==", 1)
        assert name and version and not any(char in version for char in "<>=~!")
        names.add(name.casefold().replace("_", "-"))
    return names


def test_python311_target_and_build_constraints_are_committed_and_complete() -> None:
    assert TARGET_CONSTRAINTS.exists()
    assert BUILD_CONSTRAINTS.exists()

    target_names = _constraint_names(TARGET_CONSTRAINTS)
    assert {
        "httpx2",
        "mcp",
        "build",
        "mypy",
        "pytest",
        "ruff",
        "anyio",
        "pydantic",
        "jsonschema",
        "cryptography",
    } <= target_names

    build_names = _constraint_names(BUILD_CONSTRAINTS)
    assert {
        "hatchling",
        "editables",
        "packaging",
        "pathspec",
        "pluggy",
        "tomlkit",
        "trove-classifiers",
    } <= build_names


def test_primary_ci_uses_frozen_target_and_build_constraints() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "deterministic:" in workflow
    assert 'python-version: "3.11"' in workflow
    assert "pip==26.2.1" in workflow
    assert "setuptools==79.0.1" in workflow
    assert "-c constraints/ci-py311.txt" in workflow
    assert "--build-constraint constraints/build-py311.txt" in workflow
    assert "pip freeze --all" in workflow
    assert "pip check" in workflow
    assert "ruff check ." in workflow
    assert "ruff format --check ." in workflow
    assert "mypy" in workflow
    assert "pytest" in workflow


def test_latest_compatible_ci_is_explicitly_unconstrained() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    marker = "latest-compatible:"
    assert marker in workflow
    latest = workflow.split(marker, 1)[1]

    assert 'python-version: "3.11"' in latest
    assert 'python -m pip install -e ".[dev]"' in latest
    assert "constraints/ci-py311.txt" not in latest
    assert "constraints/build-py311.txt" not in latest
    assert "pip freeze --all" in latest
    assert "pip check" in latest
    assert "ruff check ." in latest
    assert "ruff format --check ." in latest
    assert "mypy" in latest
    assert "pytest" in latest


def test_release_build_validation_consumes_deterministic_constraints() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    build_job = workflow.split("build-and-test:", 1)[1].split("live-smoke:", 1)[0]

    assert "pip==26.2.1" in build_job
    assert "setuptools==79.0.1" in build_job
    assert "-c constraints/ci-py311.txt" in build_job
    assert "--build-constraint constraints/build-py311.txt" in build_job
    assert "pip freeze --all" in build_job
    assert "pip check" in build_job


def test_testing_guide_documents_reviewable_constraint_refresh() -> None:
    guide = TESTING_GUIDE.read_text(encoding="utf-8")

    assert "constraints/ci-py311.txt" in guide
    assert "constraints/build-py311.txt" in guide
    assert "latest-compatible" in guide
    assert "pyproject.toml" in guide
    assert "pip freeze --all" in guide
    assert "review" in guide.casefold()
