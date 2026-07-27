"""Ghost Frame Recorder — translucent overlay screen region recorder."""
from __future__ import annotations

import sys
from pathlib import Path

import sounddevice as sd
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from overlay import OverlayWindow
from recorder import CaptureWorker
from recordings_panel import RecordingsPanel
from storage import default_output_dir, new_take_basename


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ghost Frame Recorder")
        self.resize(420, 220)

        self.output_dir = default_output_dir()
        self.worker = CaptureWorker()
        self.worker.started.connect(self._on_started)
        self.worker.stopped.connect(self._on_stopped)
        self.worker.error.connect(self._on_error)

        self.overlay = OverlayWindow()
        self.overlay.region_changed.connect(lambda _r: self._update_region_label())

        self.recordings = RecordingsPanel(self.output_dir, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.recordings)

        central = QWidget()
        layout = QVBoxLayout(central)

        self.region_label = QLabel()
        layout.addWidget(self.region_label)

        mic_row = QHBoxLayout()
        mic_row.addWidget(QLabel("マイク:"))
        self.mic_combo = QComboBox()
        mic_row.addWidget(self.mic_combo, stretch=1)
        layout.addLayout(mic_row)

        self.mic_check = QCheckBox("マイクを同時録音（WAV サイドカー / 可能なら mux）")
        self.mic_check.setChecked(True)
        layout.addWidget(self.mic_check)

        hint = QLabel(
            "ショートカット: Ctrl+Shift+R 録画切替 / Ctrl+Shift+H 枠表示 / Esc 停止\n"
            "保存先: "
            + str(self.output_dir)
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.setCentralWidget(central)
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self._populate_mics()
        self._update_region_label()

        toggle = QAction("録画切替", self)
        toggle.setShortcut(QKeySequence("Ctrl+Shift+R"))
        toggle.triggered.connect(self.toggle_record)
        self.addAction(toggle)

        hide_chrome = QAction("枠表示切替", self)
        hide_chrome.setShortcut(QKeySequence("Ctrl+Shift+H"))
        hide_chrome.triggered.connect(self.toggle_chrome)
        self.addAction(hide_chrome)

        stop = QAction("停止", self)
        stop.setShortcut(QKeySequence(Qt.Key_Escape))
        stop.triggered.connect(self.stop_record)
        self.addAction(stop)

        QShortcut(QKeySequence("Ctrl+Shift+R"), self.overlay, self.toggle_record)
        QShortcut(QKeySequence("Ctrl+Shift+H"), self.overlay, self.toggle_chrome)
        QShortcut(QKeySequence(Qt.Key_Escape), self.overlay, self.stop_record)

    def _populate_mics(self) -> None:
        self.mic_combo.clear()
        default_idx = None
        try:
            default_in = sd.default.device[0]
        except Exception:  # noqa: BLE001
            default_in = None
        for index, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                label = f"{index}: {dev['name']}"
                self.mic_combo.addItem(label, index)
                if index == default_in:
                    default_idx = self.mic_combo.count() - 1
        if default_idx is not None:
            self.mic_combo.setCurrentIndex(default_idx)

    def _mic_device(self) -> int | None:
        idx = self.mic_combo.currentIndex()
        if idx < 0:
            return None
        return self.mic_combo.itemData(idx)

    def _update_region_label(self) -> None:
        g = self.overlay.geometry_rect()
        self.region_label.setText(f"録画領域: x={g.x()} y={g.y()} {g.width()}×{g.height()}")

    def showEvent(self, event) -> None:  # noqa: ANN001, N802
        super().showEvent(event)
        self.overlay.show()

    def closeEvent(self, event) -> None:  # noqa: ANN001, N802
        self.stop_record()
        self.overlay.close()
        super().closeEvent(event)

    def toggle_chrome(self) -> None:
        visible = not self.overlay.chrome_visible()
        self.overlay.set_chrome_visible(visible)
        self.status.showMessage("枠を表示" if visible else "枠を非表示（録画領域はそのまま）", 3000)

    def toggle_record(self) -> None:
        if self.worker.is_recording:
            self.stop_record()
        else:
            self.start_record()

    def start_record(self) -> None:
        if self.worker.is_recording:
            return
        basename = new_take_basename()
        # Hide chrome so the blue border is not burned into the capture.
        self.overlay.set_chrome_visible(False)
        self.overlay.hide()
        self.worker.configure(
            region=self.overlay.geometry_rect(),
            output_dir=self.output_dir,
            basename=basename,
            mic_device=self._mic_device(),
            with_mic=self.mic_check.isChecked(),
        )
        self.worker.start()
        self.status.showMessage("録画開始…（枠は一時非表示）")

    def stop_record(self) -> None:
        if self.worker.is_recording:
            self.worker.stop()
            self.status.showMessage("録画停止中…")

    def _on_started(self, path: str) -> None:
        self.status.showMessage(f"録画中: {Path(path).name}")

    def _on_stopped(self, path: str, muxed: bool) -> None:
        self.overlay.show()
        self.overlay.set_chrome_visible(True)
        self.recordings.add_take(path)
        if muxed:
            self.status.showMessage(f"保存完了 (mux): {Path(path).name}", 5000)
        else:
            self.status.showMessage(
                f"保存完了: {Path(path).name}（音声は同名 .wav、mux 失敗時は別ファイル）",
                8000,
            )

    def _on_error(self, message: str) -> None:
        self.overlay.show()
        self.overlay.set_chrome_visible(True)
        QMessageBox.warning(self, "録画エラー", message)
        self.status.showMessage(message, 5000)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    print("uvdrop-portal-ok ghost-frame-recorder", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
