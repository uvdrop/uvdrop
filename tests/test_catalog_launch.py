"""preferred_command from catalog is pre-selected but guards still run."""

from __future__ import annotations

from pathlib import Path

from uvdrop.launcher import prepare_launch
from uvdrop.package_spec import PackageRule
from uvdrop.settings import Settings, save_settings


def _write_app(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\n'
        'requires-python = ">=3.11"\ndependencies = []\n',
        encoding="utf-8",
    )
    (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
    return root


def test_preferred_command_is_preselected(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "la"))
    from uvdrop.paths import ensure_layout

    ensure_layout()
    # Disable confirm-heavy defaults aren't needed; prepare_launch only builds prep.
    s = Settings()
    s.allowlist.enabled = False
    save_settings(s)

    app = _write_app(tmp_path / "src-app")
    prep = prepare_launch(app, preferred_command="main.py --from-catalog")
    assert prep.entry_command == "main.py --from-catalog"
    assert "main.py --from-catalog" in prep.entry_options
