"""TOML loader compatible with Python 3.11+ (tomllib)."""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - prefer 3.11+; optional backport
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError as e:
        raise ImportError(
            "uvdrop requires Python 3.11+ (tomllib), or install 'tomli' on 3.10.\n"
            f"This interpreter is {sys.version.split()[0]}.\n"
            "Try: py -3.12 -m uvdrop"
        ) from e

TOMLDecodeError = tomllib.TOMLDecodeError
loads = tomllib.loads
load = tomllib.load

__all__ = ["TOMLDecodeError", "load", "loads"]
