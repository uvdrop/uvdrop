"""Device discovery helpers for cameras and microphones."""
from __future__ import annotations

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


def list_cameras(max_probe: int = 8) -> list[CameraInfo]:
    found: list[CameraInfo] = []
    for index in range(max_probe):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        try:
            if cap.isOpened():
                found.append(CameraInfo(index, f"カメラ {index}"))
        finally:
            cap.release()
    return found


def list_microphones() -> list[MicInfo]:
    devices = sd.query_devices()
    found: list[MicInfo] = []
    for index, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            name = dev.get("name", f"Device {index}")
            found.append(MicInfo(index, f"{index}: {name}"))
    return found
