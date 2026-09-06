from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import tempfile
import venv
import zipfile
from email.parser import Parser
from pathlib import Path

from mcp import Client, StdioServerParameters

EXPECTED_TOOL_COUNT = 26
EXPECTED_TOOLS = frozenset(
    {
        "cal_lexicon_lookup",
        "cal_gloss_search",
        "cal_citation_text_search",
        "cal_text_catalogue",
        "cal_text_search",
        "cal_text_page",
        "cal_token_analysis",
        "cal_text_concordance",
        "cal_kwic_texts",
        "cal_kwic_dialects",
        "cal_kwic_dialect",
        "cal_bibliography_authors",
        "cal_bibliography_author",
        "cal_bibliography_keyword",
        "cal_bibliography_lemma",
        "cal_dictionary_collation",
        "cal_targum_parallel",
        "cal_targum_concordance",
        "cal_targum_hebrew_lemmas",
        "cal_targum_hebrew_reflexes",
        "cal_external_citation_dialects",
        "cal_external_citation_sources",
        "cal_external_citations",
        "cal_syriac_texts",
        "cal_syriac_missing_words",
        "cal_syriac_peshitta_parallel",
    }
)


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
                "installed MCP server version does not match wheel metadata: "
                f"{client.server_info.version!r} != {expected_version!r}"
            )
        tool_names = {tool.name for tool in (await client.list_tools()).tools}
        if len(tool_names) != EXPECTED_TOOL_COUNT or tool_names != EXPECTED_TOOLS:
            missing = sorted(EXPECTED_TOOLS - tool_names)
            extra = sorted(tool_names - EXPECTED_TOOLS)
            raise RuntimeError(
                f"installed MCP schema mismatch: missing={missing!r} extra={extra!r}"
            )


def verify_release_artifact(dist_dir: Path, *, tag: str | None = None) -> str:
    wheel, _sdist, version = _find_distributions(dist_dir)
    if tag is not None:
        normalized_tag = tag.removeprefix("v")
        if normalized_tag != version:
            raise RuntimeError(
                f"release tag {tag!r} does not match distribution version {version!r}"
            )

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
                str(wheel.resolve()),
            ],
            cwd=root,
            check=True,
        )
        if not cal_mcp_executable.is_file():
            raise RuntimeError(f"installed console script not found at {cal_mcp_executable}")
        asyncio.run(_verify_stdio(cal_mcp_executable, version, root))
    return version


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify built CAL-MCP release distributions")
    parser.add_argument("dist_dir", type=Path, help="directory containing one wheel and one sdist")
    parser.add_argument("--tag", help="optional release tag that must match wheel metadata")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    version = verify_release_artifact(args.dist_dir, tag=args.tag)
    print(f"verified cal-mcp {version} wheel/sdist and installed stdio MCP surface")


if __name__ == "__main__":
    main()
