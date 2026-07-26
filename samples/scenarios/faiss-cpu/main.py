"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import faiss  # noqa: F401
    import numpy  # noqa: F401
    import faiss
    import numpy as np
    xb = np.random.random((16, 8)).astype('float32')
    index = faiss.IndexFlatL2(8)
    index.add(xb)
    _ = index.search(xb[:1], 3)
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
