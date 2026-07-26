"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import cv2  # noqa: F401
    import cv2
    assert hasattr(cv2, 'VideoCapture')
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
