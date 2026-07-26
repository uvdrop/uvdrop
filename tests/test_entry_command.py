"""Entry candidate discovery and command-string round trips."""

from __future__ import annotations

import pytest

from uvdrop.project import entry_candidates, format_entry, parse_entry, resolve_entry


def _app(tmp_path, *files: str):
    root = tmp_path / "app"
    root.mkdir()
    for rel in files:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("print('hi')\n", encoding="utf-8")
    return root


def test_candidates_list_every_runnable_file(tmp_path) -> None:
    root = _app(tmp_path, "main.py", "app.py", "src/main.py")
    found = entry_candidates(root, root)
    names = [format_entry(argv, root) for argv in found]
    assert names[0] == "main.py"
    assert "app.py" in names
    assert "src/main.py" in names


def test_resolve_entry_reports_missing_entry(tmp_path) -> None:
    root = _app(tmp_path)
    with pytest.raises(FileNotFoundError):
        resolve_entry(root, root)


def test_format_and_parse_round_trip(tmp_path) -> None:
    root = _app(tmp_path, "src/main.py")
    argv = entry_candidates(root, root)[0]
    text = format_entry(argv, root)
    assert text == "src/main.py"
    assert parse_entry(text, root) == ["src/main.py"]


def test_parse_keeps_arguments_and_drops_python_prefix(tmp_path) -> None:
    root = _app(tmp_path, "main.py")
    assert parse_entry("python main.py --debug", root) == ["main.py", "--debug"]
    assert parse_entry("uv run python main.py", root) == ["main.py"]
    assert parse_entry("-m mypkg", root) == ["-m", "mypkg"]


def test_parse_rejects_empty(tmp_path) -> None:
    root = _app(tmp_path, "main.py")
    with pytest.raises(ValueError):
        parse_entry("python", root)


def test_parse_expands_file_outside_project_dir(tmp_path) -> None:
    root = _app(tmp_path, "main.py", "pkg/pyproject.toml")
    project_dir = root / "pkg"
    argv = parse_entry("main.py", project_dir, root)
    assert argv == [str((root / "main.py").resolve())]
