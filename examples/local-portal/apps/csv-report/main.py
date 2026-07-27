"""Local portal sample — tiny tabular report."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> int:
    out = Path(__file__).resolve().parent / "_out.xlsx"
    df = pd.DataFrame(
        {
            "item": ["alpha", "beta", "gamma"],
            "qty": [3, 5, 2],
            "yen": [1200, 800, 450],
        }
    )
    df["subtotal"] = df["qty"] * df["yen"]
    df.to_excel(out, index=False)
    print("uvdrop-portal-ok csv-report", flush=True)
    print(f"rows={len(df)} total={int(df['subtotal'].sum())} out={out.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
