"""Praise Card — oversized thank-you cards for workplace vibes (looks first)."""
from __future__ import annotations

import math
import random
import sys

from PIL import Image, ImageDraw, ImageFont, ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui_shell import format_steps, maximize_qt

STEPS = ("名前と一言を書く", "カードを確認", "コピー／保存")
THEMES = {
    "夕焼けゴールド": {
        "bg": [(255, 120, 70), (255, 190, 90), (255, 230, 160)],
        "ink": (40, 24, 16),
        "accent": (255, 255, 255),
    },
    "深夜ネオン": {
        "bg": [(18, 12, 40), (70, 30, 120), (20, 160, 180)],
        "ink": (245, 240, 255),
        "accent": (120, 255, 210),
    },
    "芝生メモ": {
        "bg": [(220, 245, 210), (170, 220, 160), (120, 190, 130)],
        "ink": (28, 48, 32),
        "accent": (255, 255, 255),
    },
}


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        ("Yu Gothic UI", "Yu Gothic UI Bold", "Meiryo", "Segoe UI", "Arial")
        if not bold
        else ("Yu Gothic UI Bold", "Meiryo Bold", "Segoe UI Bold", "Arial Bold", "Yu Gothic UI")
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient(size: tuple[int, int], colors: list[tuple[int, int, int]]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.5:
            u = t * 2
            c0, c1 = colors[0], colors[1]
        else:
            u = (t - 0.5) * 2
            c0, c1 = colors[1], colors[2]
        r = int(c0[0] + (c1[0] - c0[0]) * u)
        g = int(c0[1] + (c1[1] - c0[1]) * u)
        b = int(c0[2] + (c1[2] - c0[2]) * u)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def _confetti(draw: ImageDraw.ImageDraw, w: int, h: int, accent: tuple[int, int, int]) -> None:
    rng = random.Random(42)
    for _ in range(48):
        x = rng.randint(20, w - 20)
        y = rng.randint(20, h - 20)
        s = rng.randint(6, 16)
        ang = rng.random() * math.pi
        color = accent if rng.random() > 0.4 else (255, 255, 255)
        draw.ellipse((x, y, x + s, y + s // 2 + 2), fill=color + (180,))
        draw.line(
            (x, y, x + int(math.cos(ang) * 18), y + int(math.sin(ang) * 18)),
            fill=color + (140,),
            width=3,
        )


def render_card(name: str, message: str, theme_name: str) -> Image.Image:
    theme = THEMES[theme_name]
    w, h = 1200, 675
    base = _gradient((w, h), theme["bg"]).convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((48, 48, w - 48, h - 48), radius=36, outline=theme["accent"] + (200,), width=6)
    _confetti(draw, w, h, theme["accent"])

    ink = theme["ink"]
    draw.text((80, 90), "THANK YOU", fill=theme["accent"] + (230,), font=_font(42, bold=True))
    draw.text((80, 170), f"To  {name or 'あなた'}", fill=ink + (255,), font=_font(64, bold=True))

    body = (message or "いつも助かってます。くすっと笑えるくらい、ありがとう。").strip()
    # simple wrap
    font_body = _font(36)
    lines: list[str] = []
    buf = ""
    for ch in body:
        trial = buf + ch
        if font_body.getlength(trial) > w - 200:
            lines.append(buf)
            buf = ch
        else:
            buf = trial
    if buf:
        lines.append(buf)
    y = 290
    for line in lines[:5]:
        draw.text((80, y), line, fill=ink + (255,), font=font_body)
        y += 52

    draw.text((80, h - 120), "from your teammate  ·  Praise Card", fill=ink + (200,), font=_font(22))
    return Image.alpha_composite(base, overlay)


class PraiseCardWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Praise Card")
        self.resize(1080, 760)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #1B1410; color: #FFE8D2; }
            QLabel#hero { font-size: 30px; font-weight: 800; color: #FFC48A; }
            QLabel#sub { color: #C4A58A; font-size: 14px; }
            QLineEdit, QTextEdit, QComboBox {
                background: #2A2018; border: 1px solid #5A4030; border-radius: 12px;
                padding: 10px; color: #FFE8D2; font-size: 14px;
            }
            QPushButton {
                background: #FF7A45; color: #1B1410; border: none; border-radius: 14px;
                padding: 14px 22px; font-size: 15px; font-weight: 800;
            }
            QPushButton:hover { background: #FF9466; }
            QPushButton#ghost {
                background: transparent; border: 1px solid #5A4030; color: #FFE8D2;
            }
            QLabel#steps {
                background: #2A2018; color: #FF7A45; border-radius: 12px;
                padding: 12px 16px; font-size: 13px; font-weight: 700;
            }
            QLabel#status {
                background: #2A2018; color: #FFE8D2; border-radius: 12px;
                padding: 12px 16px; font-size: 14px;
            }
            """
        )
        self._card: Image.Image | None = None
        self._qimage = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        hero = QLabel("Praise Card")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        sub = QLabel("名前と一言で、貼れる「ありがとう」を爆速生成。見た目が仕事。称賛の摩擦を下げる。")
        sub.setObjectName("sub")
        layout.addWidget(sub)

        self._steps = QLabel(format_steps(STEPS, 1))
        self._steps.setObjectName("steps")
        layout.addWidget(self._steps)
        self._status = QLabel("次: 左に名前と一言を書いてカードを確認 → 「コピー」で共有")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        form = QHBoxLayout()
        left = QVBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("相手の名前")
        self.msg = QTextEdit()
        self.msg.setPlaceholderText("一言メッセージ（短くてOK）")
        self.msg.setFixedHeight(110)
        self.theme = QComboBox()
        self.theme.addItems(list(THEMES.keys()))
        left.addWidget(QLabel("だれに？"))
        left.addWidget(self.name)
        left.addWidget(QLabel("メッセージ"))
        left.addWidget(self.msg)
        left.addWidget(QLabel("見た目"))
        left.addWidget(self.theme)
        form.addLayout(left, stretch=1)

        self.stage = QLabel("カードがここにどかっと出る")
        self.stage.setAlignment(Qt.AlignCenter)
        self.stage.setMinimumSize(640, 360)
        self.stage.setStyleSheet(
            "background:#120E0C; border-radius:20px; color:#7A5A45; font-size:16px;"
        )
        form.addWidget(self.stage, stretch=2)
        layout.addLayout(form, stretch=1)

        actions = QHBoxLayout()
        gen = QPushButton("カードをつくる")
        gen.clicked.connect(self.generate)
        copy_btn = QPushButton("コピー")
        copy_btn.clicked.connect(self.copy_card)
        save_btn = QPushButton("PNG保存")
        save_btn.setObjectName("ghost")
        save_btn.clicked.connect(self.save_card)
        actions.addWidget(gen)
        actions.addWidget(copy_btn)
        actions.addWidget(save_btn)
        actions.addStretch()
        layout.addLayout(actions)

        self.name.textChanged.connect(self.generate)
        self.msg.textChanged.connect(self.generate)
        self.theme.currentIndexChanged.connect(self.generate)
        self.generate()

    def generate(self) -> None:
        self._card = render_card(self.name.text().strip(), self.msg.toPlainText(), self.theme.currentText())
        self._show_card()
        named = bool(self.name.text().strip() or self.msg.toPlainText().strip())
        if named:
            self._steps.setText(format_steps(STEPS, 2))
            self._status.setText("カードを確認中 — 次: 「コピー」で Slack / Teams に貼る")
        else:
            self._steps.setText(format_steps(STEPS, 1))
            self._status.setText("次: 左に名前と一言を書いてカードを確認 → 「コピー」で共有")

    def _show_card(self) -> None:
        if self._card is None:
            return
        self._qimage = ImageQt.ImageQt(self._card)
        pix = QPixmap.fromImage(self._qimage)
        self.stage.setPixmap(
            pix.scaled(self.stage.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._show_card()

    def copy_card(self) -> None:
        if self._card is None:
            return
        self._qimage = ImageQt.ImageQt(self._card.convert("RGBA"))
        QApplication.clipboard().setImage(self._qimage)
        self._steps.setText(format_steps(STEPS, 3))
        self._status.setText("コピーした — Slack / Teams / メールに貼れます")
        QMessageBox.information(self, "コピーした", "Slack / Teams / メールに貼れます。")

    def save_card(self) -> None:
        if self._card is None:
            return
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, "保存", "praise-card.png", "PNG (*.png)")
        if path:
            self._card.convert("RGB").save(path)
            self._steps.setText(format_steps(STEPS, 3))
            self._status.setText(f"保存した: {path}")


def main() -> int:
    app = QApplication(sys.argv)
    win = PraiseCardWindow()
    win.show()
    maximize_qt(win)
    print("uvdrop-portal-ok praise-card", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
