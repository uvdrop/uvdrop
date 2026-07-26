"""Tests for sample app generator."""

from __future__ import annotations

from pathlib import Path

from uvdrop.project import find_pyproject
from uvdrop.sample_app import list_samples, write_sample_tree, write_sample_zip


def test_list_samples() -> None:
    samples = list_samples()
    assert len(samples) == 2
    assert samples[0].id == "1"
    assert samples[1].id == "2"


def test_write_sample_tree(tmp_path: Path) -> None:
    root = write_sample_tree(tmp_path, sample_id="1")
    assert (root / "main.py").is_file()
    assert not (root / "nora").exists()
    assert find_pyproject(root) == root / "pyproject.toml"


def test_write_sample2_has_httpx(tmp_path: Path) -> None:
    root = write_sample_tree(tmp_path, sample_id="2")
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "httpx" in text


def test_write_sample_zip(tmp_path: Path) -> None:
    z = tmp_path / "hello-uvdrop.zip"
    write_sample_zip(z, sample_id="1")
    assert z.is_file() and z.stat().st_size > 0
