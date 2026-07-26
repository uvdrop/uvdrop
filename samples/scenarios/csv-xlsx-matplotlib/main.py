"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import pandas  # noqa: F401
    import openpyxl  # noqa: F401
    import matplotlib  # noqa: F401
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
