"""Rename Preview — batch rename with a loud before → after table."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui_shell import format_steps, maximize_qt

ACCENT = "#3DDC97"
STAGE = "#101612"
INK = "#E6FFF2"
STEPS = ("フォルダを選ぶ", "ルールでプレビュー", "リネーム実行")


def plan_names(
    files: list[Path],
    *,
    prefix: str,
    suffix: str,
    find: str,
    repl: str,
    sequence: bool,
    start: int,
    lower: bool,
) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    n = start
    for path in files:
        stem, ext = path.stem, path.suffix
        name = stem
        if find:
            name = name.replace(find, repl)
        if lower:
            name = name.lower()
            ext = ext.lower()
        if sequence:
            name = f"{name}_{n:03d}"
            n += 1
        name = f"{prefix}{name}{suffix}{ext}"
        # sanitize windows-ish
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        out.append((path, name))
    return out


class RenamePreviewWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Rename Preview")
        self.resize(1000, 700)
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background: {STAGE}; color: {INK}; }}
            QLabel#hero {{ font-size: 28px; font-weight: 800; color: {ACCENT}; }}
            QLabel#sub {{ color: #8FB9A4; font-size: 14px; }}
            QLineEdit {{
                background: #18241C; border: 1px solid #2F4A3A; border-radius: 10px;
                padding: 10px; color: {INK}; font-size: 14px;
            }}
            QPushButton {{
                background: {ACCENT}; color: #072116; border: none; border-radius: 12px;
                padding: 12px 18px; font-size: 14px; font-weight: 800;
            }}
            QPushButton:hover {{ background: #63F0B0; }}
            QPushButton#ghost {{
                background: transparent; border: 1px solid #2F4A3A; color: {INK};
            }}
            QTableWidget {{
                background: #0C120E; gridline-color: #24362C; border: none;
                border-radius: 16px; font-size: 14px;
            }}
            QHeaderView::section {{
                background: #18241C; color: {ACCENT}; padding: 10px; border: none;
                font-weight: 700;
            }}
            QLabel#steps {{
                background: #18241C; color: {ACCENT}; border-radius: 12px;
                padding: 12px 16px; font-size: 13px; font-weight: 700;
            }}
            QLabel#status {{
                background: #18241C; color: {INK}; border-radius: 12px;
                padding: 12px 16px; font-size: 14px;
            }}
            """
        )
        self.folder: Path | None = None
        self.files: list[Path] = []

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        hero = QLabel("Rename Preview")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        sub = QLabel("実行の前に、変更後の名前を大きく見せる。迷ったらやり直しやすい安全側。")
        sub.setObjectName("sub")
        layout.addWidget(sub)

        self._steps = QLabel(format_steps(STEPS, 1))
        self._steps.setObjectName("steps")
        layout.addWidget(self._steps)
        self._status = QLabel("次: 「フォルダを選ぶ」— 実行するまでファイルは変わりません")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        top = QHBoxLayout()
        pick = QPushButton("フォルダを選ぶ")
        pick.clicked.connect(self.pick_folder)
        self.folder_label = QLabel("まだ選んでいません")
        self.folder_label.setStyleSheet("color:#8FB9A4;")
        top.addWidget(pick)
        top.addWidget(self.folder_label, stretch=1)
        layout.addLayout(top)

        rules = QHBoxLayout()
        self.prefix = QLineEdit()
        self.prefix.setPlaceholderText("接頭辞")
        self.suffix = QLineEdit()
        self.suffix.setPlaceholderText("接尾辞（拡張子の前）")
        self.find = QLineEdit()
        self.find.setPlaceholderText("置換前")
        self.repl = QLineEdit()
        self.repl.setPlaceholderText("置換後")
        self.seq = QCheckBox("連番 _001")
        self.lower = QCheckBox("小文字化")
        for w in (self.prefix, self.suffix, self.find, self.repl):
            w.textChanged.connect(self.refresh)
            rules.addWidget(w)
        self.seq.stateChanged.connect(self.refresh)
        self.lower.stateChanged.connect(self.refresh)
        rules.addWidget(self.seq)
        rules.addWidget(self.lower)
        layout.addLayout(rules)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["いまの名前", "変更後"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(42)
        layout.addWidget(self.table, stretch=1)

        actions = QHBoxLayout()
        run = QPushButton("この内容でリネーム実行")
        run.clicked.connect(self.execute)
        refresh = QPushButton("プレビュー更新")
        refresh.setObjectName("ghost")
        refresh.clicked.connect(self.refresh)
        actions.addWidget(run)
        actions.addWidget(refresh)
        actions.addStretch()
        layout.addLayout(actions)

    def pick_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "フォルダ")
        if not path:
            return
        self.folder = Path(path)
        self.folder_label.setText(str(self.folder))
        self.files = sorted([p for p in self.folder.iterdir() if p.is_file()], key=lambda p: p.name.lower())
        self.refresh()

    def _plan(self) -> list[tuple[Path, str]]:
        return plan_names(
            self.files,
            prefix=self.prefix.text(),
            suffix=self.suffix.text(),
            find=self.find.text(),
            repl=self.repl.text(),
            sequence=self.seq.isChecked(),
            start=1,
            lower=self.lower.isChecked(),
        )

    def refresh(self) -> None:
        plan = self._plan()
        self.table.setRowCount(len(plan))
        bold = QFont()
        bold.setBold(True)
        for row, (src, new_name) in enumerate(plan):
            left = QTableWidgetItem(src.name)
            right = QTableWidgetItem(new_name)
            right.setFont(bold)
            right.setForeground(QColor(ACCENT))
            if src.name == new_name:
                right.setForeground(QColor("#6A8F7C"))
            self.table.setItem(row, 0, left)
            self.table.setItem(row, 1, right)
        self.table.resizeColumnsToContents()
        changed = sum(1 for s, n in plan if s.name != n)
        self._steps.setText(format_steps(STEPS, 2))
        self._status.setText(
            f"{len(plan)} 件中 {changed} 件が変わる予定 — 次: 表を確認して「この内容でリネーム実行」"
        )

    def execute(self) -> None:
        plan = self._plan()
        changes = [(s, n) for s, n in plan if s.name != n]
        if not changes:
            QMessageBox.information(self, "変化なし", "リネーム対象がありません。")
            return
        # collision check
        targets = [self.folder / n for _, n in changes]  # type: ignore[operator]
        existing = {p.name for p in self.files}
        for src, new_name in changes:
            existing.discard(src.name)
            if new_name in existing:
                QMessageBox.warning(self, "衝突", f"名前がぶつかります: {new_name}")
                return
            existing.add(new_name)

        reply = QMessageBox.question(
            self,
            "実行する？",
            f"{len(changes)} 件をリネームします。よろしいですか？",
        )
        if reply != QMessageBox.Yes:
            return

        assert self.folder is not None
        done = 0
        for src, new_name in changes:
            dest = self.folder / new_name
            try:
                src.rename(dest)
                done += 1
            except OSError as exc:
                QMessageBox.warning(self, "失敗", f"{src.name}\n{exc}")
                break
        self.files = sorted([p for p in self.folder.iterdir() if p.is_file()], key=lambda p: p.name.lower())
        self.refresh()
        self._steps.setText(format_steps(STEPS, 3))
        self._status.setText(f"完了: {done} 件リネームしました")
        QMessageBox.information(self, "完了", f"{done} 件リネームしました。")


def main() -> int:
    app = QApplication(sys.argv)
    win = RenamePreviewWindow()
    win.show()
    maximize_qt(win)
    print("uvdrop-portal-ok rename-preview", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
