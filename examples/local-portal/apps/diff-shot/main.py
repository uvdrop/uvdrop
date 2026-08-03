"""Diff Shot — Before/After with paste, auto-align, and heatmap diff."""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageGrab, ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ui_shell import format_steps, maximize_qt

ACCENT = "#E85D4C"
INK = "#F4F0E8"
STAGE = "#1A1F24"
PANEL = "#242B33"
STEPS = ("BEFOREを入れる", "AFTERを入れる", "差分を確認・保存")


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("Yu Gothic UI", "Meiryo", "Segoe UI", "Arial"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _load(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def clipboard_image() -> Image.Image | None:
    """Read an image from the clipboard (Win screenshot / copy)."""
    grab = ImageGrab.grabclipboard()
    if isinstance(grab, Image.Image):
        return grab.convert("RGBA")
    if isinstance(grab, list) and grab:
        try:
            return Image.open(grab[0]).convert("RGBA")
        except OSError:
            pass
    qimg = QApplication.clipboard().image()
    if not qimg.isNull():
        qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
        w, h = qimg.width(), qimg.height()
        ptr = qimg.bits()
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape(h, w, 4).copy()
        return Image.fromarray(arr, "RGBA")
    return None


def _fit_pair(a: Image.Image, b: Image.Image) -> tuple[Image.Image, Image.Image]:
    w = max(a.width, b.width)
    h = max(a.height, b.height)
    canvas_a = Image.new("RGBA", (w, h), (20, 24, 28, 255))
    canvas_b = Image.new("RGBA", (w, h), (20, 24, 28, 255))
    canvas_a.paste(a, ((w - a.width) // 2, (h - a.height) // 2))
    canvas_b.paste(b, ((w - b.width) // 2, (h - b.height) // 2))
    return canvas_a, canvas_b


def align_after_to_before(
    before: Image.Image,
    after: Image.Image,
    *,
    max_shift: int = 120,
) -> tuple[Image.Image, tuple[float, float]]:
    """Shift ``after`` so it lines up with ``before`` (phase correlation)."""
    a, b = _fit_pair(before, after)
    ga = cv2.cvtColor(np.asarray(a.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32)
    gb = cv2.cvtColor(np.asarray(b.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32)
    try:
        win = cv2.createHanningWindow((ga.shape[1], ga.shape[0]), cv2.CV_32F)
        ga = ga * win
        gb = gb * win
    except Exception:  # noqa: BLE001
        pass
    (dx, dy), _resp = cv2.phaseCorrelate(ga, gb)
    if abs(dx) > max_shift or abs(dy) > max_shift:
        return b, (0.0, 0.0)
    shifted = np.asarray(b.convert("RGBA"))
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    aligned = cv2.warpAffine(
        shifted,
        M,
        (shifted.shape[1], shifted.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(20, 24, 28, 255),
    )
    return Image.fromarray(aligned, "RGBA"), (float(dx), float(dy))


def render_diff(
    before: Image.Image,
    after: Image.Image,
    blend: float,
    *,
    align: bool = True,
) -> tuple[Image.Image, str]:
    """blend: 0=before, 0.5=heatmap, 1=after. Returns (image, status)."""
    status = "位置補正オフ"
    if align:
        after_aligned, (dx, dy) = align_after_to_before(before, after)
        status = f"位置補正  dx={dx:+.1f}px  dy={dy:+.1f}px"
        a, b = _fit_pair(before, after_aligned)
    else:
        a, b = _fit_pair(before, after)

    arr_a = np.asarray(a.convert("RGB"), dtype=np.float32)
    arr_b = np.asarray(b.convert("RGB"), dtype=np.float32)
    delta = np.abs(arr_a - arr_b)
    mag = delta.mean(axis=2)
    heat = np.zeros_like(arr_a)
    heat[..., 0] = np.clip(mag * 3.5, 0, 255)
    heat[..., 1] = np.clip(mag * 0.6, 0, 255)
    heat[..., 2] = np.clip(40 + mag * 0.2, 0, 255)
    base = arr_a * 0.35 + arr_b * 0.35
    heat_mix = np.clip(base + heat * 0.9, 0, 255)

    if blend <= 0.5:
        t = blend * 2.0
        out = arr_a * (1 - t) + heat_mix * t
    else:
        t = (blend - 0.5) * 2.0
        out = heat_mix * (1 - t) + arr_b * t

    img = Image.fromarray(out.astype(np.uint8), "RGB").convert("RGBA")
    badge = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    label = "BEFORE" if blend < 0.33 else ("DIFF" if blend < 0.67 else "AFTER")
    color = (232, 93, 76, 220) if label == "DIFF" else (244, 240, 232, 200)
    draw.rounded_rectangle((24, 24, 160, 72), radius=12, fill=(26, 31, 36, 200))
    draw.text((40, 34), label, fill=color, font=_font(28))
    return Image.alpha_composite(img, badge), status


class DropZone(QLabel):
    def __init__(self, title: str, which: str, owner: DiffShotWindow) -> None:
        super().__init__(title)
        self.which = which
        self.owner = owner
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setStyleSheet(
            f"QLabel {{ background:{PANEL}; color:{INK}; border:2px dashed #3D4752;"
            f" border-radius:16px; font-size:15px; }}"
        )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.owner._paste_target = self.which
        self.owner._pick(self.which)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self.owner._paste_target = self.which
        if event.mimeData().hasUrls():
            path = Path(event.mimeData().urls()[0].toLocalFile())
            if path.is_file():
                self.owner._set_image(self.which, path=path)
                return
        img = clipboard_image()
        if img is not None:
            self.owner._set_image(self.which, image=img, label="(drop)")


class DiffShotWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Diff Shot")
        self.resize(1100, 720)
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background: {STAGE}; color: {INK}; }}
            QLabel#hero {{ font-size: 28px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#sub {{ font-size: 14px; color: #9AA5B1; }}
            QPushButton {{
                background: {ACCENT}; color: white; border: none; border-radius: 12px;
                padding: 12px 20px; font-size: 14px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #FF6F5C; }}
            QPushButton#ghost {{
                background: transparent; border: 1px solid #4A5560; color: {INK};
            }}
            QCheckBox {{ color: {INK}; font-size: 13px; spacing: 8px; }}
            QLabel#steps {{
                background: #242B33; color: {ACCENT}; border-radius: 12px;
                padding: 12px 16px; font-size: 13px; font-weight: 700;
            }}
            QLabel#status {{
                background: #242B33; color: {INK}; border-radius: 12px;
                padding: 12px 16px; font-size: 14px;
            }}
            QSlider::groove:horizontal {{ height: 8px; background: #3D4752; border-radius: 4px; }}
            QSlider::handle:horizontal {{
                width: 22px; margin: -8px 0; border-radius: 11px; background: {ACCENT};
            }}
            """
        )

        self.before: Image.Image | None = None
        self.after: Image.Image | None = None
        self._result: Image.Image | None = None
        self._qimage = None
        self._paste_target = "before"
        self._align_status = ""

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        hero = QLabel("Diff Shot")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        sub = QLabel(
            "Ctrl+V で貼り付け（先に BEFORE、次に AFTER）。位置ずれは自動補正してから差分。"
        )
        sub.setObjectName("sub")
        layout.addWidget(sub)

        self._steps = QLabel(format_steps(STEPS, 1))
        self._steps.setObjectName("steps")
        layout.addWidget(self._steps)
        self._status = QLabel("次: スクショをコピーして「クリップボードを貼る」か Ctrl+V（BEFORE）")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        drops = QHBoxLayout()
        self.zone_a = DropZone("BEFORE\nクリック / ドロップ / Ctrl+V", "before", self)
        self.zone_b = DropZone("AFTER\nクリック / ドロップ / Ctrl+V", "after", self)
        drops.addWidget(self.zone_a)
        drops.addWidget(self.zone_b)
        layout.addLayout(drops)

        self.stage = QLabel()
        self.stage.setAlignment(Qt.AlignCenter)
        self.stage.setMinimumHeight(420)
        self.stage.setStyleSheet("background:#0F1317; border-radius:20px; color:#6B7785; font-size:16px;")
        layout.addWidget(self.stage, stretch=1)
        self._show_empty_stage()

        row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(50)
        self.slider.valueChanged.connect(self._refresh)
        self.align_check = QCheckBox("位置を自動補正（スクショのズレ向け）")
        self.align_check.setChecked(True)
        self.align_check.stateChanged.connect(self._refresh)
        row.addWidget(QLabel("Before"))
        row.addWidget(self.slider, stretch=1)
        row.addWidget(QLabel("After"))
        row.addWidget(self.align_check)
        layout.addLayout(row)

        actions = QHBoxLayout()
        paste_btn = QPushButton("クリップボードを貼る (Ctrl+V)")
        paste_btn.clicked.connect(self.paste_clipboard)
        save_btn = QPushButton("差分画像を保存")
        save_btn.clicked.connect(self._save)
        copy_btn = QPushButton("差分をコピー")
        copy_btn.clicked.connect(self._copy)
        hint = QPushButton("使い方")
        hint.setObjectName("ghost")
        hint.clicked.connect(self._hint)
        for w in (paste_btn, save_btn, copy_btn, hint):
            actions.addWidget(w)
        actions.addStretch()
        layout.addLayout(actions)

        QShortcut(QKeySequence.Paste, self, activated=self.paste_clipboard)

    def _show_empty_stage(self) -> None:
        w, h = 960, 420
        img = Image.new("RGBA", (w, h), (15, 19, 23, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((80, 70, 420, 350), radius=24, outline=(232, 93, 76, 180), width=4)
        draw.rounded_rectangle((540, 70, 880, 350), radius=24, outline=(120, 160, 180, 160), width=4)
        draw.text((150, 180), "BEFORE", fill=(232, 93, 76, 220), font=_font(36))
        draw.text((620, 180), "AFTER", fill=(180, 200, 210, 220), font=_font(36))
        draw.text((220, 380), "Ctrl+V で貼る → 位置補正 → 差分", fill=(107, 119, 133, 255), font=_font(20))
        self._qimage = ImageQt.ImageQt(img)
        self.stage.setPixmap(QPixmap.fromImage(self._qimage))

    def paste_clipboard(self) -> None:
        img = clipboard_image()
        if img is None:
            QMessageBox.information(self, "画像がない", "先にスクショや画像をコピーしてください。")
            return
        which = self._paste_target
        if self.before is None:
            which = "before"
        elif self.after is None:
            which = "after"
        elif which not in ("before", "after"):
            which = "after"
        self._set_image(which, image=img, label="(clipboard)")
        # next paste goes to the other side
        self._paste_target = "after" if which == "before" else "before"

    def _pick(self, which: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "画像を選ぶ", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            self._set_image(which, path=Path(path))

    def _set_image(
        self,
        which: str,
        *,
        path: Path | None = None,
        image: Image.Image | None = None,
        label: str | None = None,
    ) -> None:
        try:
            if image is not None:
                img = image.convert("RGBA")
            elif path is not None:
                img = _load(path)
                label = path.name
            else:
                return
        except OSError as exc:
            QMessageBox.warning(self, "読込失敗", str(exc))
            return
        name = label or which
        if which == "before":
            self.before = img
            self.zone_a.setText(f"BEFORE\n{name}")
            self._paste_target = "after"
        else:
            self.after = img
            self.zone_b.setText(f"AFTER\n{name}")
            self._paste_target = "before"
        self._refresh()

    def _set_flow(self, step: int, status: str) -> None:
        self._steps.setText(format_steps(STEPS, step))
        self._status.setText(status)

    def _refresh(self) -> None:
        if not self.before or not self.after:
            if self.before:
                self._set_flow(2, "次: AFTER を Ctrl+V / ドロップ / クリックで追加")
            else:
                self._set_flow(1, "次: BEFORE を Ctrl+V またはドロップで追加")
            return
        blend = self.slider.value() / 100.0
        self._result, self._align_status = render_diff(
            self.before, self.after, blend, align=self.align_check.isChecked()
        )
        self._set_flow(3, f"{self._align_status}  — 次: スライダーで確認し、保存またはコピー")
        self._qimage = ImageQt.ImageQt(self._result.convert("RGBA"))
        pix = QPixmap.fromImage(self._qimage)
        self.stage.setPixmap(pix.scaled(self.stage.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.before and self.after:
            self._refresh()

    def _save(self) -> None:
        if self._result is None:
            QMessageBox.information(self, "まだ", "Before / After を入れてください。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存", "diff-shot.png", "PNG (*.png)")
        if path:
            self._result.convert("RGB").save(path)

    def _copy(self) -> None:
        if self._result is None:
            QMessageBox.information(self, "まだ", "Before / After を入れてください。")
            return
        self._qimage = ImageQt.ImageQt(self._result.convert("RGBA"))
        QApplication.clipboard().setImage(self._qimage)
        self._set_flow(3, "差分をコピーしました — 資料に貼れます")

    def _hint(self) -> None:
        QMessageBox.information(
            self,
            "使い方",
            "1. スクショをコピー → Ctrl+V（BEFORE）\n"
            "2. もう一枚コピー → Ctrl+V（AFTER）\n"
            "3. 「位置を自動補正」でわずかなズレを吸収\n"
            "4. スライダー中央が差分ヒートマップ",
        )


def main() -> int:
    app = QApplication(sys.argv)
    win = DiffShotWindow()
    win.show()
    maximize_qt(win)
    print("uvdrop-portal-ok diff-shot", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
