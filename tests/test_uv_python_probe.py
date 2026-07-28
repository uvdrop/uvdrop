"""Python interpreter probing helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from uvdrop.uv_tool import find_project_python, probe_python_version


def test_probe_python_version_missing() -> None:
    assert probe_python_version(Path("Z:/no/such/python.exe")) is None


def test_find_project_python_prefers_venv(tmp_path: Path) -> None:
    venv = tmp_path / "env"
    scripts = venv / "Scripts"
    scripts.mkdir(parents=True)
    exe = scripts / "python.exe"
    exe.write_bytes(b"")

    with patch("uvdrop.uv_tool.probe_python_version", return_value="3.12.10"):
        path, ver = find_project_python(tmp_path / "proj", venv_dir=venv)
    assert path == str(exe)
    assert ver == "3.12.10"
