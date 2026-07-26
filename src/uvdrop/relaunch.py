"""Relaunch a kept app by key (used by desktop shortcuts)."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: python -m uvdrop.relaunch <app_key>", file=sys.stderr)
        return 2
    key = args[0]
    from uvdrop.launcher import relaunch_kept

    try:
        result = relaunch_kept(key)
    except Exception as e:
        print(f"uvdrop: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1
    print(f"launched {result.app_key} pid={result.pid}")
    for w in result.policy.warnings:
        print(f"warn: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
