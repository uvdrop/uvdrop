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

    @property
    def device(self) -> int | None:
        return self._device

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

    def start(self) -> None:
        if self._running:
            return
        self._stream = sd.InputStream(
            device=self._device,
            channels=1,
            dtype="float32",
            blocksize=self._blocksize,
            callback=self._callback,
        )
        self._stream.start()
        self._running = True

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False
        with self._lock:
            self._levels.clear()

    def current_rms(self) -> float:
        with self._lock:
            if not self._levels:
                return 0.0
            return max(self._levels)


def record_seconds(seconds: float, device: int | None, samplerate: int = 44100) -> np.ndarray:
    frames = int(seconds * samplerate)
    audio = sd.rec(frames, samplerate=samplerate, channels=1, dtype="float32", device=device)
    sd.wait()
    return audio


def play_audio(audio: np.ndarray, samplerate: int = 44100) -> None:
    sd.play(audio, samplerate=samplerate)
    sd.wait()
