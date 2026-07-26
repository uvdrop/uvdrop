"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import PyQt5  # noqa: F401
    from PyQt5 import QtCore
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
