"""Clip Factory — clipboard image trim / resize with a dominant preview."""
from __future__ import annotations

import sys

from PIL import Image, ImageChops, ImageFilter, ImageGrab, ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui_shell import format_steps, maximize_qt

ACCENT = "#2F6FED"
INK = "#E8EEF7"
STAGE = "#12161C"
PANEL = "#1C2430"
STEPS = ("クリップボードから取込", "加工を確認", "結果をコピー")


def trim_whitespace(img: Image.Image, padding: int = 8) -> Image.Image:
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    diff = ImageChops.difference(rgb, bg)
    bbox = diff.getbbox()
    if not bbox:
        return img
    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(img.width, right + padding)
    bottom = min(img.height, bottom + padding)
    return img.crop((left, top, right, bottom))


def process(
    src: Image.Image,
    *,
    do_trim: bool,
    white_bg: bool,
    max_width: int,
    sharpen: bool,
) -> Image.Image:
    img = src.convert("RGBA")
    if do_trim:
        img = trim_whitespace(img)
    if white_bg:
        base = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(base, img)
    if max_width > 0 and img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, max(1, int(img.height * ratio))), Image.Resampling.LANCZOS)
    if sharpen:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
    return img


def image_to_clipboard(img: Image.Image) -> None:
    """Put PNG on the Windows clipboard via Qt."""
    qimg = ImageQt.ImageQt(img.convert("RGBA"))
    QApplication.clipboard().setImage(qimg)


class ClipFactoryWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Clip Factory")
        self.resize(980, 680)
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background: {STAGE}; color: {INK}; }}
            QLabel#hero {{ font-size: 28px; font-weight: 700; }}
            QLabel#sub {{ color: #8B9BB0; font-size: 14px; }}
            QPushButton {{
                background: {ACCENT}; color: white; border: none; border-radius: 14px;
                padding: 14px 22px; font-size: 15px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #4C86FF; }}
            QPushButton#ghost {{
                background: {PANEL}; border: 1px solid #334155;
            }}
            QCheckBox, QSpinBox {{ font-size: 13px; }}
            QLabel#steps {{
                background: {PANEL}; color: {ACCENT}; border-radius: 12px;
                padding: 12px 16px; font-size: 13px; font-weight: 700;
            }}
            QLabel#status {{
                background: {PANEL}; color: {INK}; border-radius: 12px;
                padding: 12px 16px; font-size: 14px;
            }}
            QSpinBox {{
                background: {PANEL}; border: 1px solid #334155; border-radius: 8px;
                padding: 6px; color: {INK};
            }}
            """
        )
        self._source: Image.Image | None = None
        self._result: Image.Image | None = None
        self._qimage = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        layout.addWidget(self._label("Clip Factory", "hero"))
        layout.addWidget(
            self._label("スクショを貼る → 余白カット → 幅そろえ → すぐまたコピー。資料貼り付け専用。", "sub")
        )

        self._steps = QLabel(format_steps(STEPS, 1))
        self._steps.setObjectName("steps")
        layout.addWidget(self._steps)
        self._status = QLabel("次: スクショして「クリップボードから取り込む」または Ctrl+V")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self.stage = QLabel("クリップボードの画像が、ここにどどんと出ます")
        self.stage.setAlignment(Qt.AlignCenter)
        self.stage.setMinimumHeight(400)
        self.stage.setStyleSheet(
            f"background:#0B0E12; border-radius:22px; color:#5B6B7C; font-size:16px;"
        )
        layout.addWidget(self.stage, stretch=1)

        opts = QHBoxLayout()
        self.trim = QCheckBox("余白トリム")
        self.trim.setChecked(True)
        self.white = QCheckBox("白背景に乗せる")
        self.white.setChecked(True)
        self.sharp = QCheckBox("少しシャープ")
        self.sharp.setChecked(True)
        opts.addWidget(self.trim)
        opts.addWidget(self.white)
        opts.addWidget(self.sharp)
        opts.addSpacing(16)
        opts.addWidget(QLabel("最大幅"))
        self.width = QSpinBox()
        self.width.setRange(0, 4000)
        self.width.setValue(1200)
        self.width.setSuffix(" px（0=そのまま）")
        opts.addWidget(self.width)
        opts.addStretch()
        layout.addLayout(opts)

        for w in (self.trim, self.white, self.sharp, self.width):
            if hasattr(w, "stateChanged"):
                w.stateChanged.connect(self._reprocess)
            else:
                w.valueChanged.connect(self._reprocess)

        actions = QHBoxLayout()
        grab = QPushButton("クリップボードから取り込む")
        grab.clicked.connect(self.grab_clipboard)
        copy_btn = QPushButton("加工結果をコピー")
        copy_btn.clicked.connect(self.copy_result)
        save_btn = QPushButton("PNG保存")
        save_btn.setObjectName("ghost")
        save_btn.clicked.connect(self.save_result)
        actions.addWidget(grab)
        actions.addWidget(copy_btn)
        actions.addWidget(save_btn)
        actions.addStretch()
        layout.addLayout(actions)

        QShortcut(QKeySequence.Paste, self, activated=self.grab_clipboard)

    def _label(self, text: str, obj: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName(obj)
        return lab

    def grab_clipboard(self) -> None:
        img = ImageGrab.grabclipboard()
        if not isinstance(img, Image.Image):
            QMessageBox.information(self, "画像がない", "先に画面をスクショ／画像をコピーしてください。")
            return
        self._source = img.convert("RGBA")
        self._reprocess()
        self._steps.setText(format_steps(STEPS, 2))
        self._status.setText(
            f"取込 {self._source.width}×{self._source.height} — 次: オプションを調整し「加工結果をコピー」"
        )

    def _reprocess(self) -> None:
        if self._source is None:
            return
        self._result = process(
            self._source,
            do_trim=self.trim.isChecked(),
            white_bg=self.white.isChecked(),
            max_width=self.width.value(),
            sharpen=self.sharp.isChecked(),
        )
        self._qimage = ImageQt.ImageQt(self._result)
        pix = QPixmap.fromImage(self._qimage)
        self.stage.setPixmap(
            pix.scaled(self.stage.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        if "[3]" in self._steps.text():
            return
        self._steps.setText(format_steps(STEPS, 2))
        self._status.setText(f"結果 {self._result.width}×{self._result.height} — 次: 「加工結果をコピー」")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reprocess()

    def copy_result(self) -> None:
        if self._result is None:
            self.grab_clipboard()
            if self._result is None:
                return
        image_to_clipboard(self._result)
        self._steps.setText(format_steps(STEPS, 3))
        self._status.setText("コピーした — そのまま貼れます（必要なら PNG保存も可）")

    def save_result(self) -> None:
        if self._result is None:
            QMessageBox.information(self, "まだ", "先に取り込んでください。")
            return
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, "保存", "clip-factory.png", "PNG (*.png)")
        if path:
            self._result.convert("RGB").save(path)
            self._steps.setText(format_steps(STEPS, 3))
            self._status.setText(f"保存 {path}")


def main() -> int:
    app = QApplication(sys.argv)
    win = ClipFactoryWindow()
    win.show()
    maximize_qt(win)
    print("uvdrop-portal-ok clip-factory", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
