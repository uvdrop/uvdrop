"""App cleanup / delete."""

from __future__ import annotations

from pathlib import Path

from uvdrop.cleanup import cleanup_app, gc_inactive_venvs, hibernate_venv
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


def test_hibernate_removes_only_venv(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from uvdrop.paths import dotenv_dir, ensure_layout, envs_dir

    ensure_layout()
    workspace = tmp_path / "apps" / "demo"
    workspace.mkdir(parents=True)
    dotenv = dotenv_dir() / "demo"
    dotenv.mkdir()
    venv = envs_dir() / "demo"
    venv.mkdir()
    (venv / "package.bin").write_bytes(b"x" * 64)
    upsert(
        AppRecord(
            key="demo",
            name="Demo",
            source_kind="folder",
            source_path=str(workspace),
            workspace=str(workspace),
            mode="keep",
        )
    )

    reclaimed = hibernate_venv("demo")

    assert reclaimed == 64
    assert not venv.exists()
    assert workspace.exists()
    assert dotenv.exists()
    assert "demo" in load_registry()


def test_gc_hibernates_only_inactive_kept_venvs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from uvdrop.paths import ensure_layout, envs_dir

    ensure_layout()
    now = 2_000_000_000.0
    for key in ("old", "recent", "temp"):
        (envs_dir() / key).mkdir()
    upsert(
        AppRecord(
            key="old",
            name="Old",
            source_kind="folder",
            source_path="old",
            workspace="old",
            last_run_at=now - 15 * 86400,
        )
    )
    upsert(
        AppRecord(
            key="recent",
            name="Recent",
            source_kind="folder",
            source_path="recent",
            workspace="recent",
            last_run_at=now - 2 * 86400,
        )
    )
    upsert(
        AppRecord(
            key="temp",
            name="Temp",
            source_kind="folder",
            source_path="temp",
            workspace="temp",
            mode="temp",
            last_run_at=now - 30 * 86400,
        )
    )

    assert gc_inactive_venvs(7, now=now) == ["old"]
    assert not (envs_dir() / "old").exists()
    assert (envs_dir() / "recent").exists()
    assert (envs_dir() / "temp").exists()
    assert set(load_registry()) == {"old", "recent", "temp"}
