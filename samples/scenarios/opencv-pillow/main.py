"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import cv2  # noqa: F401
    import PIL  # noqa: F401
    import numpy  # noqa: F401
    import cv2
    import numpy as np
    from PIL import Image
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    _ = Image.fromarray(img)
    _ = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
