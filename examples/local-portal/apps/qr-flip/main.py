"""QR Flip — send via flip-book QR; read via camera, clipboard, file, or loopback."""
from __future__ import annotations

import base64
import hashlib
import sys
from dataclasses import dataclass, field

import cv2
import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageGrab, ImageQt
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui_shell import format_steps, maximize_qt

MAGIC = "UVDROPQR1"
CHUNK = 48  # smaller = easier for cameras to decode
STEPS = ("送信でQRをつくる", "受信で「一括で読む」", "完成テキストを確認")


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("Yu Gothic UI", "Meiryo", "Segoe UI"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def chunk_payload(text: str) -> list[str]:
    raw = text.encode("utf-8")
    digest = hashlib.sha1(raw).hexdigest()[:10]
    if not raw:
        parts = [b""]
    else:
        parts = [raw[i : i + CHUNK] for i in range(0, len(raw), CHUNK)]
    frames = [f"{MAGIC}|H|{len(parts)}|{digest}"]
    for i, part in enumerate(parts):
        frames.append(f"{MAGIC}|D|{i}|{base64.urlsafe_b64encode(part).decode('ascii')}")
    return frames


def make_qr_image(payload: str, index: int, total: int) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    # High-contrast black on white — easiest for OpenCV / phone cameras
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    w = max(img.width + 48, 560)
    canvas = Image.new("RGB", (w, w + 80), (11, 16, 32))
    canvas.paste(img, ((w - img.width) // 2, 32))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, w + 12, w - 24, w + 68), radius=14, fill=(77, 150, 255))
    draw.text((w // 2 - 48, w + 22), f"{index + 1} / {total}", fill=(255, 255, 255), font=_font(28))
    return canvas


def decode_qr_from_bgr(frame: np.ndarray) -> list[str]:
    """Try several preprocess paths; return unique decoded strings."""
    detector = cv2.QRCodeDetector()
    found: list[str] = []

    def _try(img: np.ndarray) -> None:
        data, _pts, _ = detector.detectAndDecode(img)
        if data:
            found.append(data)
        try:
            ok, infos, _pts, _ = detector.detectAndDecodeMulti(img)
            if ok and infos:
                for info in infos:
                    if info:
                        found.append(info)
        except Exception:  # noqa: BLE001
            pass

    _try(frame)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    _try(gray)
    _try(cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 8))
    # upscale helps screen-captured / distant codes
    big = cv2.resize(gray, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
    _try(big)

    # unique preserve order
    out: list[str] = []
    seen: set[str] = set()
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def decode_qr_from_pil(img: Image.Image) -> list[str]:
    rgb = np.array(img.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return decode_qr_from_bgr(bgr)


@dataclass
class ReceiverState:
    total: int | None = None
    digest: str | None = None
    parts: dict[int, bytes] = field(default_factory=dict)

    def ingest(self, text: str) -> str | None:
        if not text.startswith(MAGIC + "|"):
            return None
        bits = text.split("|", 3)
        if len(bits) < 4:
            return None
        _, kind, a, b = bits
        if kind == "H":
            self.total = int(a)
            self.digest = b
            self.parts.clear()
            return f"ヘッダ受信: {self.total} 枚予定"
        if kind == "D":
            idx = int(a)
            self.parts[idx] = base64.urlsafe_b64decode(b.encode("ascii"))
            got = len(self.parts)
            if self.total and got >= self.total and all(i in self.parts for i in range(self.total)):
                raw = b"".join(self.parts[i] for i in range(self.total))
                dig = hashlib.sha1(raw).hexdigest()[:10]
                if self.digest and dig != self.digest:
                    return "欠け／改ざんの可能性（ハッシュ不一致）"
                return raw.decode("utf-8", errors="replace")
            missing = []
            if self.total:
                missing = [i for i in range(self.total) if i not in self.parts]
            miss = f"  未受信:{missing[:8]}" if missing else ""
            return f"受信 {got}/{self.total or '?'}{miss}"
        return None

    def is_complete_text(self, result: str) -> bool:
        return bool(
            self.total
            and len(self.parts) >= self.total
            and all(i in self.parts for i in range(self.total))
            and not result.startswith(("受信", "ヘッダ", "欠け"))
        )


class SendPane(QWidget):
    def __init__(self, window: QrFlipWindow) -> None:
        super().__init__()
        self.window = window
        self.frames: list[str] = []
        self.index = 0
        self._qimage = None
        self.timer = QTimer(self)
        self.timer.setInterval(1200)
        self.timer.timeout.connect(self.next_frame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        self.input = QTextEdit()
        self.input.setPlaceholderText("送りたいテキスト。短いほど読みやすいです。")
        self.input.setFixedHeight(100)
        layout.addWidget(self.input)

        row = QHBoxLayout()
        paste = QPushButton("クリップボードから")
        paste.setObjectName("ghost")
        paste.clicked.connect(self.from_clip)
        build = QPushButton("パラパラQRをつくる")
        build.clicked.connect(self.build)
        play = QPushButton("自動めくり")
        play.clicked.connect(self.toggle_play)
        prev = QPushButton("◀")
        prev.setObjectName("ghost")
        prev.clicked.connect(self.prev_frame)
        nxt = QPushButton("▶")
        nxt.setObjectName("ghost")
        nxt.clicked.connect(self.next_frame)
        for w in (paste, build, play, prev, nxt):
            row.addWidget(w)
        row.addStretch()
        layout.addLayout(row)

        self.stage = QLabel("ここに巨大QRがパラパラします")
        self.stage.setAlignment(Qt.AlignCenter)
        self.stage.setMinimumHeight(480)
        self.stage.setStyleSheet("background:#070B16; border-radius:24px; color:#5C6B8A; font-size:16px;")
        layout.addWidget(self.stage, stretch=1)
        self.status = QLabel("「受信」タブで読むか、下のボタンでこのPC内テスト")
        self.status.setStyleSheet("color:#8FA0C0;")
        layout.addWidget(self.status)

    def from_clip(self) -> None:
        text = QApplication.clipboard().text()
        if text:
            self.input.setPlainText(text)

    def build(self) -> None:
        text = self.input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "空", "テキストを入れてください。")
            return
        self.frames = chunk_payload(text)
        self.index = 0
        self.show_frame()
        self.status.setText(f"{len(self.frames)} 枚に分割（自動めくり約1.2秒/枚）")
        self.window.set_flow(2, "次: 「受信」タブ → 「送信タブを一括で読む（確実）」")

    def toggle_play(self) -> None:
        if not self.frames:
            self.build()
        if not self.frames:
            return
        if self.timer.isActive():
            self.timer.stop()
            self.status.setText("自動めくり停止")
        else:
            self.timer.start()
            self.status.setText("自動めくり中… 受信タブで読んでください")
            self.window.set_flow(2, "次: 「受信」タブで読む（まずは一括読取が確実）")

    def prev_frame(self) -> None:
        if not self.frames:
            return
        self.index = (self.index - 1) % len(self.frames)
        self.show_frame()

    def next_frame(self) -> None:
        if not self.frames:
            return
        self.index = (self.index + 1) % len(self.frames)
        self.show_frame()

    def show_frame(self) -> None:
        img = make_qr_image(self.frames[self.index], self.index, len(self.frames))
        self._qimage = ImageQt.ImageQt(img.convert("RGBA"))
        pix = QPixmap.fromImage(self._qimage)
        self.stage.setPixmap(pix.scaled(self.stage.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def current_payload(self) -> str | None:
        if not self.frames:
            return None
        return self.frames[self.index]

    def all_payloads(self) -> list[str]:
        return list(self.frames)


class ReceivePane(QWidget):
    def __init__(self, window: QrFlipWindow) -> None:
        super().__init__()
        self.window = window
        self.state = ReceiverState()
        self.cap: cv2.VideoCapture | None = None
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)
        self._seen: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)

        tip = QLabel(
            "読み方: ①このPCで一括読取  ②画像/スクショから  ③カメラでパラパラ受信"
        )
        tip.setStyleSheet("color:#8FA0C0;")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        row = QHBoxLayout()
        loop = QPushButton("送信タブを一括で読む（確実）")
        loop.clicked.connect(self.read_from_send_tab)
        clip = QPushButton("クリップボード画像を読む")
        clip.setObjectName("ghost")
        clip.clicked.connect(self.read_clipboard_image)
        file_btn = QPushButton("画像ファイルを読む")
        file_btn.setObjectName("ghost")
        file_btn.clicked.connect(self.read_file)
        start = QPushButton("カメラ受信")
        start.clicked.connect(self.start_camera)
        stop = QPushButton("停止")
        stop.setObjectName("ghost")
        stop.clicked.connect(self.stop)
        reset = QPushButton("リセット")
        reset.setObjectName("ghost")
        reset.clicked.connect(self.reset)
        for w in (loop, clip, file_btn, start, stop, reset):
            row.addWidget(w)
        layout.addLayout(row)

        self.preview = QLabel("プレビュー")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(320)
        self.preview.setStyleSheet("background:#070B16; border-radius:24px; color:#5C6B8A;")
        layout.addWidget(self.preview, stretch=1)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setPlaceholderText("復元テキストがここに出ます")
        self.out.setFixedHeight(130)
        layout.addWidget(self.out)
        self.status = QLabel("まず「送信タブを一括で読む」で動作確認するのがおすすめ")
        self.status.setStyleSheet("color:#8FA0C0;")
        layout.addWidget(self.status)

    def _feed(self, payloads: list[str], *, source: str) -> None:
        if not payloads:
            self.status.setText(f"{source}: QR を読めませんでした")
            return
        last = ""
        for data in payloads:
            if data in self._seen and not data.startswith(MAGIC + "|H|"):
                continue
            self._seen.add(data)
            result = self.state.ingest(data)
            if result is None:
                continue
            last = result
            if self.state.is_complete_text(result):
                self.out.setPlainText(result)
                self.status.setText(f"完成！（{source}）")
                self.window.set_flow(3, "完成テキストを確認できました。カメラ読取も試せます。")
                self.stop()
                return
        if last:
            self.status.setText(f"{source}: {last}")
            self.window.set_flow(2, f"{source}: {last}")
        else:
            self.status.setText(f"{source}: 認識したがプロトコル外のQRでした")

    def read_from_send_tab(self) -> None:
        """Same-PC reliable path: ingest exact payloads from the send tab."""
        frames = self.window.send.all_payloads()
        if not frames:
            QMessageBox.information(self, "まだ", "先に送信タブで「パラパラQRをつくる」を押してください。")
            self.window.set_flow(1, "次: 「送信」タブでテキストを入れ「パラパラQRをつくる」")
            return
        self.reset()
        self.window.set_flow(2, "送信タブを一括読取中…")
        self._feed(frames, source="送信タブ一括")
        # also show current QR preview for reassurance
        payload = self.window.send.current_payload()
        if payload:
            img = make_qr_image(payload, self.window.send.index, len(frames))
            self._show_pil(img)

    def read_clipboard_image(self) -> None:
        grab = ImageGrab.grabclipboard()
        if not isinstance(grab, Image.Image):
            QMessageBox.information(self, "画像がない", "QR が写ったスクショをコピーしてから押してください。")
            return
        self._show_pil(grab)
        decoded = decode_qr_from_pil(grab)
        self._feed(decoded, source="クリップボード")

    def read_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "QR画像", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        img = Image.open(path).convert("RGB")
        self._show_pil(img)
        self._feed(decode_qr_from_pil(img), source="ファイル")

    def _show_pil(self, img: Image.Image) -> None:
        q = ImageQt.ImageQt(img.convert("RGBA"))
        self._keep = q
        self.preview.setPixmap(
            QPixmap.fromImage(q).scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def start_camera(self) -> None:
        self.stop()
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.warning(self, "カメラ", "カメラを開けませんでした。画像から読む方法を使ってください。")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap = cap
        self.timer.start()
        self.status.setText("カメラスキャン中… QR全体が枠に入るように")

    def stop(self) -> None:
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def reset(self) -> None:
        self.state = ReceiverState()
        self._seen.clear()
        self.out.clear()
        self.status.setText("受信リセット")

    def tick(self) -> None:
        if self.cap is None:
            return
        ok, frame = self.cap.read()
        if not ok:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        self.preview.setPixmap(
            QPixmap.fromImage(qimg).scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        decoded = decode_qr_from_bgr(frame)
        if decoded:
            self._feed(decoded, source="カメラ")


class QrFlipWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("QR Flip")
        self.resize(1000, 860)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #0B1020; color: #E8EEFF; }
            QLabel#hero { font-size: 30px; font-weight: 800; color: #6BCB77; }
            QLabel#sub { color: #8FA0C0; font-size: 14px; }
            QTextEdit {
                background: #151A2E; border: 1px solid #2A3555; border-radius: 14px;
                padding: 10px; color: #E8EEFF; font-size: 14px;
            }
            QPushButton {
                background: #6BCB77; color: #0B1020; border: none; border-radius: 12px;
                padding: 10px 14px; font-size: 13px; font-weight: 800;
            }
            QPushButton:hover { background: #88E090; }
            QPushButton#ghost {
                background: transparent; border: 1px solid #2A3555; color: #E8EEFF;
            }
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #151A2E; color: #8FA0C0; padding: 10px 18px; margin-right: 6px;
                border-radius: 10px;
            }
            QTabBar::tab:selected { background: #243056; color: #E8EEFF; font-weight: 700; }
            QLabel#steps {
                background: #151A2E; color: #6BCB77; border-radius: 12px;
                padding: 12px 16px; font-size: 13px; font-weight: 700;
            }
            QLabel#status {
                background: #151A2E; color: #E8EEFF; border-radius: 12px;
                padding: 12px 16px; font-size: 14px;
            }
            """
        )
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        hero = QLabel("QR Flip")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        sub = QLabel("パラパラ送信＋読む。まずは同一PCで「送信タブを一括で読む」が確実です。")
        sub.setObjectName("sub")
        layout.addWidget(sub)

        self._steps = QLabel(format_steps(STEPS, 1))
        self._steps.setObjectName("steps")
        layout.addWidget(self._steps)
        self._status = QLabel("次: 「送信」タブでテキストを入れ「パラパラQRをつくる」")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        tabs = QTabWidget()
        self.send = SendPane(self)
        self.recv = ReceivePane(self)
        tabs.addTab(self.send, "送信（パラパラ）")
        tabs.addTab(self.recv, "受信（読む）")
        layout.addWidget(tabs, stretch=1)

    def set_flow(self, step: int, status: str) -> None:
        self._steps.setText(format_steps(STEPS, step))
        self._status.setText(status)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.recv.stop()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    win = QrFlipWindow()
    win.show()
    maximize_qt(win)
    print("uvdrop-portal-ok qr-flip", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
