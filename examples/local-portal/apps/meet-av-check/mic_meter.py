"""Microphone level meter and short record/playback test."""
from __future__ import annotations

import threading
from collections import deque

import numpy as np
import sounddevice as sd


class MicMeter:
    def __init__(self, device: int | None = None, blocksize: int = 1024) -> None:
        self._device = device
        self._blocksize = blocksize
        self._stream: sd.InputStream | None = None
        self._levels: deque[float] = deque(maxlen=8)
        self._lock = threading.Lock()
        self._running = False
        self._last_error = ""

    @property
    def device(self) -> int | None:
        return self._device

    @property
    def last_error(self) -> str:
        return self._last_error

    def set_device(self, device: int | None) -> None:
        self.stop()
        self._device = device

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        if status:
            return
        mono = indata[:, 0] if indata.ndim > 1 else indata
        rms = float(np.sqrt(np.mean(np.square(mono.astype(np.float64)))))
        with self._lock:
            self._levels.append(rms)

    def start(self) -> bool:
        self.stop()
        self._last_error = ""
        try:
            kwargs: dict = {
                "channels": 1,
                "dtype": "float32",
                "blocksize": self._blocksize,
                "callback": self._callback,
            }
            if self._device is not None:
                kwargs["device"] = self._device
            # Prefer device default samplerate when available
            try:
                info = sd.query_devices(self._device, "input")
                sr = int(info.get("default_samplerate") or 44100)
                kwargs["samplerate"] = sr
            except Exception:  # noqa: BLE001
                kwargs["samplerate"] = 44100
            self._stream = sd.InputStream(**kwargs)
            self._stream.start()
            self._running = True
            return True
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            self._stream = None
            self._running = False
            return False

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None
        self._running = False
        with self._lock:
            self._levels.clear()

    def current_rms(self) -> float:
        with self._lock:
            if not self._levels:
                return 0.0
            return max(self._levels)


def record_seconds(seconds: float, device: int | None, samplerate: int | None = None) -> np.ndarray:
    if samplerate is None:
        try:
            info = sd.query_devices(device, "input")
            samplerate = int(info.get("default_samplerate") or 44100)
        except Exception:  # noqa: BLE001
            samplerate = 44100
    frames = int(seconds * samplerate)
    audio = sd.rec(frames, samplerate=samplerate, channels=1, dtype="float32", device=device)
    sd.wait()
    return audio


def play_audio(audio: np.ndarray, samplerate: int = 44100) -> None:
    sd.play(audio, samplerate=samplerate)
    sd.wait()
