"""Screen + mic recording on a background thread."""
from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mss
import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtCore import QObject, QRect, Signal


@dataclass
class RecordingPaths:
    video: Path
    audio: Path | None
    muxed: Path | None


class CaptureWorker(QObject):
    started = Signal(str)
    stopped = Signal(str, bool)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._region = QRect()
        self._fps = 20
        self._samplerate = 44100
        self._mic_device: int | None = None
        self._output_dir = Path(".")
        self._basename = "take"
        self._with_mic = True

    def configure(
        self,
        region: QRect,
        output_dir: Path,
        basename: str,
        fps: int = 20,
        mic_device: int | None = None,
        with_mic: bool = True,
    ) -> None:
        self._region = QRect(region)
        self._output_dir = output_dir
        self._basename = basename
        self._fps = fps
        self._mic_device = mic_device
        self._with_mic = with_mic

    @property
    def is_recording(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_recording:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        region = self._region
        if region.width() < 2 or region.height() < 2:
            self.error.emit("録画領域が小さすぎます。")
            return

        video_path = self._output_dir / f"{self._basename}.mp4"
        audio_path = self._output_dir / f"{self._basename}.wav"
        muxed_path = self._output_dir / f"{self._basename}_mux.mp4"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(video_path),
            fourcc,
            self._fps,
            (region.width(), region.height()),
        )
        if not writer.isOpened():
            self.error.emit("動画ファイルを開けませんでした。")
            return

        audio_frames: list[np.ndarray] = []
        stream: sd.InputStream | None = None

        def audio_callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
            if status:
                return
            audio_frames.append(indata.copy())

        try:
            if self._with_mic:
                stream = sd.InputStream(
                    samplerate=self._samplerate,
                    channels=1,
                    dtype="float32",
                    device=self._mic_device,
                    callback=audio_callback,
                )
                stream.start()

            self.started.emit(str(video_path))
            interval = 1.0 / self._fps

            with mss.mss() as sct:
                monitor = {
                    "left": region.x(),
                    "top": region.y(),
                    "width": region.width(),
                    "height": region.height(),
                }
                while not self._stop.is_set():
                    t0 = time.perf_counter()
                    shot = sct.grab(monitor)
                    frame = np.array(shot, dtype=np.uint8)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    writer.write(frame)
                    elapsed = time.perf_counter() - t0
                    sleep_for = interval - elapsed
                    if sleep_for > 0:
                        time.sleep(sleep_for)

            writer.release()
            if stream is not None:
                stream.stop()
                stream.close()

            audio_written = False
            if self._with_mic and audio_frames:
                audio = np.concatenate(audio_frames, axis=0)
                sf.write(str(audio_path), audio, self._samplerate)
                audio_written = True

            mux_ok = False
            if audio_written:
                mux_ok = _try_mux(video_path, audio_path, muxed_path)

            result = str(muxed_path if mux_ok else video_path)
            self.stopped.emit(result, mux_ok)
        except Exception as exc:  # noqa: BLE001
            writer.release()
            self.error.emit(str(exc))


def _try_mux(video: Path, audio: Path, output: Path) -> bool:
    ffmpeg = _find_ffmpeg()
    if ffmpeg is None:
        return False
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(output),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, check=False)
        return proc.returncode == 0 and output.exists()
    except OSError:
        return False


def _find_ffmpeg() -> str | None:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None
