"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import torch  # noqa: F401
    import torch
    x = torch.ones(2, 2); _ = x @ x
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
