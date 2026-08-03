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
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from overlay import OverlayWindow
from recorder import CaptureWorker
from recordings_panel import RecordingsPanel
from storage import default_output_dir, new_take_basename
from ui_shell import format_steps, maximize_qt

STEPS = ("枠を置く", "録画", "一覧で確認")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ghost Frame Recorder")
        self.resize(900, 560)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #0B1020; color: #E8EEFF; }
            QLabel#hero { font-size: 28px; font-weight: 800; color: #4D96FF; }
            QLabel#sub { color: #8FA0C0; font-size: 14px; }
            QLabel#steps {
                background: #151A2E; color: #4D96FF; border-radius: 12px;
                padding: 12px 16px; font-size: 13px; font-weight: 700;
            }
            QLabel#status {
                background: #151A2E; color: #E8EEFF; border-radius: 12px;
                padding: 12px 16px; font-size: 14px;
            }
            QPushButton {
                background: #4D96FF; color: white; border: none; border-radius: 12px;
                padding: 12px 18px; font-size: 14px; font-weight: 800;
            }
            QPushButton:hover { background: #6AABFF; }
            QPushButton#ghost {
                background: transparent; border: 1px solid #2A3555; color: #E8EEFF;
            }
            QPushButton#danger { background: #D64550; }
            QComboBox, QCheckBox { font-size: 13px; }
            QComboBox {
                background: #151A2E; border: 1px solid #2A3555; border-radius: 8px;
                padding: 8px; color: #E8EEFF;
            }
            """
        )

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
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        hero = QLabel("Ghost Frame Recorder")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        sub = QLabel("半透明の枠で範囲を決めて録画。ショートカットもそのまま使えます。")
        sub.setObjectName("sub")
        layout.addWidget(sub)

        self._steps = QLabel(format_steps(STEPS, 1))
        self._steps.setObjectName("steps")
        layout.addWidget(self._steps)
        self._status = QLabel("次: 画面上の青枠をドラッグして録画範囲を決める")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self.region_label = QLabel()
        self.region_label.setStyleSheet("color:#8FA0C0; font-size:13px;")
        layout.addWidget(self.region_label)

        mic_row = QHBoxLayout()
        mic_row.addWidget(QLabel("マイク:"))
        self.mic_combo = QComboBox()
        mic_row.addWidget(self.mic_combo, stretch=1)
        layout.addLayout(mic_row)

        self.mic_check = QCheckBox("マイクを同時録音（WAV サイドカー / 可能なら mux）")
        self.mic_check.setChecked(True)
        layout.addWidget(self.mic_check)

        actions = QHBoxLayout()
        self.record_btn = QPushButton("録画開始 (Ctrl+Shift+R)")
        self.record_btn.clicked.connect(self.toggle_record)
        chrome_btn = QPushButton("枠の表示切替 (Ctrl+Shift+H)")
        chrome_btn.setObjectName("ghost")
        chrome_btn.clicked.connect(self.toggle_chrome)
        stop_btn = QPushButton("停止 (Esc)")
        stop_btn.setObjectName("ghost")
        stop_btn.clicked.connect(self.stop_record)
        for w in (self.record_btn, chrome_btn, stop_btn):
            actions.addWidget(w)
        actions.addStretch()
        layout.addLayout(actions)

        hint = QLabel(
            "ショートカット: Ctrl+Shift+R 録画切替 / Ctrl+Shift+H 枠表示 / Esc 停止\n"
            "保存先: "
            + str(self.output_dir)
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#8FA0C0;")
        layout.addWidget(hint)
        layout.addStretch(1)

        self.setCentralWidget(central)

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

    def _set_flow(self, step: int, status: str) -> None:
        self._steps.setText(format_steps(STEPS, step))
        self._status.setText(status)

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
        # Don't rewind past a completed take when the overlay reappears.
        if not self.worker.is_recording and "[1]" in self._steps.text().split("→")[0]:
            self._set_flow(1, "次: 青枠の位置・サイズを決めたら「録画開始」")

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
        msg = "枠を表示" if visible else "枠を非表示（録画領域はそのまま）"
        if not self.worker.is_recording:
            self._set_flow(1, f"{msg} — 次: 範囲を決めて「録画開始」")

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
        self.record_btn.setText("録画停止 (Ctrl+Shift+R)")
        self.record_btn.setObjectName("danger")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        self._set_flow(2, "録画開始…（枠は一時非表示）Esc または同ボタンで停止")

    def stop_record(self) -> None:
        if self.worker.is_recording:
            self.worker.stop()
            self._set_flow(2, "録画停止中…")

    def _on_started(self, path: str) -> None:
        self._set_flow(2, f"録画中: {Path(path).name} — Esc で停止")

    def _on_stopped(self, path: str, muxed: bool) -> None:
        self.overlay.show()
        self.overlay.set_chrome_visible(True)
        self.recordings.add_take(path)
        self.record_btn.setText("録画開始 (Ctrl+Shift+R)")
        self.record_btn.setObjectName("")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        if muxed:
            self._set_flow(3, f"保存完了 (mux): {Path(path).name} — 右の一覧で確認")
        else:
            self._set_flow(
                3,
                f"保存完了: {Path(path).name}（音声は同名 .wav）— 右の一覧で確認",
            )

    def _on_error(self, message: str) -> None:
        self.overlay.show()
        self.overlay.set_chrome_visible(True)
        self.record_btn.setText("録画開始 (Ctrl+Shift+R)")
        self.record_btn.setObjectName("")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        QMessageBox.warning(self, "録画エラー", message)
        self._set_flow(1, f"エラー: {message} — 枠を直して再録画")


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    maximize_qt(window)
    print("uvdrop-portal-ok ghost-frame-recorder", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
