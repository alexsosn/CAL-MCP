from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import tarfile
import tempfile
import venv
import zipfile
from email.parser import Parser
from pathlib import Path, PurePosixPath

from mcp import Client, StdioServerParameters

from cal_mcp.release_surface import V01_PUBLIC_TOOLS


def _distribution_version(wheel: Path) -> str:
    with zipfile.ZipFile(wheel) as archive:
        metadata_paths = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_paths) != 1:
            raise RuntimeError(f"expected one wheel METADATA file, found {metadata_paths!r}")
        metadata = Parser().parsestr(archive.read(metadata_paths[0]).decode("utf-8"))
    name = metadata.get("Name")
    version = metadata.get("Version")
    if name != "cal-mcp" or not version:
        raise RuntimeError(f"unexpected distribution metadata: Name={name!r} Version={version!r}")
    return version


def _sdist_version(sdist: Path, expected_version: str) -> str:
    expected_root = sdist.name.removesuffix(".tar.gz")
    try:
        with tarfile.open(sdist, "r:gz") as archive:
            members = archive.getmembers()
            paths: list[PurePosixPath] = []
            for member in members:
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or not path.parts:
                    raise RuntimeError(f"sdist contains unsafe member path {member.name!r}")
                paths.append(path)

            roots = {path.parts[0] for path in paths}
            if roots != {expected_root}:
                raise RuntimeError(
                    f"sdist root mismatch: expected {expected_root!r}, found {sorted(roots)!r}"
                )

            pkg_info_path = PurePosixPath(expected_root, "PKG-INFO")
            pyproject_path = PurePosixPath(expected_root, "pyproject.toml")
            pkg_info_members = [
                member for member, path in zip(members, paths, strict=True) if path == pkg_info_path
            ]
            pyproject_members = [
                member
                for member, path in zip(members, paths, strict=True)
                if path == pyproject_path
            ]
            if len(pkg_info_members) != 1:
                raise RuntimeError(
                    f"expected one root sdist PKG-INFO file, found {len(pkg_info_members)}"
                )
            if not pkg_info_members[0].isfile():
                raise RuntimeError("root sdist PKG-INFO is not a regular file")
            if len(pyproject_members) != 1:
                raise RuntimeError(
                    f"expected one root sdist pyproject.toml file, found {len(pyproject_members)}"
                )
            if not pyproject_members[0].isfile():
                raise RuntimeError("root sdist pyproject.toml is not a regular file")

            metadata_file = archive.extractfile(pkg_info_members[0])
            if metadata_file is None:
                raise RuntimeError("could not read root sdist PKG-INFO")
            metadata = Parser().parsestr(metadata_file.read().decode("utf-8"))
    except RuntimeError:
        raise
    except (OSError, tarfile.TarError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"could not read sdist {sdist.name!r}: {exc}") from exc

    name = metadata.get("Name")
    version = metadata.get("Version")
    if name != "cal-mcp":
        raise RuntimeError(f"unexpected sdist metadata name: {name!r}")
    if version != expected_version:
        raise RuntimeError(
            f"sdist metadata version {version!r} does not match wheel version {expected_version!r}"
        )
    return expected_version


def _find_distributions(dist_dir: Path) -> tuple[Path, Path, str]:
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError(
            f"expected exactly one wheel and one sdist in {dist_dir}, "
            f"found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)"
        )
    version = _distribution_version(wheels[0])
    expected_sdist = f"cal_mcp-{version}.tar.gz"
    if sdists[0].name != expected_sdist:
        raise RuntimeError(
            f"sdist {sdists[0].name!r} does not match wheel version; expected {expected_sdist!r}"
        )
    _sdist_version(sdists[0], version)
    return wheels[0], sdists[0], version


def _venv_paths(root: Path) -> tuple[Path, Path]:
    if os.name == "nt":
        return root / "Scripts" / "python.exe", root / "Scripts" / "cal-mcp.exe"
    return root / "bin" / "python", root / "bin" / "cal-mcp"


async def _verify_stdio(executable: Path, expected_version: str, cwd: Path) -> None:
    parameters = StdioServerParameters(command=str(executable), cwd=str(cwd))
    async with Client(parameters) as client:
        if client.server_info is None:
            raise RuntimeError("installed cal-mcp returned no MCP server information")
        if client.server_info.name != "cal-mcp":
            raise RuntimeError(f"unexpected MCP server name {client.server_info.name!r}")
        if client.server_info.version != expected_version:
            raise RuntimeError(
                "installed MCP server version does not match distribution metadata: "
                f"{client.server_info.version!r} != {expected_version!r}"
            )
        tool_names = frozenset(tool.name for tool in (await client.list_tools()).tools)
        if tool_names != V01_PUBLIC_TOOLS:
            missing = sorted(V01_PUBLIC_TOOLS - tool_names)
            extra = sorted(tool_names - V01_PUBLIC_TOOLS)
            raise RuntimeError(
                f"installed MCP schema mismatch: missing={missing!r} extra={extra!r}"
            )


def _verify_installable_distribution(distribution: Path, expected_version: str) -> None:
    with tempfile.TemporaryDirectory(prefix="cal-mcp-release-") as temporary:
        root = Path(temporary)
        venv_dir = root / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        python_executable, cal_mcp_executable = _venv_paths(venv_dir)
        subprocess.run(
            [
                str(python_executable),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",
                str(distribution.resolve()),
            ],
            cwd=root,
            check=True,
        )
        if not cal_mcp_executable.is_file():
            raise RuntimeError(f"installed console script not found at {cal_mcp_executable}")
        asyncio.run(_verify_stdio(cal_mcp_executable, expected_version, root))


def verify_release_artifact(dist_dir: Path, *, tag: str | None = None) -> str:
    wheel, sdist, version = _find_distributions(dist_dir)
    if tag is not None:
        normalized_tag = tag.removeprefix("v")
        if normalized_tag != version:
            raise RuntimeError(
                f"release tag {tag!r} does not match distribution version {version!r}"
            )

    _verify_installable_distribution(wheel, version)
    _verify_installable_distribution(sdist, version)
    return version


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify built CAL-MCP release distributions")
    parser.add_argument("dist_dir", type=Path, help="directory containing one wheel and one sdist")
    parser.add_argument("--tag", help="optional release tag that must match distribution metadata")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    version = verify_release_artifact(args.dist_dir, tag=args.tag)
    print(f"verified cal-mcp {version} wheel/sdist and installed stdio MCP surface")


if __name__ == "__main__":
    main()
