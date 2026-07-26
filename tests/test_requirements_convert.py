"""requirements.txt → pyproject.toml conversion."""

from __future__ import annotations

from uvdrop.requirements_convert import (
    GENERATED_MARKER,
    convert_to_pyproject,
    find_requirements,
    parse_requirements,
)
from uvdrop.tomlcompat import loads as toml_loads


def test_parse_skips_pip_only_lines(tmp_path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text(
        """
# comment
requests==2.31.0
httpx>=0.27  # inline comment
-e .
--index-url https://example.invalid/simple
git+https://github.com/psf/requests.git
rich ; python_version >= "3.10"
requests
""".strip(),
        encoding="utf-8",
    )
    deps, skipped = parse_requirements(req)
    assert deps == ["requests==2.31.0", "httpx>=0.27", 'rich ; python_version >= "3.10"']
    assert "-e ." in skipped
    assert any("index-url" in s for s in skipped)
    assert any("git+" in s for s in skipped)


def test_parse_follows_includes(tmp_path) -> None:
    (tmp_path / "base.txt").write_text("requests\n", encoding="utf-8")
    req = tmp_path / "requirements.txt"
    req.write_text("-r base.txt\nhttpx\n", encoding="utf-8")
    deps, _ = parse_requirements(req)
    assert deps == ["requests", "httpx"]


def test_convert_writes_pyproject(tmp_path) -> None:
    app = tmp_path / "some-app"
    app.mkdir()
    (app / "requirements.txt").write_text("httpx>=0.27\n", encoding="utf-8")
    result = convert_to_pyproject(app / "requirements.txt")

    assert result.pyproject == app / "pyproject.toml"
    text = result.pyproject.read_text(encoding="utf-8")
    assert GENERATED_MARKER in text
    data = toml_loads(text)
    assert data["project"]["name"] == "some-app"
    assert data["project"]["dependencies"] == ["httpx>=0.27"]


def test_convert_honors_python_version_file(tmp_path) -> None:
    app = tmp_path / "pinned"
    app.mkdir()
    (app / "requirements.txt").write_text("rich\n", encoding="utf-8")
    (app / ".python-version").write_text("3.12.4\n", encoding="utf-8")
    result = convert_to_pyproject(app / "requirements.txt")
    data = toml_loads(result.pyproject.read_text(encoding="utf-8"))
    assert data["project"]["requires-python"] == ">=3.12"


def test_find_requirements_one_level_down(tmp_path) -> None:
    nested = tmp_path / "app"
    nested.mkdir()
    target = nested / "requirements.txt"
    target.write_text("rich\n", encoding="utf-8")
    assert find_requirements(tmp_path) == target
