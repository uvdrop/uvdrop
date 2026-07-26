"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import sklearn  # noqa: F401
    import numpy  # noqa: F401
    from sklearn.linear_model import LogisticRegression
    import numpy as np
    X = np.array([[0.0], [1.0], [2.0], [3.0]])
    y = np.array([0, 0, 1, 1])
    LogisticRegression().fit(X, y)
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
