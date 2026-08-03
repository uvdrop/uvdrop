"""OpenCV camera capture wrapper (Windows-safe)."""
from __future__ import annotations

import time

import cv2
from PIL import Image


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
        # Prefer DirectShow on Windows; fall back to default backend.
        for backend in (cv2.CAP_DSHOW, cv2.CAP_ANY):
            cap = cv2.VideoCapture(self._index, backend)
            if not cap.isOpened():
                cap.release()
                continue
            # Verify we can actually grab a frame (opened≠usable on some drivers)
            ok = False
            for _ in range(8):
                ok, frame = cap.read()
                if ok and frame is not None:
                    break
                time.sleep(0.03)
            if ok:
                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                except Exception:  # noqa: BLE001
                    pass
                self._cap = cap
                return True
            cap.release()
        self._cap = None
        return False

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
            time.sleep(0.05)  # let DirectShow release the device
