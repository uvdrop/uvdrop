"""Local portal sample — stdlib only."""
from __future__ import annotations

import platform
import sys


def main() -> int:
    print("uvdrop-portal-ok hello-stdlib", flush=True)
    print(f"python={sys.version.split()[0]} platform={platform.platform()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
