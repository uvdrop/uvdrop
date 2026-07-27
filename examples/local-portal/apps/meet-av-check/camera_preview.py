"""OpenCV camera capture wrapper."""
from __future__ import annotations

import cv2

class CameraPreview:
    def __init__(self, index: int = 0) -> None:
        self._index = index
        self._cap: cv2.VideoCapture | None = None

    @property
    def index(self) -> int:
        return self._index

    def open(self, index: int | None = None) -> bool:
        self.close()
        if index is not None:
            self._index = index
        cap = cv2.VideoCapture(self._index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            return False
        self._cap = cap
        return True

    def read_pil(self) -> Image.Image | None:
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
