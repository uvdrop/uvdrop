"""CLI launch helper."""

from __future__ import annotations

from pathlib import Path

from uvdrop.launcher import launch_source, relaunch_kept
from uvdrop.registry import load_registry


def run_path(path_or_key: str, *, keep: bool = True) -> int:
    # If it matches a kept key and path doesn't exist, relaunch
    p = Path(path_or_key)
    if not p.exists():
        apps = load_registry()
        if path_or_key in apps:
            result = relaunch_kept(path_or_key)
            print(f"launched {result.app_key} pid={result.pid}")
            for w in result.policy.warnings:
                print(f"warn: {w}")
            return 0
        print(f"not found: {path_or_key}")
        return 1

    result = launch_source(p, keep=keep)
    print(f"launched {result.app_key} pid={result.pid}")
    print(f"workspace: {result.workspace}")
    for w in result.policy.warnings:
        print(f"warn: {w}")
    return 0
