"""CLI launch helper."""

from __future__ import annotations

import os
from pathlib import Path

from uvdrop.i18n import t
from uvdrop.launcher import launch_source, prepare_launch, prepare_relaunch, execute_launch
from uvdrop.policy import needs_launch_confirm
from uvdrop.registry import load_registry


def _cli_may_proceed(policy) -> bool:
    """CLI has no dialog — refuse when GUI would have asked for confirmation."""
    if policy.blocking:
        return False
    if not needs_launch_confirm(policy):
        return True
    if os.environ.get("UVDROP_ASSUME_YES", "").strip() in {"1", "true", "yes"}:
        return True
    print(t("cli.needs_confirm"), flush=True)
    return False


def run_path(path_or_key: str, *, keep: bool = True) -> int:
    # If it matches a kept key and path doesn't exist, relaunch
    p = Path(path_or_key)
    if not p.exists():
        apps = load_registry()
        if path_or_key in apps:
            prep = prepare_relaunch(path_or_key)
            if prep.policy.blocking:
                print("blocked:\n" + "\n".join(prep.policy.errors))
                return 1
            # Shortcuts / relaunch: already approved once; still honor block.
            # Confirm-skip rules apply only to brand-new launches.
            result = execute_launch(prep, keep=True, sync=True, run=True)
            print(f"launched {result.app_key} pid={result.pid}")
            for w in result.policy.warnings:
                print(f"warn: {w}")
            return 0
        print(f"not found: {path_or_key}")
        return 1

    prep = prepare_launch(p)
    if prep.policy.blocking:
        print("blocked:\n" + "\n".join(prep.policy.errors))
        return 1
    if not _cli_may_proceed(prep.policy):
        return 2
    result = execute_launch(prep, keep=keep, sync=True, run=True)
    print(f"launched {result.app_key} pid={result.pid}")
    print(f"workspace: {result.workspace}")
    for w in result.policy.warnings:
        print(f"warn: {w}")
    return 0
