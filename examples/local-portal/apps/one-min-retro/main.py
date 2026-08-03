"""One-min Retro — Keep / Problem / Try board with a big visual export."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageQt
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui_shell import format_steps, maximize_qt

STEPS = ("1分スタート", "Keep / Problem / Try を書く", "一枚絵で共有")
COLS = (
    ("Keep", "よかったこと", "#E7F8EF", "#1F8A70", "#0B3D2E"),
    ("Problem", "困ったこと", "#FDEBEC", "#D64550", "#4A151A"),
    ("Try", "次に試すこと", "#EEF2FF", "#4C6EF5", "#1B2A6B"),
)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        ("Yu Gothic UI Bold", "Meiryo Bold", "Segoe UI Bold", "Yu Gothic UI")
        if bold
        else ("Yu Gothic UI", "Meiryo", "Segoe UI")
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in (text or "（まだ書いてない）").splitlines() or ["（まだ書いてない）"]:
        buf = ""
        for ch in para:
            trial = buf + ch
            if font.getlength(trial) > max_w:
                lines.append(buf)
                buf = ch
            else:
                buf = trial
        lines.append(buf or " ")
    return lines[:12]


def render_board(keep: str, problem: str, try_: str, seconds_left: int | None) -> Image.Image:
    w, h = 1400, 820
    img = Image.new("RGB", (w, h), (248, 246, 241))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, 110), fill=(28, 36, 48))
    draw.text((40, 28), "1-min Retro", fill=(255, 255, 255), font=_font(42, True))
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    right = f"{stamp}" if seconds_left is None else f"{stamp}   ·   {seconds_left:02d}s"
    draw.text((w - 360, 42), right, fill=(180, 190, 205), font=_font(22))

    texts = (keep, problem, try_)
    gap = 24
    col_w = (w - 40 - gap * 2) // 3
    x = 20
    for (title, sub, bg, accent, ink), body in zip(COLS, texts, strict=True):
        draw.rounded_rectangle((x, 140, x + col_w, h - 40), radius=28, fill=bg)
        draw.rounded_rectangle((x + 22, 164, x + 22 + 120, 210), radius=12, fill=accent)
        draw.text((x + 36, 172), title, fill=(255, 255, 255), font=_font(22, True))
        draw.text((x + 22, 230), sub, fill=ink, font=_font(20, True))
        y = 280
        for line in wrap(draw, body, _font(26), col_w - 48):
            draw.text((x + 22, y), line, fill=ink, font=_font(26))
            y += 40
        x += col_w + gap
    draw.text((40, h - 32), "local only · uvdrop sample", fill=(150, 150, 150), font=_font(16))
    return img


class Column(QWidget):
    def __init__(self, title: str, sub: str, bg: str, accent: str) -> None:
        super().__init__()
        self.setStyleSheet(
            f"""
            QWidget#col {{ background: {bg}; border-radius: 22px; }}
            QLabel#title {{
                background: {accent}; color: white; border-radius: 12px;
                padding: 8px 14px; font-size: 16px; font-weight: 800;
            }}
            QLabel#sub {{ color: #243044; font-size: 13px; font-weight: 700; }}
            QTextEdit {{
                background: rgba(255,255,255,180); border: none; border-radius: 14px;
                padding: 12px; font-size: 16px; color: #1C2430;
            }}
            """
        )
        wrap_l = QVBoxLayout(self)
        wrap_l.setContentsMargins(0, 0, 0, 0)
        card = QWidget()
        card.setObjectName("col")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        t = QLabel(title)
        t.setObjectName("title")
        t.setFixedWidth(120)
        layout.addWidget(t, alignment=Qt.AlignLeft)
        s = QLabel(sub)
        s.setObjectName("sub")
        layout.addWidget(s)
        self.edit = QTextEdit()
        self.edit.setPlaceholderText("短くでOK。責めない。")
        layout.addWidget(self.edit, stretch=1)
        wrap_l.addWidget(card)


class RetroWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("1-min Retro")
        self.resize(1180, 780)
        self.left = 60
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)
        self._qimage = None
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #F8F6F1; color: #1C2430; }
            QLabel#hero { font-size: 30px; font-weight: 800; color: #1C2430; }
            QLabel#sub { color: #5B6B7C; font-size: 14px; }
            QPushButton {
                background: #1C2430; color: white; border: none; border-radius: 14px;
                padding: 12px 18px; font-size: 14px; font-weight: 800;
            }
            QPushButton:hover { background: #2C3648; }
            QPushButton#accent { background: #4C6EF5; }
            QPushButton#ghost {
                background: white; border: 1px solid #D5D0C6; color: #1C2430;
            }
            QLabel#steps {
                background: #EDEAE3; color: #4C6EF5; border-radius: 12px;
                padding: 12px 16px; font-size: 13px; font-weight: 700;
            }
            QLabel#status {
                background: #EDEAE3; color: #1C2430; border-radius: 12px;
                padding: 12px 16px; font-size: 14px;
            }
            """
        )

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        hero = QLabel("1-min Retro")
        hero.setObjectName("hero")
        sub = QLabel("Keep / Problem / Try。サーバに残さない。短く書いて、画像で共有。")
        sub.setObjectName("sub")
        titles.addWidget(hero)
        titles.addWidget(sub)
        head.addLayout(titles, stretch=1)
        self.clock = QLabel("60")
        self.clock.setAlignment(Qt.AlignCenter)
        self.clock.setFixedSize(84, 84)
        self.clock.setStyleSheet(
            "background:#1C2430; color:#FFD93D; border-radius:42px; font-size:28px; font-weight:800;"
        )
        head.addWidget(self.clock)
        layout.addLayout(head)

        self._steps = QLabel(format_steps(STEPS, 1))
        self._steps.setObjectName("steps")
        layout.addWidget(self._steps)
        self._status = QLabel("次: 「1分スタート」を押してから、3列に短く書く")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        cols = QHBoxLayout()
        self.keep = Column(*COLS[0][:4])
        self.problem = Column(*COLS[1][:4])
        self.try_ = Column(*COLS[2][:4])
        cols.addWidget(self.keep)
        cols.addWidget(self.problem)
        cols.addWidget(self.try_)
        layout.addLayout(cols, stretch=1)

        self.preview = QLabel("書き出すと、共有用の一枚絵がここに出ます")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedHeight(150)
        self.preview.setStyleSheet(
            "background:#EDEAE3; border-radius:16px; color:#7A8694; font-size:14px;"
        )
        layout.addWidget(self.preview)

        actions = QHBoxLayout()
        start = QPushButton("1分スタート")
        start.setObjectName("accent")
        start.clicked.connect(self.start_timer)
        export = QPushButton("一枚絵を保存")
        export.clicked.connect(self.export_png)
        copy = QPushButton("画像をコピー")
        copy.setObjectName("ghost")
        copy.clicked.connect(self.copy_png)
        for w in (start, export, copy):
            actions.addWidget(w)
        actions.addStretch()
        layout.addLayout(actions)

    def start_timer(self) -> None:
        self.left = 60
        self.clock.setText("60")
        self.clock.setStyleSheet(
            "background:#1C2430; color:#FFD93D; border-radius:42px; font-size:28px; font-weight:800;"
        )
        self.timer.start()
        self._steps.setText(format_steps(STEPS, 2))
        self._status.setText("タイマー計測中 — Keep / Problem / Try を短く書いてください")

    def _tick(self) -> None:
        self.left -= 1
        self.clock.setText(str(max(0, self.left)))
        if self.left <= 0:
            self.timer.stop()
            self.clock.setStyleSheet(
                "background:#D64550; color:white; border-radius:42px; font-size:22px; font-weight:800;"
            )
            self.clock.setText("TIME")
            self._steps.setText(format_steps(STEPS, 3))
            self._status.setText("時間切れ — 次: 「一枚絵を保存」または「画像をコピー」で共有")
            self._refresh_preview()

    def _board(self) -> Image.Image:
        left = self.left if self.timer.isActive() or self.left == 0 else None
        return render_board(
            self.keep.edit.toPlainText(),
            self.problem.edit.toPlainText(),
            self.try_.edit.toPlainText(),
            left if self.timer.isActive() or self.clock.text() == "TIME" else None,
        )

    def _refresh_preview(self) -> None:
        img = self._board()
        self._qimage = ImageQt.ImageQt(img)
        self.preview.setPixmap(
            QPixmap.fromImage(self._qimage).scaled(
                self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def export_png(self) -> None:
        img = self._board()
        self._refresh_preview()
        path, _ = QFileDialog.getSaveFileName(
            self, "保存", f"retro-{datetime.now():%Y%m%d-%H%M}.png", "PNG (*.png)"
        )
        if path:
            img.save(path)
            self._steps.setText(format_steps(STEPS, 3))
            self._status.setText(f"保存した: {path} — 会議チャットに貼れます")
            QMessageBox.information(self, "保存した", "会議のチャットにそのまま貼れます。")

    def copy_png(self) -> None:
        img = self._board()
        self._qimage = ImageQt.ImageQt(img.convert("RGBA"))
        QApplication.clipboard().setImage(self._qimage)
        self._refresh_preview()
        self._steps.setText(format_steps(STEPS, 3))
        self._status.setText("画像をコピーした — そのまま貼れます")
        QMessageBox.information(self, "コピーした", "画像として貼れます。")


def main() -> int:
    app = QApplication(sys.argv)
    win = RetroWindow()
    win.show()
    maximize_qt(win)
    print("uvdrop-portal-ok one-min-retro", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
