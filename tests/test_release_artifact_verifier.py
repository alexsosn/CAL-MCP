from __future__ import annotations

import importlib.util
import io
import sys
import tarfile
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts" / "verify_release_artifact.py"


def _load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("cal_mcp_release_verifier_test", VERIFIER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_wheel(dist_dir: Path, *, version: str = "0.1.0", name: str = "cal-mcp") -> Path:
    wheel = dist_dir / f"cal_mcp-{version}-py3-none-any.whl"
    metadata = f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n\n"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"cal_mcp-{version}.dist-info/METADATA", metadata)
    return wheel


def _add_tar_file(archive: tarfile.TarFile, path: str, content: str) -> None:
    payload = content.encode("utf-8")
    info = tarfile.TarInfo(path)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


def _write_sdist(
    dist_dir: Path,
    *,
    filename_version: str = "0.1.0",
    metadata_version: str = "0.1.0",
    name: str = "cal-mcp",
    duplicate_pkg_info_symlink: bool = False,
) -> Path:
    sdist = dist_dir / f"cal_mcp-{filename_version}.tar.gz"
    root = f"cal_mcp-{filename_version}"
    pkg_info_path = f"{root}/PKG-INFO"
    pkg_info = f"Metadata-Version: 2.4\nName: {name}\nVersion: {metadata_version}\n\n"
    pyproject = (
        '[build-system]\nrequires = ["hatchling>=1.27"]\nbuild-backend = "hatchling.build"\n'
    )
    with tarfile.open(sdist, "w:gz") as archive:
        _add_tar_file(archive, pkg_info_path, pkg_info)
        if duplicate_pkg_info_symlink:
            duplicate = tarfile.TarInfo(pkg_info_path)
            duplicate.type = tarfile.SYMTYPE
            duplicate.linkname = "elsewhere"
            archive.addfile(duplicate)
        _add_tar_file(archive, f"{root}/pyproject.toml", pyproject)
    return sdist


def test_release_verifier_frozen_tool_surface_matches_current_public_tools() -> None:
    module = _load_verifier()

    assert module.EXPECTED_TOOL_COUNT == 29
    assert len(module.EXPECTED_TOOLS) == module.EXPECTED_TOOL_COUNT
    assert {
        "cal_convert_to_code",
        "cal_gloss_field",
        "cal_text_information",
    } <= module.EXPECTED_TOOLS


def test_distribution_discovery_rejects_sdist_embedded_version_mismatch(tmp_path: Path) -> None:
    module = _load_verifier()
    _write_wheel(tmp_path)
    _write_sdist(tmp_path, metadata_version="9.9.9")

    with pytest.raises(RuntimeError, match="sdist.*version|source.*version"):
        module._find_distributions(tmp_path)


def test_distribution_discovery_rejects_duplicate_sdist_pkg_info_path(tmp_path: Path) -> None:
    module = _load_verifier()
    _write_wheel(tmp_path)
    _write_sdist(tmp_path, duplicate_pkg_info_symlink=True)

    with pytest.raises(RuntimeError, match="one root sdist PKG-INFO"):
        module._find_distributions(tmp_path)


def test_release_verifier_installs_wheel_and_sdist_independently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_verifier()
    wheel = _write_wheel(tmp_path)
    sdist = _write_sdist(tmp_path)
    created_envs: list[Path] = []
    install_targets: list[Path] = []
    stdio_checks: list[tuple[str, Path]] = []

    class FakeEnvBuilder:
        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def create(self, env_dir: Path) -> None:
            created_envs.append(Path(env_dir))

    def fake_run(command: list[str], **kwargs: Any) -> None:
        assert kwargs["check"] is True
        install_targets.append(Path(command[-1]))

    def fake_venv_paths(root: Path) -> tuple[Path, Path]:
        del root
        executable = Path(sys.executable)
        return executable, executable

    async def fake_verify_stdio(executable: Path, expected_version: str, cwd: Path) -> None:
        assert executable == Path(sys.executable)
        stdio_checks.append((expected_version, Path(cwd)))

    monkeypatch.setattr(module.venv, "EnvBuilder", FakeEnvBuilder)
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "_venv_paths", fake_venv_paths)
    monkeypatch.setattr(module, "_verify_stdio", fake_verify_stdio)

    assert module.verify_release_artifact(tmp_path, tag="v0.1.0") == "0.1.0"
    assert install_targets == [wheel.resolve(), sdist.resolve()]
    assert len(created_envs) == 2
    assert created_envs[0] != created_envs[1]
    assert [version for version, _cwd in stdio_checks] == ["0.1.0", "0.1.0"]
    assert stdio_checks[0][1] != stdio_checks[1][1]
