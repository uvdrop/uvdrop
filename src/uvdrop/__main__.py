"""CLI / GUI entrypoint."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    if sys.version_info < (3, 11):
        try:
            import tomli  # noqa: F401
        except ImportError:
            print(
                "uvdrop needs Python 3.11+ (this is "
                f"{sys.version.split()[0]}).\n"
                "Try:  py -3.12 -m uvdrop\n"
                "Or from repo root:  py -3.12 -m pip install -e .  then  py -3.12 -m uvdrop",
                file=sys.stderr,
            )
            return 1

    parser = argparse.ArgumentParser(prog="uvdrop", description="Practical offline uv launcher")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--cli", action="store_true", help="Skip GUI and use CLI helpers only")
    parser.add_argument(
        "--relaunch",
        metavar="APP_KEY",
        help="Relaunch a kept app by registry key (used by desktop shortcuts)",
    )
    parser.add_argument("path", nargs="?", help="App folder or ZIP to launch (CLI)")
    parser.add_argument(
        "--keep",
        action="store_true",
        default=True,
        help="Keep app after run (default)",
    )
    parser.add_argument(
        "--temp",
        action="store_true",
        help="Temporary run (remove workspace after process exit when supported)",
    )
    args = parser.parse_args(argv)

    if args.version:
        from uvdrop import __version__

        print(__version__)
        return 0

    if args.relaunch:
        from uvdrop.relaunch import main as relaunch_main

        return relaunch_main([args.relaunch])

    if args.path or args.cli:
        from uvdrop.cli_run import run_path

        if not args.path:
            parser.error("path is required with --cli")
        return run_path(args.path, keep=not args.temp)

    from uvdrop.ui.app import run_app

    run_app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
