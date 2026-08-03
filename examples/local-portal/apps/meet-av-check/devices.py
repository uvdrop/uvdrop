"""Device discovery helpers for cameras and microphones."""
from __future__ import annotations

import time
from dataclasses import dataclass

import cv2
import sounddevice as sd


@dataclass(frozen=True)
class CameraInfo:
    index: int
    label: str


@dataclass(frozen=True)
class MicInfo:
    index: int
    label: str


def list_cameras(max_probe: int = 4) -> list[CameraInfo]:
    """Probe a few indices gently — opening many DSHOW devices locks webcams."""
    found: list[CameraInfo] = []
    for index in range(max_probe):
        opened = False
        for backend in (cv2.CAP_DSHOW, cv2.CAP_ANY):
            cap = cv2.VideoCapture(index, backend)
            try:
                if not cap.isOpened():
                    continue
                ok, _frame = cap.read()
                if ok:
                    found.append(CameraInfo(index, f"カメラ {index}"))
                    opened = True
                    break
            finally:
                cap.release()
            time.sleep(0.04)
        if not opened and index > 0 and not found:
            # no camera at 0 → stop probing further
            break
        time.sleep(0.05)
    return found


def list_microphones() -> list[MicInfo]:
    found: list[MicInfo] = []
    try:
        devices = sd.query_devices()
    except Exception:  # noqa: BLE001
        return found
    for index, dev in enumerate(devices):
        try:
            if int(dev.get("max_input_channels", 0) or 0) > 0:
                name = str(dev.get("name", f"Device {index}"))
                found.append(MicInfo(index, f"{index}: {name}"))
        except Exception:  # noqa: BLE001
            continue
    return found
