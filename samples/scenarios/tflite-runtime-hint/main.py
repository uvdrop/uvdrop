"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    try:
        import ai_edge_litert  # noqa: F401
    except ImportError:
        import importlib
        importlib.import_module('ai_edge_litert')
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
