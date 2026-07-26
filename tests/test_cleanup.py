"""App cleanup / delete."""

from __future__ import annotations

from pathlib import Path

from uvdrop.cleanup import cleanup_app
from uvdrop.registry import AppRecord, load_registry, upsert


def test_cleanup_removes_registry_and_workspace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from uvdrop.paths import ensure_layout

    ensure_layout()
    workspace = tmp_path / "apps" / "demo"
    workspace.mkdir(parents=True)
    (workspace / "marker.txt").write_text("x", encoding="utf-8")

    upsert(
        AppRecord(
            key="demo",
            name="Demo App",
            source_kind="folder",
            source_path=str(workspace),
            workspace=str(workspace),
            mode="keep",
        )
    )
    assert "demo" in load_registry()
    assert workspace.is_dir()

    cleanup_app("demo", remove_registry=True)

    assert "demo" not in load_registry()
    assert not workspace.exists()
