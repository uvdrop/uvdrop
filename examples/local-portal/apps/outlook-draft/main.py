"""Outlook Draft — polished COM launcher for mail drafts."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
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

STEPS = ("宛先・件名・本文", "必要なら添付", "Outlookで下書きを開く")


def create_draft(to: str, subject: str, body: str, attachment: Path | None) -> None:
    import win32com.client  # type: ignore

    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)  # olMailItem
    mail.To = to
    mail.Subject = subject
    mail.Body = body
    if attachment and attachment.is_file():
        mail.Attachments.Add(str(attachment))
    mail.Display(True)


class OutlookDraftWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Outlook Draft")
        self.resize(920, 680)
        self.attachment: Path | None = None
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #F3F0EA; color: #1C2430; }
            QLabel#hero { font-size: 32px; font-weight: 800; color: #0F4C81; }
            QLabel#sub { color: #5B6B7C; font-size: 14px; }
            QLabel#field { font-size: 12px; font-weight: 700; color: #3D4A5C; }
            QLineEdit, QTextEdit {
                background: white; border: 1px solid #D5D0C6; border-radius: 12px;
                padding: 12px; font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus { border: 2px solid #0F4C81; }
            QPushButton {
                background: #0F4C81; color: white; border: none; border-radius: 14px;
                padding: 14px 22px; font-size: 15px; font-weight: 800;
            }
            QPushButton:hover { background: #1763A5; }
            QPushButton#ghost {
                background: white; border: 1px solid #D5D0C6; color: #1C2430;
            }
            QWidget#card {
                background: white; border-radius: 24px;
            }
            QLabel#steps {
                background: #E4EDF5; color: #0F4C81; border-radius: 12px;
                padding: 12px 16px; font-size: 13px; font-weight: 700;
            }
            QLabel#status {
                background: #E4EDF5; color: #1C2430; border-radius: 12px;
                padding: 12px 16px; font-size: 14px;
            }
            """
        )

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(14)

        hero = QLabel("Outlook Draft")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        sub = QLabel("フォームを書いてボタン一発。入っている Outlook が下書きウィンドウを開きます。")
        sub.setObjectName("sub")
        layout.addWidget(sub)

        self._steps = QLabel(format_steps(STEPS, 1))
        self._steps.setObjectName("steps")
        layout.addWidget(self._steps)
        self._status = QLabel("次: 宛先・件名・本文を書く → 「Outlook で下書きを開く」")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        card = QWidget()
        card.setObjectName("card")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(28, 24, 28, 24)
        card_l.setSpacing(10)

        def field(title: str, widget: QWidget) -> None:
            lab = QLabel(title)
            lab.setObjectName("field")
            card_l.addWidget(lab)
            card_l.addWidget(widget)

        self.to = QLineEdit()
        self.to.setPlaceholderText("hana@example.com; taro@example.com")
        self.subject = QLineEdit()
        self.subject.setPlaceholderText("件名（わかりやすく短く）")
        self.body = QTextEdit()
        self.body.setPlaceholderText("本文。署名は Outlook 側のままでOK。")
        self.body.setMinimumHeight(220)
        field("宛先", self.to)
        field("件名", self.subject)
        field("本文", self.body)

        att_row = QHBoxLayout()
        self.att_label = QLabel("添付なし")
        self.att_label.setStyleSheet("color:#5B6B7C;")
        att_btn = QPushButton("添付ファイル…")
        att_btn.setObjectName("ghost")
        att_btn.clicked.connect(self.pick_attachment)
        clear_att = QPushButton("添付クリア")
        clear_att.setObjectName("ghost")
        clear_att.clicked.connect(self.clear_attachment)
        att_row.addWidget(self.att_label, stretch=1)
        att_row.addWidget(att_btn)
        att_row.addWidget(clear_att)
        card_l.addLayout(att_row)

        layout.addWidget(card, stretch=1)

        actions = QHBoxLayout()
        go = QPushButton("Outlook で下書きを開く")
        go.clicked.connect(self.open_draft)
        tip = QPushButton("これは何？")
        tip.setObjectName("ghost")
        tip.clicked.connect(self.show_tip)
        actions.addWidget(go)
        actions.addWidget(tip)
        actions.addStretch()
        layout.addLayout(actions)

    def pick_attachment(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "添付")
        if path:
            self.attachment = Path(path)
            self.att_label.setText(self.attachment.name)
            self._steps.setText(format_steps(STEPS, 2))
            self._status.setText(f"添付: {self.attachment.name} — 次: 「Outlook で下書きを開く」")

    def clear_attachment(self) -> None:
        self.attachment = None
        self.att_label.setText("添付なし")
        self._steps.setText(format_steps(STEPS, 1))
        self._status.setText("次: 宛先・件名・本文を書く → 「Outlook で下書きを開く」")

    def open_draft(self) -> None:
        try:
            create_draft(
                self.to.text().strip(),
                self.subject.text().strip() or "(無題)",
                self.body.toPlainText(),
                self.attachment,
            )
            self._steps.setText(format_steps(STEPS, 3))
            self._status.setText("Outlook を開きました — 送る前に内容を確認してね")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self,
                "Outlook に届かない",
                "Outlook（デスクトップ版）が見つかりませんでした。\n"
                "このサンプルは『入っている人限定』の COM 連携デモです。\n\n"
                f"詳細: {exc}",
            )
            self._status.setText("Outlook が見つかりません — デスクトップ版が入っている PC で試してください")

    def show_tip(self) -> None:
        QMessageBox.information(
            self,
            "ヒント",
            "uvdrop らしい『他アプリ連携』の入口です。\n"
            "許可リストとセットで見せると、導入担当にも伝わりやすいです。",
        )


def main() -> int:
    app = QApplication(sys.argv)
    app.setFont(QFont("Yu Gothic UI", 10))
    win = OutlookDraftWindow()
    win.show()
    maximize_qt(win)
    print("uvdrop-portal-ok outlook-draft", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
