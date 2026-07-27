"""Lazy Supertonic TTS wrapper."""
from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np

VOICES = [f"M{i}" for i in range(1, 6)] + [f"F{i}" for i in range(1, 6)]
LANGS = ["ja", "en", "ko", "zh", "es", "fr", "de", "na"]


@dataclass
class SynthResult:
    audio: np.ndarray
    samplerate: int


class TtsEngine:
    def __init__(self) -> None:
        self._tts = None
        self._lock = threading.Lock()
        self._samplerate = 44100

    @property
    def is_ready(self) -> bool:
        return self._tts is not None

    def ensure_loaded(self, on_status) -> None:  # noqa: ANN001
        if self._tts is not None:
            return
        with self._lock:
            if self._tts is not None:
                return
            on_status("初回起動: Supertonic モデルをダウンロード中（約400MB）…")
            from supertonic import TTS

            self._tts = TTS(auto_download=True)
            on_status("モデルの準備が完了しました。")

    def synthesize(
        self,
        text: str,
        voice: str,
        speed: float,
        silence_duration: float,
        lang: str,
        on_status,  # noqa: ANN001
    ) -> SynthResult:
        self.ensure_loaded(on_status)
        assert self._tts is not None
        on_status("音声を合成中…")
        style = self._tts.get_voice_style(voice_name=voice)
        wav, _duration = self._tts.synthesize(
            text=text,
            voice_style=style,
            speed=speed,
            silence_duration=silence_duration,
            lang=lang or None,
        )
        audio = np.asarray(wav, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio[:, 0]
        return SynthResult(audio=audio, samplerate=self._samplerate)
