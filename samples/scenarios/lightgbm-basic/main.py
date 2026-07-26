"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import lightgbm  # noqa: F401
    import numpy  # noqa: F401
    import lightgbm as lgb
    import numpy as np
    X = np.random.randn(40, 3)
    y = (X[:, 0] > 0).astype(int)
    lgb.LGBMClassifier(n_estimators=5, verbose=-1).fit(X, y)
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
