from __future__ import annotations

import argparse
import re
from collections.abc import Mapping, Sequence
from importlib import metadata
from pathlib import Path

_CANONICALIZE_RE = re.compile(r"[-_.]+")


def canonicalize_name(name: str) -> str:
    return _CANONICALIZE_RE.sub("-", name).casefold()


def load_constraints(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ValueError(f"constraint is not an exact pin: {line!r}")
        raw_name, version = line.split("==", 1)
        name = canonicalize_name(raw_name.strip())
        version = version.strip()
        if not name or not version or any(char in version for char in "<>=~!"):
            raise ValueError(f"constraint is not an exact pin: {line!r}")
        if name in pins:
            raise ValueError(f"duplicate constraint for {name!r}")
        pins[name] = version
    if not pins:
        raise ValueError(f"constraint file {path} contains no pins")
    return pins


def compare_environment(
    constraints_path: Path,
    installed: Mapping[str, str],
    *,
    excluded_names: Sequence[str],
) -> list[str]:
    expected = load_constraints(constraints_path)
    excluded = {canonicalize_name(name) for name in excluded_names}
    actual = {
        canonicalize_name(name): version
        for name, version in installed.items()
        if canonicalize_name(name) not in excluded
    }

    problems: list[str] = []
    for name in sorted(expected.keys() - actual.keys()):
        problems.append(f"missing installed distribution: {name}=={expected[name]}")
    for name in sorted(actual.keys() - expected.keys()):
        problems.append(f"unexpected installed distribution: {name}=={actual[name]}")
    for name in sorted(expected.keys() & actual.keys()):
        if actual[name] != expected[name]:
            problems.append(
                f"version mismatch for {name}: installed {actual[name]!r}, "
                f"expected {expected[name]!r}"
            )
    return problems


def installed_environment() -> dict[str, str]:
    result: dict[str, str] = {}
    for distribution in metadata.distributions():
        name = distribution.metadata.get("Name")
        if not name:
            continue
        canonical = canonicalize_name(name)
        if canonical in result and result[canonical] != distribution.version:
            raise RuntimeError(
                f"multiple installed versions for {canonical!r}: "
                f"{result[canonical]!r} and {distribution.version!r}"
            )
        result[canonical] = distribution.version
    return result


def verify_environment(constraints_path: Path, *, excluded_names: Sequence[str]) -> None:
    problems = compare_environment(
        constraints_path,
        installed_environment(),
        excluded_names=excluded_names,
    )
    if problems:
        raise RuntimeError("CI environment does not match constraints:\n- " + "\n- ".join(problems))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that the installed CI environment exactly matches a constraints file"
    )
    parser.add_argument("constraints", type=Path)
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="installed distribution name intentionally outside the target constraint file",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    verify_environment(args.constraints, excluded_names=args.exclude)
    print(f"verified installed environment against {args.constraints}")


if __name__ == "__main__":
    main()
